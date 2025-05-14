Specification Document: ChocoForestWatch Centralized ML Pipeline (Phase 1)
Version: 1.0
Date: 2025-05-12

1. Introduction & Goal

This document specifies the development of a standalone Python-based pipeline for training a Random Forest model and generating monthly land cover/deforestation predictions for Western Ecuador using Planet NICFI mosaics. This replaces the previous user-driven front-end training process with a centralized, developer-managed workflow. The goal is to create reproducible, maintainable scripts for model training and prediction, optimized for easier iteration during development. Automation (e.g., cron scheduling) is out of scope for this phase.

2. Scope

In Scope:
* Setting up a dedicated Python environment using Poetry.
* Creating scripts for data preparation (fetching training polygons from PostGIS, sampling imagery).
* Creating a script for training a Random Forest model.
* Creating a script for running predictions on monthly mosaics for a given month
* Saving trained models to disk.
* Saving prediction outputs as Cloud-Optimized GeoTIFFs (COGs).
* Storing metadata about models and predictions in the existing PostGIS database.
* Using environment variables for configuration (database credentials, paths).

Out of Scope:
* Automatic scheduling/triggering of the pipeline (manual execution only for now).
* Downloading/acquiring the Planet NICFI mosaics (they are accessible via S3 from a Digital Oceans space)
* Advanced model evaluation beyond basic metrics printed during training.
* Web interface integration beyond storing prediction metadata in the database (the existing Django app would need separate modifications to display these).
* Production Docker container setup for running these scripts (focus is on Poetry dev environment and script logic first).

3. Project Setup

Directory Structure: Create a new directory named ml_pipeline at the root of the ChocoForestWatch repository.
ChocoForestWatch/
├── backend/
├── frontend/
├── data/
│   ├── models/      # Output directory for trained models
│   └── predictions/ # Output directory for prediction rasters
├── ml_pipeline/     # New directory for this pipeline
│   ├── pyproject.toml
│   ├── README.md
│   ├── .env.example # Example environment file
│   ├── src/          # Source code directory
│   │   ├── __init__.py
│   │   ├── config.py      # Handles loading .env variables
│   │   ├── db.py          # Database connection/query functions
│   │   ├── prepare_data.py
│   │   ├── train_model.py
│   │   ├── run_predictions.py
│   │   └── utils.py       # Common utility functions (e.g., raster I/O)
│   └── notebooks/     # Optional: For exploration
├── docker-compose.yml
└── ... (other existing files)
Environment Management (Poetry):
Navigate into the ml_pipeline directory.
Initialize Poetry: poetry init (follow prompts)
Add dependencies:
Bash

poetry add python="^3.10" # Or your preferred Python 3 version
poetry add scikit-learn pandas joblib python-dotenv SQLAlchemy GeoAlchemy2 psycopg2-binary rasterio geopandas pyproj shapely tqdm # Core dependencies
poetry add jupyterlab ipykernel -G dev # Development dependencies for notebooks
This will create pyproject.toml and poetry.lock.
Configuration (.env):
Create a .env file inside ml_pipeline. Do not commit .env to Git. Add it to your .gitignore.
Create .env.example with keys but no values for repository tracking.
Required variables (adjust names/values as needed):
Code snippet

# .env.example
# PostGIS Database Credentials (should match docker-compose)
DB_HOST=db
DB_PORT=5432
DB_NAME=your_db_name # Replace with actual DB name from your .env
DB_USER=your_db_user # Replace with actual user from your .env
DB_PASSWORD=your_db_password # Replace with actual password from your .env

# Training Data Configuration
TRAINING_POLYGON_TABLE=your_polygon_table # Name of table with training polygons
TRAINING_POLYGON_GEOM_COL=geom # Geometry column name in polygon table
TRAINING_POLYGON_CLASS_COL=class_label # Column name for land cover class

# File Paths (Relative to project root or absolute paths accessible by the script runner)
# These might point inside mounted volumes if run via 'docker exec' or need mapping if run via 'docker run' later
MODEL_OUTPUT_DIR=../data/models
PREDICTION_OUTPUT_DIR=../data/predictions
PLANET_MOSAIC_DIR=/path/to/your/nicfi/mosaics # Directory containing monthly mosaics

# AOI Definition (e.g., Western Ecuador) - Use WKT or path to a GeoJSON/Shapefile
AOI_DEFINITION="path/to/western_ecuador_boundary.geojson" # Or a WKT string

# Planet API Key (if needed for direct access, otherwise assume mosaics pre-exist)
# PLANET_API_KEY=YOUR_API_KEY
Implement ml_pipeline/src/config.py to load these variables using python-dotenv and os.getenv.
4. Core Scripts (ml_pipeline/src/)

config.py:
Loads environment variables from .env using dotenv.
Provides access to configuration values.
db.py:
Uses SQLAlchemy and GeoAlchemy2 to connect to the PostGIS database using credentials from config.
Provides functions to:
Fetch training polygons within the AOI.
Create new tables (ml_models, raster_predictions) if they don't exist.
Insert records into ml_models and raster_predictions.
utils.py:
Contains helper functions, e.g.:
Raster I/O using rasterio (reading, writing COGs).
Sampling raster data at point/polygon locations.
COG creation options (tiling, compression).
prepare_data.py:
Input: Year and Month (e.g., via command-line arguments), path to the corresponding monthly mosaic.
Functionality:
Construct the path to the specific monthly mosaic (e.g., using PLANET_MOSAIC_DIR, year, month).
Load the AOI geometry from config.AOI_DEFINITION.
Use db.py to fetch training polygons (geometry and class label) that intersect the AOI.
Use rasterio and geopandas (or rasterstats) to extract pixel values from the mosaic for each training polygon. Handle potential issues like polygons spanning multiple pixels, NODATA values. Aggregate pixel values per polygon if necessary (e.g., majority class, mean values).
Structure the extracted pixel values (features) and class labels into a Pandas DataFrame.
Output: Save the prepared data (features and labels DataFrame) to a file (e.g., Feather, Parquet, or Pickle format) for the training script. Example filename: prepared_data_YYYYMM.parquet. Print the path to the output file.
train_model.py:
Input: Path to the prepared data file (from prepare_data.py), Year, Month.
Functionality:
Load the prepared data (features and labels).
Define/configure the sklearn.ensemble.RandomForestClassifier (e.g., number of trees, max depth – potentially load from config or args).
Split data for training/validation (optional but recommended).
Train the Random Forest model.
(Optional) Evaluate the model on a validation set and print metrics (accuracy, confusion matrix, etc.).
Construct the model output path using config.MODEL_OUTPUT_DIR, year, and month (e.g., ../data/models/rf_model_YYYYMM.joblib).
Save the trained model using joblib.dump.
Use db.py to insert a record into the ml_models table (see Section 7).
Output: Saved model file. Log messages indicating success and metrics.
run_predictions.py:
Input: Year, Month (to identify model and mosaic), path to the specific monthly mosaic.
Functionality:
Construct the path to the trained model file (using year/month). Load using joblib.load.
Construct the path to the input monthly mosaic file.
Use rasterio to open the input mosaic. Read metadata (profile).
Process the raster in chunks (windows) to handle large files without exceeding memory:
For each chunk: read pixel data, reshape for the model, run model.predict(), reshape back to 2D chunk shape.
Prepare the output raster profile (update dtype, set compression, tiling for COG).
Use rasterio to write the prediction chunks to a new COG file in config.PREDICTION_OUTPUT_DIR. Example filename: prediction_YYYYMM.tif.
Use db.py to insert a record into the raster_predictions table (see Section 7).
Output: Prediction COG file. Log messages indicating progress and success.
5. Data Flow

Input: Planet NICFI Monthly Mosaic (.tif), Training Polygons (PostGIS).
prepare_data.py: Reads polygons (PostGIS) -> Samples mosaic (.tif) -> Writes structured training data (.parquet).
train_model.py: Reads training data (.parquet) -> Trains RF -> Writes model (.joblib) -> Writes model metadata (PostGIS).
run_predictions.py: Reads model (.joblib) & mosaic (.tif) -> Predicts chunk by chunk -> Writes prediction raster (.tif COG) -> Writes prediction metadata (PostGIS).
Output: Model files (.joblib), Prediction COGs (.tif), Metadata records (PostGIS).
6. Configuration

Refer to Section 3.3 (.env file). Ensure ml_pipeline/src/config.py correctly loads and provides these values.

7. Database Interaction Details

Use connection details from .env.
Assume the training polygon table (TRAINING_POLYGON_TABLE) exists with geometry (TRAINING_POLYGON_GEOM_COL) and class label (TRAINING_POLYGON_CLASS_COL).
New Table: ml_models (Create if not exists)
model_id (SERIAL PRIMARY KEY)
model_filename (VARCHAR, unique) - e.g., rf_model_YYYYMM.joblib
model_type (VARCHAR) - e.g., 'RandomForestClassifier'
trained_at (TIMESTAMPZ DEFAULT NOW())
training_data_source (VARCHAR) - e.g., path to prepared_data_YYYYMM.parquet
parameters (JSONB) - Store model hyperparameters (n_estimators, etc.)
metrics (JSONB, optional) - Store evaluation metrics (accuracy, etc.)
year (INTEGER)
month (INTEGER)
New Table: raster_predictions (Create if not exists)
prediction_id (SERIAL PRIMARY KEY)
prediction_filename (VARCHAR, unique) - e.g., prediction_YYYYMM.tif
prediction_path (VARCHAR) - Full path or relative path from a known root (e.g., relative to PREDICTION_OUTPUT_DIR).
generated_at (TIMESTAMPZ DEFAULT NOW())
model_id (INTEGER, REFERENCES ml_models(model_id))
source_mosaic (VARCHAR) - Path or identifier of the input mosaic used.
year (INTEGER)
month (INTEGER)
aoi_definition (TEXT or Geometry) - Store AOI used for this prediction run.
8. Output Specification

Models: Saved as .joblib files in the directory specified by MODEL_OUTPUT_DIR. Filename convention: rf_model_YYYYMM.joblib.
Predictions: Saved as Cloud-Optimized GeoTIFF (.tif) files in the directory specified by PREDICTION_OUTPUT_DIR. Use LZW or Deflate compression and appropriate block sizes (e.g., 256x256 or 512x512). Filename convention: prediction_YYYYMM.tif.
9. Execution (Manual)

Ensure the PostGIS database is running (e.g., via docker-compose up db).
Ensure NICFI mosaics are available at PLANET_MOSAIC_DIR.
Ensure the .env file is populated correctly in the ml_pipeline directory.
Navigate to the ml_pipeline directory in your terminal.
Run the scripts sequentially using poetry run:
Bash

# Example for June 2025
export YEAR=2025
export MONTH=6
export MOSAIC_PATH="$PLANET_MOSAIC_DIR/nicfi_mosaic_${YEAR}-${MONTH}_analytic.tif" # Adjust actual mosaic path/naming

# Check if mosaic exists (simple example)
if [ ! -f "$MOSAIC_PATH" ]; then echo "Mosaic $MOSAIC_PATH not found!"; exit 1; fi

echo "--- Preparing Data for $YEAR-$MONTH ---"
poetry run python src/prepare_data.py --year $YEAR --month $MONTH --mosaic_path "$MOSAIC_PATH"
# (Assuming prepare_data outputs the path or uses a predictable name like prepared_data_YYYYMM.parquet)
export PREPARED_DATA_PATH="prepared_data_${YEAR}${MONTH}.parquet" # Adjust if output name differs

echo "--- Training Model for $YEAR-$MONTH ---"
poetry run python src/train_model.py --input_data "$PREPARED_DATA_PATH" --year $YEAR --month $MONTH

echo "--- Running Predictions for $YEAR-$MONTH ---"
poetry run python src/run_predictions.py --year $YEAR --month $MONTH --mosaic_path "$MOSAIC_PATH"

echo "--- Pipeline finished for $YEAR-$MONTH ---"
(Note: Command-line arguments (--year, --month, etc.) need to be implemented using argparse in the respective Python scripts).
10. Dockerization (Future Consideration)

The scripts should be written assuming they might eventually run inside a Docker container. This means:

Relying on environment variables for all configuration.
Using relative paths based on the ml_pipeline root or paths defined in environment variables (like MODEL_OUTPUT_DIR).
The database host (DB_HOST=db) should be the service name defined in docker-compose.yml.
A separate Dockerfile can be created later in ml_pipeline to build an image containing Poetry, Python, system dependencies (like GDAL), and the pipeline code, allowing execution via docker run or integration into docker-compose.