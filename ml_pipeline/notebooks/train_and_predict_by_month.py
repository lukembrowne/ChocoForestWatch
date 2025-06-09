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
from ml_pipeline.stac_builder import STACBuilder
from ml_pipeline.db_utils import get_db_connection
import argparse
from ml_pipeline.run_manager import RunManager    
from pathlib import PosixPath
import json


# Set up database connection
engine = get_db_connection()


#%% 

# --- Argument Parsing ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ML pipeline for a given year and month.")
    parser.add_argument("--year", type=str, required=True, help="Year for the pipeline (e.g., '2022')")
    parser.add_argument("--month", type=str, required=True, help="Month for the pipeline (e.g., '06')")
    parser.add_argument("--run_dir", type=str, required=True, help="Run directory for the pipeline")
    args = parser.parse_args()

    year = args.year
    month = args.month
    run_dir = Path(args.run_dir) if args.run_dir else None
    run_id = run_dir.parts[1]


#%% 
# Default values for interactive IPython session if not run from command line
year = "2022"
month = "01"
rm = RunManager("northern_choco_test_2025_05_21")


#%% 
gdf = load_training_polygons(
    engine,
    project_id=2,
    basemap_date=f"{year}-{month}",
)

gdf.head()

# Print number of training polygons
print(f"Number of training polygons: {len(gdf)}")

# If no data, break out of script
if len(gdf) == 0:
    print(f"No training polygons found for {year}-{month}. Exiting...")
    import sys
    sys.exit(0)



#%% 
# Extract pixels from NICFI collection
extractor = TitilerExtractor(
    base_url="http://localhost:8083",
    collection=f"nicfi-{year}-{month}",
    band_indexes=[1, 2, 3, 4]  # Example band indexes for RGB+NIR
)


#%% 
# Train model
config = TrainerConfig(cache_dir=rm.run_path / "data_cache") # Set cache dir

trainer = ModelTrainer(
    extractor=extractor,
    out_dir=rm.run_path / "saved_models",
    cfg=config
)

# %% 
# Train model
print("Preparing training data...")
npz = trainer.prepare_training_data(training_sets = [{"gdf": gdf, "basemap_date": f"{year}-{month}"}], 
                                    cache_name = f"pixels_{year}_{month}.npz",)


#%% 
print("Fitting model...")
model_path, metrics = trainer.fit_prepared_data(npz, 
                                                model_name=f"nicfi-{year}-{month}")  

print(metrics)

# Save metrics to run_dir
with open(rm.run_path / "metrics.json", "w") as f:
    json.dump(metrics, f)


# %% 

print("Initializing ModelPredictor...")
predictor = ModelPredictor(
    model_path=trainer.saved_model_path,
    extractor=extractor,
    upload_to_s3=True,
    s3_path=f"predictions/{rm.run_id}", # No trailing slash 
)

#%% 

print("Predicting across entire collection...")

# Predict across entire collection
predictor.predict_collection(
    basemap_date=f"{year}-{month}",
    collection=f"nicfi-{year}-{month}",
    pred_dir=rm.run_path / f"prediction_cogs/{year}/{month}",
    save_local=False
)



# %%

# Add predictions to the pgstac database
builder = STACBuilder()

print("Adding predictions to the STAC database...")

builder.process_month(
    year=year,
    month=month,
    prefix_on_s3=f"predictions/{rm.run_id}", ## do not need year and month here
    collection_id=f"{rm.run_id}-pred-{year}-{month}",
    asset_key="data",
    asset_roles=["classification"],
    asset_title=f"Land‑cover classes - {rm.run_id}",
    extra_asset_fields={
        "raster:bands": [{"nodata": 255, "data_type": "uint8"}],
        "classification:classes": [
            {"value": 0, "name": "Forest"},
            {"value": 1, "name": "Non‑Forest"},
            {"value": 2, "name": "Cloud"},
            {"value": 3, "name": "Shadow"},
            {"value": 4, "name": "Water"},
        ],
    }
)
# %%
