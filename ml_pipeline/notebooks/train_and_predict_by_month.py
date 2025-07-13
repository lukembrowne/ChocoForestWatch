#%% 
from ml_pipeline.polygon_loader import load_training_polygons
from ml_pipeline.extractor import TitilerExtractor
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from pathlib import Path
import numpy as np
from ml_pipeline.extractor import TitilerExtractor
from ml_pipeline.trainer import ModelTrainer, TrainerConfig
from ml_pipeline.predictor import ModelPredictor
from ml_pipeline.stac_builder import STACManager, STACManagerConfig
from ml_pipeline.db_utils import get_db_connection
import argparse
import logging
from ml_pipeline.run_manager import RunManager    
# Import feature engineering components
from ml_pipeline.feature_engineering import NDVIExtractor, NDWIExtractor, FeatureManager

# Configure logging for better pipeline visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress AWS credential logging noise
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('s3transfer').setLevel(logging.WARNING)


#%% 

# --- Argument Parsing ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ML pipeline for a given year and month.")
    parser.add_argument("--year", type=str, required=True, help="Year for the pipeline (e.g., '2022')")
    parser.add_argument("--month", type=str, required=True, help="Month for the pipeline (e.g., '06')")
    parser.add_argument("--run_dir", type=str, required=True, help="Run directory for the pipeline")
    parser.add_argument("--project_id", type=str, required=True, help="Project ID for the training polygons")
    parser.add_argument("--db-host", type=str, choices=["local", "remote"], default="local", 
                       help="Database host configuration: 'local' for localhost, 'remote' for production database")
    # Feature engineering options
    parser.add_argument("--features", type=str, nargs="*", choices=["ndvi", "ndwi"], 
                       default=[], help="Feature extractors to use (e.g., --features ndvi ndwi)")
    args = parser.parse_args()

    year = args.year
    month = args.month
    run_dir = Path(args.run_dir) if args.run_dir else None
    run_id = run_dir.parts[1]
    project_id = args.project_id
    db_host = getattr(args, 'db_host', 'local')  # Handle hyphenated argument
    features = args.features
    
    # Set up database connection based on configuration
    logger.info(f"🗄️  Connecting to {db_host} database...")
    engine = get_db_connection(host=db_host)
    logger.info(f"✅ Database connection established")

    #%% 
    # Default values for interactive IPython session if not run from command line

    # year = "2022"
    # month = "01"
    # run_id = "test_2025_07_11"
    # rm = RunManager(run_id)
    # run_dir = rm.run_path
    # project_id = 7
    # db_host = "remote"  # Change to "remote" for production database
    # # Set up database connection based on configuration
    # logger.info(f"🗄️  Connecting to {db_host} database...")
    # engine = get_db_connection(host=db_host)
    # logger.info(f"✅ Database connection established")



    #%% 
    # --- Load Training Data ---
    logger.info(f"📊 Loading training polygons for project {project_id}, date {year}-{month}...")
    gdf = load_training_polygons(
        engine,
        project_id=project_id,
        basemap_date=f"{year}-{month}",
    )

    gdf.head()

    # Print number of training polygons
    logger.info(f"📊 Loaded {len(gdf)} training polygons")

    # If no data, break out of script
    if len(gdf) == 0:
        logger.warning(f"⚠️  No training polygons found for {year}-{month}. Exiting...")
        import sys
        sys.exit(0)



    #%% 
    # --- Initialize Data Extractor ---
    logger.info(f"🛰️  Initializing extractor for NICFI collection {year}-{month}...")
    extractor = TitilerExtractor(
        collection=f"nicfi-{year}-{month}",
        band_indexes=[1, 2, 3, 4],  # RGB + Near-Infrared bands
        db_host=db_host  # Pass database configuration
    )
    logger.info("✅ Extractor initialized")


    #%% 
    # --- Configure Feature Engineering ---
    feature_extractors = []
    if "ndvi" in features:
        feature_extractors.append(NDVIExtractor())
        logger.info("   ✓ NDVI extractor added")
    if "ndwi" in features:
        feature_extractors.append(NDWIExtractor())
        logger.info("   ✓ NDWI extractor added")
    
    if feature_extractors:
        logger.info(f"🧪 Feature engineering enabled with {len(feature_extractors)} extractors: {[e.name for e in feature_extractors]}")
    else:
        logger.info("📊 Using base bands only (no feature engineering)")

    # --- Initialize Model Trainer ---
    logger.info(f"🤖 Setting up model trainer with cache directory: {run_dir / 'data_cache'}...")
    config = TrainerConfig(
        cache_dir=run_dir / "data_cache",
        feature_extractors=feature_extractors  # Add feature extractors to config
    ) 

    trainer = ModelTrainer(
        extractor=extractor,
        run_dir=run_dir,
        cfg=config
    )
    logger.info("✅ Trainer initialized")

    # %% 
    # --- Prepare Training Data ---
    logger.info(f"🔄 Preparing training data from {len(gdf)} polygons...")
    # Add feature suffix to cache name for differentiation
    feature_suffix = "_".join(features) if features else "base"
    cache_name = f"pixels_{year}_{month}_{feature_suffix}.npz"
    
    npz = trainer.prepare_training_data(training_sets = [{"gdf": gdf, "basemap_date": f"{year}-{month}"}], 
                                        cache_name = cache_name)
    logger.info("✅ Training data prepared")


    #%% 
    # --- Train Model ---
    logger.info("🎯 Training model on prepared data...")
    # Add feature suffix to model name for differentiation
    feature_suffix = "_".join(features) if features else "base"
    model_name = f"nicfi-{year}-{month}-{feature_suffix}"
    
    model_path, metrics = trainer.fit_prepared_data(npz, model_name=model_name)  

    #%% 
    # Print model metrics
    accuracy = metrics.get('accuracy', 'N/A')
    logger.info(f"✅ Model training completed. Overall Accuracy: {accuracy:.4f}" if isinstance(accuracy, float) else f"✅ Model training completed. Accuracy: {accuracy}")

    # Format and display key metrics in a structured way
    if metrics:
        logger.info("📊 Model Performance Summary:")
        logger.info("-" * 50)
        
        # Overall accuracy
        if 'accuracy' in metrics:
            logger.info(f"   Overall Accuracy: {metrics['accuracy']:.4f}")
        
        # Cross-validation accuracy (if available)
        if 'cv_accuracy' in metrics:
            cv_scores = metrics['cv_accuracy']
            cv_mean = sum(cv_scores) / len(cv_scores)
            cv_std = (sum((x - cv_mean) ** 2 for x in cv_scores) / len(cv_scores)) ** 0.5
            logger.info(f"   CV Accuracy: {cv_mean:.4f} ± {cv_std:.4f}")
        
        # Class-wise metrics
        if all(key in metrics for key in ['precision', 'recall', 'f1', 'classes_present']):
            logger.info("\n   📈 Class-wise Performance:")
            classes = metrics['classes_present']
            precision = metrics['precision']
            recall = metrics['recall']
            f1 = metrics['f1']
            
            for i, class_name in enumerate(classes):
                if i < len(precision) and i < len(recall) and i < len(f1):
                    logger.info(f"      {class_name:<12}: P={precision[i]:.3f}, R={recall[i]:.3f}, F1={f1[i]:.3f}")
        
        logger.info("-" * 50)
    else:
        logger.info("📊 No detailed metrics available")

    # Save metrics to run_dir
    # with open(run_dir / "metrics.json", "w") as f:
    #     json.dump(metrics, f)


    # %% 

    # --- Initialize Model Predictor ---
    logger.info("🔮 Initializing model predictor...")
    predictor = ModelPredictor(
        model_path=trainer.saved_model_path, # Path to the saved model
        extractor=extractor, # TitilerExtractor object
        upload_to_s3=False, # Upload predictions to cloud storage
        s3_path=None, # S3 path prefix
    )
    logger.info("✅ Predictor initialized")

    #%% 
    # --- Generate Predictions ---
    logger.info(f"🌍 Generating predictions across entire NICFI collection for {year}-{month}...")

    # Predict across entire collection - parallel processing for each COG
    predictor.predict_collection(
        basemap_date=f"{year}-{month}",
        collection=f"nicfi-{year}-{month}",
        pred_dir=run_dir / f"prediction_cogs/{year}/{month}",
        save_local=True,
        filter_western_ecuador=True # Only process Western Ecuador
    )
    logger.info("✅ Predictions generated and saved")



    # %%

    # --- Add Predictions to STAC Database (only if uploaded to S3) ---
    if predictor.upload_to_s3:
        # Use same database configuration as training data
        use_remote_stac = (db_host == "remote") # Will be true if db_host is "remote"
        logger.info(f"📚 Adding predictions to {'remote' if use_remote_stac else 'local'} STAC database...")

        builder = STACManager(STACManagerConfig(use_remote_db=use_remote_stac))

        builder.process_month(
            year=year,
            month=month,
            prefix_on_s3=f"predictions/{run_id}", # S3 prefix for predictions
            collection_id=f"{run_id}-pred-{year}-{month}",
            asset_key="data",
            asset_roles=["classification"],
            asset_title=f"Land‑cover classes - {run_id}",
            extra_asset_fields={
                "raster:bands": [{"nodata": 255, "data_type": "uint8"}],
                "classification:classes": [
                    {"value": 0, "name": "Forest"},
                    {"value": 1, "name": "Non‑Forest"},
                    {"value": 2, "name": "Cloud"},
                    {"value": 3, "name": "Shadow"},
                    {"value": 4, "name": "Water"},
                    {"value": 5, "name": "Haze"},
                    {"value": 6, "name": "Sensor Error"},
                ],
            }
        )
        logger.info("✅ STAC collection created for S3 predictions")
    else:
        logger.info("⏭️ Skipping STAC collection creation (predictions saved locally only)")
    logger.info(f"✅ Pipeline completed successfully for {year}-{month}")
    # %%
