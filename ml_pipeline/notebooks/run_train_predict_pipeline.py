"""
Run Training and Prediction Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This script runs a complete training and prediction pipeline for land cover classification
across all months of a specified year. It:

1. Creates a parent directory for the year-long experiment
2. For each month:
   - Creates a child directory for that month's results
   - Runs the training and prediction pipeline
   - Saves metrics for that month
3. Aggregates all monthly metrics into a summary
4. Generates annual composites from the monthly predictions in parallel

The script uses subprocess to run train_and_predict_by_month.py for each month,
which handles:
- Loading training polygons
- Extracting pixel data
- Training an XGBoost model
- Making predictions
- Saving results and metrics

Usage:
    poetry run python run_train_predict_pipeline.py

The results are organized as:
    runs/
    └── {timestamp}_{tag}_{year}/
        ├── {year}_01/
        │   ├── saved_models/
        │   ├── data_cache/
        │   └── prediction_cogs/
        ├── {year}_02/
        │   └── ...
        ├── metrics_*.json
        └── composites/
            └── {quad_name}_{year}_forest_cover.tif
"""

#%% 
import subprocess, json
from ml_pipeline.run_manager import RunManager     
from ml_pipeline.composite_generator import CompositeGenerator
from tqdm import tqdm
from joblib import Parallel, delayed
from ml_pipeline.s3_utils import list_files
from ml_pipeline.benchmark_tester import BenchmarkTester

#%% 

# Set tag
run_id = "northern_choco_test_2025_06_16" # Name for run

# Set year
year = "2022"
project_id = 6 # Project ID for the training polygons

#%% 
# One folder for the whole year-long experiment
rm = RunManager(run_id=run_id, root="runs")

#%%
# Loop through months
for m in tqdm(range(9, 10), desc=f"Processing months for {year}"):
    
    print("-"*100)
    print("-"*100)
    print("-"*100)
    month = f"{m:02d}"                                # keeps artefacts separate

    subprocess.run(
        [
            "poetry","run","python",
            "train_and_predict_by_month.py",
            "--year",  year,
            "--month", month,
            "--run_dir", str(rm.run_path),
            "--project_id", str(project_id),
        ],
    check=True,
    )

#%%
def process_quad(quad_name: str, run_id: str, year: str):
    """Process a single quad for composite generation."""
    try:
        with CompositeGenerator(run_id=run_id, year=year) as composite_gen:
            composite_gen.generate_composite(quad_name=quad_name)
        return True
    except Exception as e:
        print(f"Error processing quad {quad_name}: {str(e)}")
        return False


#%%
# Generate composites in parallel
print("\nGenerating annual composites...")

# Get list of quads from S3
s3_files = list_files(prefix=f"predictions/{run_id}/{year}/01")


def extract_quad_name(s3_file: dict) -> str:
    """Extract quad name (e.g. '567-1027') from S3 file listing."""
    # Get the filename from either key or url
    filename = s3_file['key'].split('/')[-1]  # or s3_file['url'].split('/')[-1]
    # Split on underscore and take first part
    return filename.split('_')[0]


quads = list(set(extract_quad_name(f) for f in s3_files))  # Use set to remove duplicates
print(f"Found {len(quads)} unique quads")
print("Examples of quads: ", quads[0:4])



#%% 

# Generate composites in parallel for each quad
# Need to limit number of jobs to avoid overwhelming S3
results = Parallel(n_jobs=2, prefer="processes")(
    delayed(process_quad)(quad_name=quad, run_id=run_id, year=year)
    for quad in tqdm(quads, desc="Processing quads")
)

# Check results
successful = sum(results)
failed = len(quads) - successful
print(f"Completed composite generation: {successful} successful, {failed} failed")


#%% 

# Create STAC collection so that the composites are visible in the frontend
CompositeGenerator(run_id=run_id, year=year)._create_stac_collection()


#%%
# Run benchmark evaluation against reference datasets

print("\nRunning benchmark tests…")

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

# Loop through each benchmark collection
for collection in benchmark_collections:
    print("\n" + "="*100)
    print(f"Evaluating benchmark: {collection}")
    print("="*100)
    
    try:
        tester = BenchmarkTester(
            base_url="http://localhost:8083",
            collection=collection,
            year=year,
            project_id=project_id,
            run_id=run_id,
        )
        tester.run()
    except Exception as e:
        print(f"❌  Failed to evaluate {collection}: {str(e)}")
        continue

# %%

# Playground
tester = BenchmarkTester(
            base_url="http://localhost:8083",
            collection="benchmarks-jrc-forestcover-2020",
            year=year,
            project_id=project_id,
            run_id=run_id,
        )

#%% 
tester.run()



# %%

# Testing summary stats

from ml_pipeline.summary_stats import AOISummaryStats
import json

stats = AOISummaryStats("http://localhost:8083", "benchmarks-hansen-tree-cover-2022")

with open("shapefiles/Ecuador DEM 900m contour.geojson") as f:
    aoi = json.load(f)

df = stats.summary(aoi['features'][0])

print(df.to_markdown(index=False))

# %%

from ml_pipeline.summary_stats import AOISummaryStats
import json

stats = AOISummaryStats("http://localhost:8083", "benchmarks-mapbiomes-2022")

with open("shapefiles/Ecuador DEM 900m contour.geojson") as f:
    aoi = json.load(f)

df = stats.summary(aoi['features'][0])
df

print(df.to_markdown(index=False))

# %%

from ml_pipeline.summary_stats import AOISummaryStats
import json

stats = AOISummaryStats("http://localhost:8083", "nicfi-pred-northern_choco_test_2025_06_16-composite-2022")

with open("shapefiles/Ecuador DEM 900m contour.geojson") as f:
    aoi = json.load(f)

df = stats.summary(aoi['features'][0])
df

print(df.to_markdown(index=False))

# %%
