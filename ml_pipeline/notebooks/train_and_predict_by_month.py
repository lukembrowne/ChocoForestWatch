#%% 
from ml_pipeline.polygon_loader import load_training_polygons
from ml_pipeline.extractor import TitilerExtractor
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from pathlib import Path
import numpy as np
from ml_pipeline.extractor import TitilerExtractor
from ml_pipeline.trainer import ModelTrainer
from ml_pipeline.predictor import ModelPredictor
from ml_pipeline.stac_builder import STACBuilder


# Load environment variables
load_dotenv('../.env')

# Database connection parameters
DB_HOST = "localhost"
DB_PORT = os.getenv('DB_PORT')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

print(f"DB_HOST: {DB_HOST}")
print(f"DB_PORT: {DB_PORT}")
print(f"POSTGRES_DB: {POSTGRES_DB}")
print(f"POSTGRES_USER: {POSTGRES_USER}")
print(f"POSTGRES_PASSWORD: {POSTGRES_PASSWORD}")

# Create database connection
db_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}"
engine = create_engine(db_url)


#%% 

# Set year and month
year = "2022"
month = "02"


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
extractor = TitilerExtractor(base_url="http://localhost:8083",
                             collection=f"nicfi-{year}-{month}")

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

# Extract pixels and set up Trainer
trainer = ModelTrainer(
    extractor=extractor,
    out_dir=Path("saved_models"),
)

# %% 
# Train model
trainer.train(
    training_sets=[{"gdf": gdf, "basemap_date": f"{year}-{month}"}],
    model_name="landcover_demo",
    model_description=f"First run with NICFI {year}-{month} imagery",
    model_params={"max_depth": 6, "n_estimators": 300},
)


# %% 

# import importlib
# import ml_pipeline.predictor
# importlib.reload(ml_pipeline.predictor)
# from ml_pipeline.predictor import ModelPredictor


predictor = ModelPredictor(
    model_path=trainer.saved_model_path,
    extractor=extractor,
    upload_to_spaces=True,
)

predictor.model.consecutive_to_global

#%% 

# Predict across entire collection
predictor.predict_collection(
    basemap_date=f"{year}-{month}",
    collection=f"nicfi-{year}-{month}",
    pred_dir=f"prediction_cogs/{year}/{month}",
)
# %%

# Testing out adding predictions to the pgstac database

builder = STACBuilder()

builder.list_cogs(prefix=f"predictions/model/{year}/{month}")

builder.process_month(
    year=year,
    month=month,
    prefix="predictions/model", ## do not need year and month here
    collection_id=f"nicfi-pred-{year}-{month}",
    asset_key="pred",
    asset_roles=["classification"],
    asset_title="Land‑cover classes (RF v1)",
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
