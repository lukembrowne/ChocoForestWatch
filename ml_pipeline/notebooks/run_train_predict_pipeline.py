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
4. Optionally processes ChocoForestWatch dataset into unified dataset structure
5. Optionally runs dataset evaluations

The script uses subprocess to run train_and_predict_by_month.py for each month,
which handles:
- Loading training polygons from specified database (local/remote)
- Extracting pixel data from NICFI imagery
- Training a Random Forest model
- Making predictions across target areas
- Saving results and uploading to cloud storage

Usage:

# Full pipeline: train models, generate composites, run benchmarks
poetry run python run_train_predict_pipeline.py \
  --step all \
  --start_month 1 --end_month 12 \
  --year 2022 \
  --project_id 7 \
  --run_id "test_2025_07_11" \
  --db-host "remote"

# Run only training step
poetry run python run_train_predict_pipeline.py \
  --step training \
  --start_month 1 --end_month 12 \
  --year 2022 \
  --project_id 7 \
  --run_id "test_2025_07_11" \
  --db-host "remote"

# Run only composites step
poetry run python run_train_predict_pipeline.py \
  --step composites \
  --year 2022 \
  --project_id 7 \
  --run_id "test_2025_07_11" \
  --db-host "remote"

# Run only benchmarks step
poetry run python run_train_predict_pipeline.py \
  --step benchmarks \
  --year 2022 \
  --project_id 7 \
  --run_id "test_2025_07_11" \
  --db-host "remote"

Database Configuration:
- Use --db-host "local" for development with local database
- Use --db-host "remote" for production with remote database
- COG spatial filtering is now done directly via database queries (no SSH tunnel needed)

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
    
    # Core arguments
    parser.add_argument("--year", type=str, required=True, help="Year for the pipeline")
    parser.add_argument("--project_id", type=int, required=True, help="Project ID for training polygons")
    parser.add_argument("--run_id", type=str, required=True, help="Unique identifier for this pipeline run")
    parser.add_argument("--db-host", type=str, choices=["local", "remote"], default="local", 
                       help="Database host configuration: 'local' for localhost, 'remote' for production database")
    
    # Training arguments (only required for training step)
    parser.add_argument("--start_month", type=int, help="Starting month (1-12) - required for training")
    parser.add_argument("--end_month", type=int, help="Ending month (1-12) - required for training")
    
    # Step selection - choose which steps to run
    parser.add_argument("--step", type=str, choices=["training", "composites", "cfw-processing", "benchmarks", "all"], 
                       default="all", help="Which step to run (default: all)")
    
    # Feature engineering options
    parser.add_argument("--features", type=str, nargs="*", choices=["ndvi", "ndwi"], 
                       default=[], help="Feature extractors to use (e.g., --features ndvi ndwi)")
    
    return parser.parse_args()

def validate_arguments(args):
    """Validate command line arguments."""
    # Validate month range (only if training step is selected)
    if args.step in ["training", "all"]:
        if args.start_month is None or args.end_month is None:
            logger.error("❌ --start_month and --end_month are required for training step")
            sys.exit(1)
        if args.start_month < 1 or args.start_month > 12:
            logger.error("❌ start_month must be between 1 and 12")
            sys.exit(1)
        if args.end_month < 1 or args.end_month > 12:
            logger.error("❌ end_month must be between 1 and 12")
            sys.exit(1)
        if args.start_month > args.end_month:
            logger.error("❌ start_month must be <= end_month")
            sys.exit(1)

def process_quad_with_local(quad_name: str, run_id: str, year: str):
    """Process a single quad for composite generation using local files only."""
    try:
        with CompositeGenerator(run_id=run_id, year=year) as composite_gen:
            # Generate composite locally only - no S3 upload
            local_path = composite_gen.generate_composite(quad_name=quad_name, skip_s3_upload=True, use_local_files=True)
            
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
        # Look for local prediction files
        ml_pipeline_dir = Path(__file__).parent.parent  # Go up from notebooks to ml_pipeline
        local_pred_dir = ml_pipeline_dir / "runs" / run_id / "prediction_cogs" / year / "01"
        
        logger.info(f"📁 Looking for local prediction files in: {local_pred_dir}")
        
        if not local_pred_dir.exists():
            raise FileNotFoundError(f"Local prediction directory not found: {local_pred_dir}")
        
        local_files = list(local_pred_dir.glob("*.tif*"))
        
        if not local_files:
            raise FileNotFoundError(f"No prediction files found in: {local_pred_dir}")
        
        logger.info(f"📍 Found {len(local_files)} local prediction files")
        
        # Extract quad names from local filenames
        quads = list(set(f.name.split('_')[0] for f in local_files))
        logger.info(f"📍 Extracted {len(quads)} unique quads from local files")
        logger.info(f"🔍 Example quads: {quads[:4] if len(quads) >= 4 else quads}")
        
        # Generate composites in parallel (limited to avoid overwhelming storage)  
        results = Parallel(n_jobs=2, prefer="processes")(
            delayed(process_quad_with_local)(quad_name=quad, run_id=run_id, year=year)
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
                merged_key = composite_gen.merge_composites(use_local_files=True)
                if merged_key:
                    logger.info(f"✅ Successfully merged composites: {merged_key}")
                    use_merged = True
                else:
                    logger.warning("⚠️  Merge failed, using individual COGs")
                    use_merged = False
        else:
            logger.info("ℹ️  Only one composite generated, skipping merge")
            use_merged = False
        
        # Note: STAC collection creation is handled by the cfw-processing step
        # to avoid redundant collection creation and S3 dependency issues
        logger.info("📚 Skipping STAC creation - will be handled by cfw-processing step")
        
    except Exception as e:
        logger.error(f"❌ Error during composite generation: {str(e)}")

def process_cfw_dataset_for_pipeline(run_id: str, year: str, db_host: str = "local"):
    """Process the ChocoForestWatch dataset created by this pipeline run."""
    logger.info("\n🎨 Processing ChocoForestWatch dataset for unified dataset structure...")
    
    try:
        # Import here to avoid circular imports
        sys.path.append(str(Path(__file__).parent))
        from process_forest_cover_rasters import process_cfw_dataset
        
        # Look for merged composite file from this run
        ml_pipeline_dir = Path(__file__).parent.parent  # Go up from notebooks to ml_pipeline
        runs_dir = ml_pipeline_dir / "runs" / run_id / "composites"
        
        # Find the merged composite file
        merged_files = list(runs_dir.glob(f"{run_id}_{year}_merged_composite.tif"))
        
        if not merged_files:
            logger.warning(f"⚠️  No merged composite found for {run_id}-{year}, looking for individual composites...")
            # Look for any composite files if merged doesn't exist
            composite_files = list(runs_dir.glob(f"*_{year}_forest_cover.tif"))
            if composite_files:
                input_path = str(composite_files[0])  # Use first one found
                logger.info(f"📄 Using individual composite: {input_path}")
            else:
                logger.error(f"❌ No composite files found in {runs_dir}")
                return False
        else:
            input_path = str(merged_files[0])
            logger.info(f"📄 Using merged composite: {input_path}")
        
        # Process the CFW dataset
        success = process_cfw_dataset(
            run_id=run_id,
            year=year,
            input_path=input_path,
            boundary_geojson_path=None,  # Could be made configurable
            dry_run=False,
            db_host=db_host,
            asset_title=f"ChocoForestWatch - {run_id.replace('_', ' ').title()} {year}",
            description=f"ChocoForestWatch {run_id} Annual Forest Cover Dataset {year} for Western Ecuador"
        )
        
        if success:
            logger.info(f"✅ Successfully processed ChocoForestWatch dataset: cfw-{run_id}-{year}")
        else:
            logger.error(f"❌ Failed to process ChocoForestWatch dataset: cfw-{run_id}-{year}")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Error processing ChocoForestWatch dataset: {str(e)}")
        return False

def run_dataset_evaluation(run_id: str, year: str, project_id: int, db_host: str = "local"):
    """Run evaluation against all datasets (external + ChocoForestWatch)."""
    logger.info("\n🏆 Running dataset evaluation...")
    
    # List of dataset collections to evaluate
    dataset_collections = [
        # Our own ChocoForestWatch predictions
        f"datasets-cfw-{run_id}-{year}",          # Our annual composite
        
        # External datasets
        "datasets-hansen-tree-cover-2022",        # Hansen Global Forest Change
        "datasets-mapbiomes-2022",                # MapBiomas
        "datasets-esa-landcover-2020",            # ESA WorldCover
        "datasets-jrc-forestcover-2020",          # JRC Global Forest Cover
        "datasets-palsar-2020",                   # PALSAR Forest/Non-Forest
        "datasets-wri-treecover-2020",            # WRI Tree Cover
    ]
    
    logger.info(f"📊 Evaluating {len(dataset_collections)} dataset collections")
    
    # Loop through each dataset collection
    successful_benchmarks = 0
    for collection in dataset_collections:
        logger.info(f"\n📈 Evaluating dataset: {collection}")
        logger.info("-" * 80)
        
        try:
            tester = BenchmarkTester(
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
    
    logger.info(f"\n🏁 Dataset evaluation completed: {successful_benchmarks}/{len(dataset_collections)} successful")
    
    # Generate summary visualizations if we have results
    if successful_benchmarks > 0:
        logger.info("\n📊 Generating dataset evaluation summary charts...")
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
        logger.warning("⚠️ No successful dataset evaluations - skipping summary chart generation")

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
    step = args.step
    
    # Log pipeline configuration
    logger.info(f"🚀 Starting ML Pipeline - Step: {step}")
    logger.info(f"📅 Year: {year}")
    if step in ["training", "all"]:
        logger.info(f"📅 Months: {args.start_month}-{args.end_month}")
    logger.info(f"📋 Project ID: {project_id}")
    logger.info(f"🏃 Run ID: {run_id}")
    logger.info(f"🗄️  Database: {db_host}")
    logger.info("=" * 60)
    
    # Create run manager for organizing results
    rm = RunManager(run_id=run_id)  # Uses ml_pipeline/runs/ automatically
    logger.info(f"📁 Run directory: {rm.run_path}")

    # Execute based on selected step
    if step == "training":
        run_training_step(args, rm)
    elif step == "composites":
        generate_composites(run_id, year, db_host)
    elif step == "cfw-processing":
        process_cfw_dataset_for_pipeline(run_id, year, db_host)
    elif step == "benchmarks":
        run_dataset_evaluation(run_id, year, project_id, db_host)
    elif step == "all":
        # Run all steps in sequence
        run_training_step(args, rm)
        generate_composites(run_id, year, db_host)
        process_cfw_dataset_for_pipeline(run_id, year, db_host)
        run_dataset_evaluation(run_id, year, project_id, db_host)
    
    logger.info(f"\n🎉 Pipeline step '{step}' completed successfully at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def run_training_step(args, rm):
    """Run the training and prediction step."""
    logger.info("🏋️ Starting Training & Prediction Step")
    
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
    
    for m in tqdm(range(args.start_month, args.end_month + 1), desc=f"Processing months for {args.year}"):
        month = f"{m:02d}"  # Zero-pad month for consistency
        current_month = f"{args.year}-{month}"
        
        logger.info(f"\n🗓️  Processing month {m}/{args.end_month}: {current_month}")
        logger.info("-" * 50)
        
        # Build command with database configuration
        cmd = [
            "python",
            str(script_path),
            "--year", args.year,
            "--month", month,
            "--run_dir", str(rm.run_path),
            "--project_id", str(args.project_id),
            "--db-host", args.db_host
        ]
        
        # Add feature engineering options if specified
        if hasattr(args, 'features') and args.features:
            cmd.extend(["--features"] + args.features)
        
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
    logger.info("📊 TRAINING & PREDICTION SUMMARY")
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
            retry_cmd = f"python {script_path} --year {args.year} --month {month} --run_dir {rm.run_path} --project_id {args.project_id} --db-host {args.db_host}"
            logger.info(f"   {retry_cmd}")
    
    # Only proceed if we have some successful months
    if not successful_months:
        logger.error("❌ No months processed successfully. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()