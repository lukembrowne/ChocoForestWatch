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

from ml_pipeline.db_utils import get_db_connection

engine = get_db_connection()


#%% 

# Set year and month
year = "2022"
month = "06"


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
trainer = ModelTrainer(
    extractor=extractor,
    out_dir=Path("saved_models"),
)

# %% 
# Train model
npz = trainer.prepare_training_data(training_sets = [{"gdf": gdf, "basemap_date": f"{year}-{month}"}], 
                                    cache_name = f"pixels_{year}_{month}.npz")


#%% 
model_path, metrics = trainer.fit_prepared_data(npz, model_name=f"nicfi-{year}-{month}")  

print(metrics)
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
    asset_key="data",
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
