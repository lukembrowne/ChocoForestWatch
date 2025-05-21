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
else:
    # Default values for interactive IPython session if not run from command line
    year = "2022"
    month = "01"
    run_dir = PosixPath('runs/20250520T2325_rf_ndvi_2022/2022_01')
    run_id = run_dir.parts[1]

#%%
if run_dir is None:                 
    rm = RunManager()
    run_dir = rm.new_run(tag=f"rf_{year}{month}")            


#%% 
gdf = load_training_polygons(
    engine,
    project_id=1,
    basemap_date=f"{year}-{month}",
)

gdf.head()

# Print number of training polygons
print(f"Number of training polygons: {len(gdf)}")

#%% 
# Extract pixels using the extractor - this is the same as the extractor in the trainer

# Extract pixels from NICFI collection
extractor = TitilerExtractor(
    base_url="http://localhost:8083",
    collection=f"nicfi-{year}-{month}",
    band_indexes=[1, 2, 3, 4]  # Example band indexes for RGB+NIR
)

# Test
# extractor.get_all_cog_urls(collection="nicfi-2022-01")

# Test it out
# X, y, fids = extractor.extract_pixels(gdf, collection="nicfi-2022-01")

# print("\nTitilerExtractor results:")
# print(f"Total number of pixels: {len(X)}")
# print(f"Number of unique classes: {len(np.unique(y))}")
# print(f"Shape of X: {X.shape}")
# print(f"Shape of y: {y.shape}")
# print(f"Number of unique feature IDs: {len(np.unique(fids))}")



#%% 
# Train model
config = TrainerConfig(cache_dir=run_dir / "data_cache")

trainer = ModelTrainer(
    extractor=extractor,
    out_dir=run_dir / "saved_models",
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
with open(run_dir / "metrics.json", "w") as f:
    json.dump(metrics, f)


# %% 

print("Initializing ModelPredictor...")
predictor = ModelPredictor(
    model_path=trainer.saved_model_path,
    extractor=extractor,
    upload_to_s3=True,
    s3_path=f"predictions/{run_id}/",
)

#%% 

print("Predicting across entire collection...")

# Predict across entire collection
predictor.predict_collection(
    basemap_date=f"{year}-{month}",
    collection=f"nicfi-{year}-{month}",
    pred_dir=run_dir / f"prediction_cogs/{year}/{month}",
)



# %%

# Add predictions to the pgstac database

builder = STACBuilder()

print("Adding predictions to the STAC database...")

builder.process_month(
    year=year,
    month=month,
    prefix_on_s3=f"predictions/{run_id}", ## do not need year and month here
    collection_id=f"nicfi-pred-{year}-{month}",
    asset_key="data",
    asset_roles=["classification"],
    asset_title=f"Land‑cover classes - {run_dir.name}",
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
