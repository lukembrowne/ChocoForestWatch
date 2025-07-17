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

# Complete pipeline with automatic tuning + training (RECOMMENDED)
poetry run python run_train_predict_pipeline.py \
  --step all \
  --start_month 1 --end_month 12 \
  --year 2022 \
  --project_id 7 \
  --run_id "tuning_test_2025_07_14" \
  --db-host "remote" \
  --features ndvi ndwi evi savi brightness water_detection shadow \
  --boundary-geojson shapefiles/Ecuador-DEM-900m-contour.geojson \
  --tune-trials 15

# This automatically: 1) runs hyperparameter tuning, 2) trains all monthly models 
# with optimized parameters, 3) generates composites, 4) processes datasets, 5) runs benchmarks

Database Configuration:
- Use --db-host "local" for development with local database
- Use --db-host "remote" for production with remote database

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
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from ml_pipeline.run_manager import RunManager     
from ml_pipeline.composite_generator import CompositeGenerator
from tqdm import tqdm
from joblib import Parallel, delayed
from ml_pipeline.s3_utils import list_files
from ml_pipeline.benchmark_tester import BenchmarkTester
from ml_pipeline.benchmark_metrics_io import create_benchmark_summary_charts
# from ml_pipeline.dataset_registration import register_cfw_dataset  # Disabled: datasets now managed via JSON config
from ml_pipeline.hyperparameter_tuner import HyperparameterTuner, run_hyperparameter_tuning
from ml_pipeline.tuning_reporter import generate_tuning_report
from ml_pipeline.tuning_configs import TuningConfig

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
    parser.add_argument("--step", type=str, choices=["training", "tuning", "composites", "cfw-processing", "benchmarks", "all"], 
                       default="all", help="Which step to run (default: all)")
    
    # Feature engineering options
    parser.add_argument("--features", type=str, nargs="*", 
                       choices=["ndvi", "ndwi", "evi", "savi", "brightness", "water_detection", "shadow"], 
                       default=[], help="Feature extractors to use (e.g., --features ndvi ndwi evi)")
    
    # Hyperparameter tuning options
    parser.add_argument("--tune-trials", type=int, default=25, help="Number of tuning trials (default: 25)")
    parser.add_argument("--tune-month", type=int, help="Specific month for tuning (1-12, defaults to first month)")
    parser.add_argument("--tune-random-state", type=int, default=42, help="Random state for tuning reproducibility")
    
    # Hyperparameter loading options
    parser.add_argument("--tune-run-id", type=str, help="Load hyperparameters from specific tuning run ID")
    parser.add_argument("--skip-tuning", action="store_true", help="Skip hyperparameter tuning in 'all' step")
    parser.add_argument("--use-default-params", action="store_true", help="Use default XGBoost parameters instead of tuned ones")
    
    # Boundary configuration
    parser.add_argument("--boundary-geojson", type=str, 
                       help="Path to GeoJSON file for boundary masking (optional, used for CFW dataset processing)")
    
    return parser.parse_args()

def log_command_to_file(run_manager: RunManager) -> None:
    """
    Log the full command used to run this pipeline to a file in the run directory.
    This helps with reproducibility and tracking of experiments.
    """
    # Reconstruct the command from sys.argv
    command_parts = ["poetry", "run", "python"] + sys.argv
    
    # Create multiline command with proper escaping
    first_part = f"{command_parts[0]} {command_parts[1]} {command_parts[2]}"
    remaining_parts = command_parts[3:]
    full_command = first_part + " \\\n  " + " \\\n  ".join(remaining_parts)
    
    # Create command log file in run directory
    log_file = run_manager.run_path / "run_commands.log"
    
    # Prepare log entry with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    separator = "=" * 80
    
    log_entry = f"""
# Pipeline Run Command Log
# Generated on: {timestamp}
# Working directory: {os.getcwd()}

{full_command}

# Alternative single-line format:
{' '.join(sys.argv)}

{separator}
"""
    
    # Write to log file (append mode to preserve history)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    logger.info(f"📝 Command logged to: {log_file}")
    logger.info(f"🔄 To reproduce this run, use:")
    logger.info(f"   {full_command}")

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
    
    # Validate tuning arguments (for both tuning step and all step)
    if args.step in ["tuning", "all"]:
        if args.tune_month is not None:
            if args.tune_month < 1 or args.tune_month > 12:
                logger.error("❌ --tune-month must be between 1 and 12")
                sys.exit(1)
        if args.tune_trials < 1:
            logger.error("❌ --tune-trials must be positive")
            sys.exit(1)
    
    # Validate parameter loading options
    if args.tune_run_id and args.use_default_params:
        logger.error("❌ Cannot use both --tune-run-id and --use-default-params")
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

def load_best_hyperparameters(run_manager: RunManager, tuning_run_id: str = None) -> Optional[dict]:
    """
    Load best hyperparameters from tuning results.
    
    Parameters
    ----------
    run_manager : RunManager
        Current run manager instance.
    tuning_run_id : str, optional
        Specific tuning run ID to load parameters from. If None, uses current run.
        
    Returns
    -------
    Optional[dict]
        Best hyperparameters dictionary, or None if not found.
    """
    # Determine which run to check for parameters
    if tuning_run_id is not None:
        # Load from specified tuning run
        tuning_run_path = run_manager.run_path.parent / tuning_run_id
        source_desc = f"tuning run '{tuning_run_id}'"
    else:
        # Load from current run
        tuning_run_path = run_manager.run_path
        source_desc = "current run"
    
    # Check for best parameters file
    best_params_file = tuning_run_path / "best_hyperparameters.json"
    
    if not best_params_file.exists():
        logger.debug(f"No hyperparameters found in {source_desc} at: {best_params_file}")
        return None
    
    try:
        with open(best_params_file, 'r') as f:
            params = json.load(f)
        
        logger.info(f"✅ Loaded hyperparameters from {source_desc}")
        logger.info(f"📋 Parameters: {len(params)} total")
        
        # Log key parameters for visibility
        key_params = ['n_estimators', 'max_depth', 'learning_rate']
        for param in key_params:
            if param in params:
                logger.info(f"   {param}: {params[param]}")
        
        return params
        
    except Exception as e:
        logger.error(f"❌ Failed to load hyperparameters from {source_desc}: {e}")
        return None

def save_parameters_for_monthly_training(run_manager: RunManager, parameters: dict) -> Path:
    """
    Save hyperparameters in a standard location for monthly training scripts to auto-load.
    
    Parameters
    ----------
    run_manager : RunManager
        Current run manager instance.
    parameters : dict
        Hyperparameters to save.
        
    Returns
    -------
    Path
        Path to the saved parameters file.
    """
    # Save to standard location that monthly scripts can find
    params_file = run_manager.run_path / "training_hyperparameters.json"
    
    with open(params_file, 'w') as f:
        json.dump(parameters, f, indent=2)
    
    logger.info(f"💾 Saved training parameters to: {params_file}")
    return params_file

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

def process_cfw_dataset_for_pipeline(run_id: str, year: str, db_host: str = "local", boundary_geojson_path: Optional[str] = None):
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
            boundary_geojson_path=boundary_geojson_path,
            dry_run=False,
            db_host=db_host,
            asset_title=f"ChocoForestWatch - {run_id.replace('_', ' ').title()} {year}",
            description=f"ChocoForestWatch {run_id} Annual Forest Cover Dataset {year} for Western Ecuador"
        )
        
        if success:
            logger.info(f"✅ Successfully processed ChocoForestWatch dataset: cfw-{run_id}-{year}")
            
            # Dataset registration disabled - datasets now managed via JSON config
            # To add new CFW datasets, manually update backend/djangocfw/core/datasets.json
            logger.info(f"📋 Dataset generated: datasets-cfw-{run_id}-{year}")
            logger.info("ℹ️  To make this dataset available in the frontend, manually add it to backend/djangocfw/core/datasets.json")
                
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
        "datasets-mapbiomas-2022",                # MapBiomas
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

def run_hyperparameter_tuning_step(args, rm):
    """Run hyperparameter tuning for optimal model parameters."""
    logger.info("🔧 Starting Hyperparameter Tuning Step")
    
    # Determine which month to use for tuning
    tune_month = args.tune_month if args.tune_month is not None else 1
    tune_month_str = f"{tune_month:02d}"
    
    logger.info(f"🗓️  Using month {tune_month} for hyperparameter tuning")
    
    # Get path to the monthly processing script for data preparation
    script_path = Path(__file__).parent / "train_and_predict_by_month.py"
    if not script_path.exists():
        logger.error(f"❌ Could not find script at {script_path}")
        sys.exit(1)
    
    # First, prepare training data for the tuning month (extract pixels only)
    logger.info("📊 Preparing training data for tuning...")
    
    # Import here to avoid issues with sys path
    sys.path.append(str(Path(__file__).parent))
    
    try:
        from train_and_predict_by_month import setup_trainer_and_extractor
        
        # Setup trainer and extractor using the same logic as monthly training
        trainer, extractor = setup_trainer_and_extractor(
            year=args.year,
            month=tune_month_str,
            run_dir=rm.run_path,
            project_id=args.project_id,
            db_host=args.db_host,
            features=getattr(args, 'features', [])
        )
        
        # Prepare training data (extract and cache pixels)
        npz_cache_name = f"tune_data_{args.year}_{tune_month_str}.npz"
        
        logger.info("🎯 Extracting training polygons and pixel data...")
        # This will extract pixels from the database for the specified month
        # We need to call the data preparation directly since we have the trainer
        
        # Get training sets from the database (similar to train_and_predict_by_month.py)
        from ml_pipeline.polygon_loader import load_training_polygons
        from ml_pipeline.db_utils import get_db_connection
        
        # Set up database connection
        logger.info(f"🗄️  Connecting to {args.db_host} database...")
        engine = get_db_connection(host=args.db_host)
        logger.info(f"✅ Database connection established")
        
        # Load training polygons
        logger.info(f"📊 Loading training polygons for project {args.project_id}, date {args.year}-{tune_month_str}...")
        gdf = load_training_polygons(
            engine,
            project_id=args.project_id,
            basemap_date=f"{args.year}-{tune_month_str}",
        )
        
        logger.info(f"📍 Found {len(gdf)} training polygons for {args.year}-{tune_month_str}")
        
        if len(gdf) == 0:
            logger.error(f"❌ No training data found for {args.year}-{tune_month_str}")
            sys.exit(1)
        
        # Format training sets for trainer
        training_sets = [{"gdf": gdf, "basemap_date": f"{args.year}-{tune_month_str}"}]
        
        # Prepare training data cache
        npz_path = trainer.prepare_training_data(
            training_sets=training_sets,
            cache_name=npz_cache_name,
            overwrite=False  # Use cache if available
        )
        
        logger.info(f"✅ Training data prepared: {npz_path}")
        
    except ImportError as e:
        logger.error(f"❌ Failed to import required modules: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to prepare training data: {e}")
        sys.exit(1)
    
    # Run hyperparameter tuning
    logger.info(f"🎯 Starting hyperparameter tuning with {args.tune_trials} trials")
    
    try:
        # Setup tuning configuration
        tuning_config = TuningConfig.create_config(args.tune_trials)
        
        logger.info(f"🔬 Will run {tuning_config['n_trials']} experiments")
        logger.info(f"📋 Tuning parameters: {list(tuning_config['parameters'].keys())}")
        
        # Run tuning
        best_result = run_hyperparameter_tuning(
            trainer=trainer,
            run_manager=rm,
            npz_path=npz_path,
            n_trials=args.tune_trials,
            random_state=args.tune_random_state
        )
        
        logger.info(f"🏆 Tuning completed! Best CV F1-macro: {best_result.cv_f1_macro_mean:.4f}")
        logger.info(f"📊 Best test F1-macro: {best_result.test_f1_macro:.4f}")
        logger.info(f"📊 Best test accuracy: {best_result.test_accuracy:.4f}")
        
        # Generate tuning report
        logger.info("📝 Generating tuning analysis report...")
        tuning_dir = rm.run_path / "hyperparameter_tuning"
        report_path = generate_tuning_report(tuning_dir)
        logger.info(f"📄 Tuning report generated: {report_path}")
        
        # Print best parameters for easy copying
        logger.info("\n" + "="*60)
        logger.info("🎯 BEST HYPERPARAMETERS FOUND")
        logger.info("="*60)
        for param, value in best_result.parameters.items():
            if param != 'random_state':
                logger.info(f"  {param}: {value}")
        logger.info("="*60)
        
        # Save best parameters to easy-to-use file
        best_params_file = rm.run_path / "best_hyperparameters.json"
        with open(best_params_file, 'w') as f:
            json.dump(best_result.parameters, f, indent=2)
        logger.info(f"💾 Best parameters saved to: {best_params_file}")
        
    except Exception as e:
        logger.error(f"❌ Hyperparameter tuning failed: {e}")
        sys.exit(1)

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
    boundary_geojson_path = getattr(args, 'boundary_geojson', None)
    
    # Log pipeline configuration
    logger.info(f"🚀 Starting ML Pipeline - Step: {step}")
    logger.info(f"📅 Year: {year}")
    if step in ["training", "all"]:
        logger.info(f"📅 Months: {args.start_month}-{args.end_month}")
    elif step == "tuning":
        tune_month = args.tune_month if args.tune_month is not None else 1
        logger.info(f"🔧 Tuning month: {tune_month}")
        logger.info(f"🎯 Tuning trials: {args.tune_trials}")
    logger.info(f"📋 Project ID: {project_id}")
    logger.info(f"🏃 Run ID: {run_id}")
    logger.info(f"🗄️  Database: {db_host}")
    if getattr(args, 'features', []):
        logger.info(f"🔬 Features: {', '.join(args.features)}")
    if boundary_geojson_path:
        logger.info(f"🗺️  Boundary file: {boundary_geojson_path}")
    logger.info("=" * 60)
    
    # Create run manager for organizing results
    rm = RunManager(run_id=run_id)  # Uses ml_pipeline/runs/ automatically
    logger.info(f"📁 Run directory: {rm.run_path}")
    
    # Log the command used to run this pipeline
    log_command_to_file(rm)

    # Execute based on selected step
    if step == "training":
        run_training_step(args, rm)
    elif step == "tuning":
        run_hyperparameter_tuning_step(args, rm)
    elif step == "composites":
        generate_composites(run_id, year, db_host)
    elif step == "cfw-processing":
        process_cfw_dataset_for_pipeline(run_id, year, db_host, boundary_geojson_path)
    elif step == "benchmarks":
        run_dataset_evaluation(run_id, year, project_id, db_host)
    elif step == "all":
        # Run all steps in sequence
        if not args.skip_tuning:
            # Run hyperparameter tuning first (unless explicitly skipped)
            logger.info("🔧 Running hyperparameter tuning as part of complete pipeline...")
            run_hyperparameter_tuning_step(args, rm)
        else:
            logger.info("⏭️  Skipping hyperparameter tuning (--skip-tuning specified)")
        
        # Run training with tuned parameters
        run_training_step(args, rm)
        generate_composites(run_id, year, db_host)
        process_cfw_dataset_for_pipeline(run_id, year, db_host, boundary_geojson_path)
        run_dataset_evaluation(run_id, year, project_id, db_host)
    
    logger.info(f"\n🎉 Pipeline step '{step}' completed successfully at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def run_training_step(args, rm):
    """Run the training and prediction step."""
    logger.info("🏋️ Starting Training & Prediction Step")
    
    # Load hyperparameters if available and not using default parameters
    hyperparameters = None
    if not args.use_default_params:
        # Try to load from specified tuning run or current run
        hyperparameters = load_best_hyperparameters(rm, args.tune_run_id)
        
        if hyperparameters is not None:
            # Save parameters for monthly training scripts to auto-load
            save_parameters_for_monthly_training(rm, hyperparameters)
            logger.info("🎯 Will use tuned hyperparameters for all monthly training")
        else:
            if args.tune_run_id:
                logger.warning(f"⚠️  Could not load parameters from tuning run '{args.tune_run_id}', using defaults")
            else:
                logger.info("ℹ️  No tuned parameters found, using XGBoost defaults")
    else:
        logger.info("🔧 Using default XGBoost parameters (--use-default-params specified)")
    
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