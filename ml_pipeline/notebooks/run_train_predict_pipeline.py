"""
Run Training and Prediction Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This script runs a complete training and prediction pipeline for land cover classification
across specified months of a year. It:

1. Creates a parent directory for the experiment
2. For each month:
   - Creates a child directory for that month's results
   - Runs the training and prediction pipeline
   - Saves metrics for that month
3. Optionally generates annual composites from monthly predictions
4. Optionally runs benchmark evaluations

The script uses subprocess to run train_and_predict_by_month.py for each month,
which handles:
- Loading training polygons from specified database (local/remote)
- Extracting pixel data from NICFI imagery
- Training a Random Forest model
- Making predictions across target areas
- Saving results and uploading to cloud storage

Usage:
    # Full pipeline
    python run_train_predict_pipeline.py --start_month 1 --end_month 12 --year 2023 --project_id 6 --run_id "experiment_name" --db-host local
    
    # Skip specific steps
    python run_train_predict_pipeline.py --start_month 1 --end_month 12 --year 2023 --project_id 6 --run_id "experiment_name" --skip-composites --skip-benchmarks
    
    # Run only benchmarks (requires existing STAC collections)
    python run_train_predict_pipeline.py --benchmarks-only --year 2023 --project_id 6 --run_id "experiment_name"

Database Configuration:
- Use --db-host local for development with local database
- Use --db-host remote for production with remote database

The results are organized as:
    runs/
    └── {run_id}/
        ├── {year}_{month}/
        │   ├── saved_models/
        │   ├── data_cache/
        │   └── prediction_cogs/
        └── composites/
            └── {quad_name}_{year}_forest_cover.tif
"""

import subprocess
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from ml_pipeline.run_manager import RunManager     
from ml_pipeline.composite_generator import CompositeGenerator
from tqdm import tqdm
from joblib import Parallel, delayed
from ml_pipeline.s3_utils import list_files
from ml_pipeline.benchmark_tester import BenchmarkTester
from ml_pipeline.benchmark_metrics_io import create_benchmark_summary_charts

# Configure logging for better pipeline visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments for the pipeline."""
    parser = argparse.ArgumentParser(description="Run training and prediction pipeline for multiple months")
    parser.add_argument("--start_month", type=int, required=True, help="Starting month (1-12)")
    parser.add_argument("--end_month", type=int, required=True, help="Ending month (1-12)")
    parser.add_argument("--year", type=str, required=True, help="Year for the pipeline")
    parser.add_argument("--project_id", type=int, required=True, help="Project ID for training polygons")
    parser.add_argument("--run_id", type=str, required=True, help="Unique identifier for this pipeline run")
    parser.add_argument("--db-host", type=str, choices=["local", "remote"], default="local", 
                       help="Database host configuration: 'local' for localhost, 'remote' for production database")
    parser.add_argument("--skip-composites", action="store_true", 
                       help="Skip composite generation after monthly processing")
    parser.add_argument("--skip-benchmarks", action="store_true", 
                       help="Skip benchmark evaluation after composite generation")
    parser.add_argument("--skip-training", action="store_true", 
                       help="Skip training and prediction, go directly to composites/benchmarks")
    parser.add_argument("--benchmarks-only", action="store_true", 
                       help="Skip training, prediction, and composites - only run benchmarks")
    
    return parser.parse_args()

def validate_arguments(args):
    """Validate command line arguments."""
    # Validate month range (only if training is not skipped)
    if not args.skip_training and not args.benchmarks_only:
        if args.start_month < 1 or args.start_month > 12:
            logger.error("❌ start_month must be between 1 and 12")
            sys.exit(1)
        if args.end_month < 1 or args.end_month > 12:
            logger.error("❌ end_month must be between 1 and 12")
            sys.exit(1)
        if args.start_month > args.end_month:
            logger.error("❌ start_month must be <= end_month")
            sys.exit(1)
    
    # Validate skip option combinations
    if args.benchmarks_only and (args.skip_composites or args.skip_training):
        logger.error("❌ --benchmarks-only cannot be combined with other skip options")
        sys.exit(1)

def process_quad(quad_name: str, run_id: str, year: str):
    """Process a single quad for composite generation."""
    try:
        with CompositeGenerator(run_id=run_id, year=year) as composite_gen:
            composite_gen.generate_composite(quad_name=quad_name)
        return True
    except Exception as e:
        logger.error(f"Error processing quad {quad_name}: {str(e)}")
        return False

def extract_quad_name(s3_file: dict) -> str:
    """Extract quad name (e.g. '567-1027') from S3 file listing."""
    # Get the filename from either key or url
    filename = s3_file['key'].split('/')[-1]
    # Split on underscore and take first part
    return filename.split('_')[0]

def generate_composites(run_id: str, year: str, db_host: str = "local"):
    """Generate annual composites from monthly predictions."""
    logger.info("\n🧩 Generating annual composites...")
    
    try:
        # Get list of quads from S3 based on first successful month
        s3_files = list_files(prefix=f"predictions/{run_id}/{year}/01")
        
        if not s3_files:
            logger.warning("⚠️  No S3 files found for composite generation. Skipping...")
            return
        
        # Extract unique quad names
        quads = list(set(extract_quad_name(f) for f in s3_files))
        logger.info(f"📍 Found {len(quads)} unique quads for composite generation")
        logger.info(f"🔍 Example quads: {quads[:4] if len(quads) >= 4 else quads}")
        
        # Generate composites in parallel (limited to avoid overwhelming S3)
        results = Parallel(n_jobs=2, prefer="processes")(
            delayed(process_quad)(quad_name=quad, run_id=run_id, year=year)
            for quad in tqdm(quads, desc="Generating composites")
        )
        
        # Report results
        successful = sum(results)
        failed = len(quads) - successful
        logger.info(f"✅ Composite generation completed: {successful} successful, {failed} failed")
        
        # Merge individual composites into a single COG (if more than one quad)
        if successful > 1:
            logger.info("🔗 Merging individual composite COGs into single file...")
            with CompositeGenerator(run_id=run_id, year=year) as composite_gen:
                merged_key = composite_gen.merge_composites()
                if merged_key:
                    logger.info(f"✅ Successfully merged composites: {merged_key}")
                    use_merged = True
                else:
                    logger.warning("⚠️  Merge failed, using individual COGs")
                    use_merged = False
        else:
            logger.info("ℹ️  Only one composite generated, skipping merge")
            use_merged = False
        
        # Create STAC collection for composites
        logger.info("📚 Creating STAC collection for composites...")
        use_remote_db = (db_host == "remote")
        CompositeGenerator(run_id=run_id, year=year)._create_stac_collection(
            use_remote_db=use_remote_db, 
            use_merged_cog=use_merged
        )
        logger.info("✅ STAC collection created")
        
    except Exception as e:
        logger.error(f"❌ Error during composite generation: {str(e)}")

def run_benchmarks(run_id: str, year: str, project_id: int, db_host: str = "local"):
    """Run benchmark evaluation against reference datasets."""
    logger.info("\n🏆 Running benchmark evaluation...")
    
    # List of benchmark collections to evaluate
    benchmark_collections = [
        # Our own predictions
        f"nicfi-pred-{run_id}-composite-{year}",  # Our annual composite
        
        # External benchmarks
        "benchmarks-hansen-tree-cover-2022",      # Hansen Global Forest Change
        "benchmarks-mapbiomes-2022",              # MapBiomas
        "benchmarks-esa-landcover-2020",          # ESA WorldCover
        "benchmarks-jrc-forestcover-2020",        # JRC Global Forest Cover
        "benchmarks-palsar-2020",                 # PALSAR Forest/Non-Forest
        "benchmarks-wri-treecover-2020",          # WRI Tree Cover
    ]
    
    logger.info(f"📊 Evaluating {len(benchmark_collections)} benchmark collections")
    
    # Loop through each benchmark collection
    successful_benchmarks = 0
    for collection in benchmark_collections:
        logger.info(f"\n📈 Evaluating benchmark: {collection}")
        logger.info("-" * 80)
        
        try:
            tester = BenchmarkTester(
                base_url="http://localhost:8083",
                collection=collection,
                year=year,
                project_id=project_id,
                run_id=run_id,
                db_host=db_host,
                verbose=False,
            )
            tester.run()
            successful_benchmarks += 1
            logger.info(f"✅ Successfully evaluated {collection}")
        except Exception as e:
            logger.error(f"❌ Failed to evaluate {collection}: {str(e)}")
            continue
    
    logger.info(f"\n🏁 Benchmark evaluation completed: {successful_benchmarks}/{len(benchmark_collections)} successful")
    
    # Generate summary visualizations if we have results
    if successful_benchmarks > 0:
        logger.info("\n📊 Generating benchmark summary charts...")
        try:
            create_benchmark_summary_charts(
                run_id=run_id,
                save_charts=True,
                show_charts=False  # Don't show interactively in pipeline mode
            )
            logger.info("✅ Summary charts generated successfully")
        except Exception as e:
            logger.error(f"❌ Failed to generate summary charts: {str(e)}")
    else:
        logger.warning("⚠️ No successful benchmarks - skipping summary chart generation")

def main():
    """Main pipeline execution function."""
    # Parse and validate arguments
    args = parse_arguments()
    validate_arguments(args)
    
    # Extract arguments for easier access
    run_id = args.run_id
    year = args.year
    project_id = args.project_id
    db_host = getattr(args, 'db_host', 'local')
    
    # Log pipeline configuration
    logger.info("🚀 Starting ML Pipeline")
    logger.info(f"📅 Year: {year}, Months: {args.start_month}-{args.end_month}")
    logger.info(f"📋 Project ID: {project_id}")
    logger.info(f"🏃 Run ID: {run_id}")
    logger.info(f"🗄️  Database: {db_host}")
    logger.info("=" * 60)
    
    # Create run manager for organizing results
    rm = RunManager(run_id=run_id)  # Uses ml_pipeline/runs/ automatically
    logger.info(f"📁 Run directory: {rm.run_path}")

    # Skip training if requested
    if args.skip_training or args.benchmarks_only:
        logger.info("⏭️ Skipping training and prediction as requested")
        successful_months = [f"{m:02d}" for m in range(args.start_month, args.end_month + 1)]
    else:
        # Process each month sequentially
        failed_months = []
        successful_months = []
        total_months = args.end_month - args.start_month + 1
        
        logger.info(f"📊 Processing {total_months} months from {args.start_month:02d} to {args.end_month:02d}")
        
        # Get path to the monthly processing script
        script_path = Path(__file__).parent / "train_and_predict_by_month.py"
        if not script_path.exists():
            logger.error(f"❌ Could not find script at {script_path}")
            sys.exit(1)
        
        for m in tqdm(range(args.start_month, args.end_month + 1), desc=f"Processing months for {year}"):
            month = f"{m:02d}"  # Zero-pad month for consistency
            current_month = f"{year}-{month}"
            
            logger.info(f"\n🗓️  Processing month {m}/{args.end_month}: {current_month}")
            logger.info("-" * 50)
            
            # Build command with database configuration
            cmd = [
                "python",
                str(script_path),
                "--year", year,
                "--month", month,
                "--run_dir", str(rm.run_path),
                "--project_id", str(project_id),
                "--db-host", db_host
            ]
            
            try:
                # Execute monthly pipeline subprocess with live output
                logger.info(f"▶️  Running: {' '.join(cmd)}")
                logger.info("📺 Subprocess output:")
                logger.info("-" * 40)
                start_time = datetime.now()
                
                # Run subprocess without capturing output so it streams to terminal
                subprocess.run(cmd, check=True)
                
                elapsed_time = datetime.now() - start_time
                logger.info("-" * 40)
                logger.info(f"✅ Successfully processed {current_month} in {elapsed_time}")
                
                successful_months.append(month)
                
            except subprocess.CalledProcessError as e:
                elapsed_time = datetime.now() - start_time
                logger.error("-" * 40)
                logger.error(f"❌ Failed to process {current_month} after {elapsed_time}")
                logger.error(f"Return code: {e.returncode}")
                
                failed_months.append(month)

        # Print monthly processing summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 MONTHLY PROCESSING SUMMARY")
        logger.info("=" * 60)
        
        total_processed = len(successful_months) + len(failed_months)
        success_rate = len(successful_months) / total_processed * 100 if total_processed > 0 else 0
        
        logger.info(f"📈 Processed: {total_processed}/{total_months} months ({success_rate:.1f}% success rate)")
        
        if successful_months:
            logger.info(f"✅ Successful months: {', '.join(successful_months)}")
        
        if failed_months:
            logger.warning(f"❌ Failed months: {', '.join(failed_months)}")
            logger.info(f"\n🔄 To retry failed months, run:")
            for month in failed_months:
                retry_cmd = f"python {script_path} --year {year} --month {month} --run_dir {rm.run_path} --project_id {project_id} --db-host {db_host}"
                logger.info(f"   {retry_cmd}")
        
        # Only proceed if we have some successful months
        if not successful_months:
            logger.error("❌ No months processed successfully. Exiting.")
            sys.exit(1)
    
    # Skip composite generation if requested or if benchmarks-only
    if args.skip_composites or args.benchmarks_only:
        logger.info("⏭️ Skipping composite generation as requested")
    else:
        # Generate annual composites
        generate_composites(run_id, year, db_host)
    
    # Skip benchmark evaluation if requested
    if args.skip_benchmarks:
        logger.info("⏭️ Skipping benchmark evaluation as requested")
        return
    
    # Run benchmark evaluation
    run_benchmarks(run_id, year, project_id, db_host)
    
    logger.info(f"\n🎉 Pipeline completed successfully at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()