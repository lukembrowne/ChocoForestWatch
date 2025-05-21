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
        └── metrics_*.json
"""

#%% 
from pathlib import Path
import argparse, subprocess, json, shutil
from ml_pipeline.run_manager import RunManager     
from tqdm import tqdm

#%% 

# Set tag
tag = "rf_test" # Folder prefix will be the time

# Set year
year = "2022"

#%% 
# One folder for the whole year-long experiment
rm = RunManager()
parent = rm.new_run(tag=f"{tag}_{year}")    


#%%
# Loop through months
for m in tqdm(range(1, 13), desc=f"Processing months for {year}"):
    
    print("-"*100)
    print("-"*100)
    print("-"*100)
    month = f"{m:02d}"
    child = parent / f"{year}_{month}"
    child.mkdir()                                       # keeps artefacts separate

    subprocess.run(
        [
            "poetry","run","python",
            "train_and_predict_by_month.py",
            "--year",  year,
            "--month", month,
            "--run_dir", str(child),                    # NEW flag
        ],
    check=True,
    )

    # append month metrics to parent-level aggregator (optional)
    metrics_file = child / "metrics.json"
    if metrics_file.exists():
        with open(metrics_file) as f:
            metrics = json.load(f)
        rm.save_json(f"metrics_{month}.json", metrics)
    else:
        print(f"No metrics file found for {year}-{month}")

    print(f"✅ Year {year} finished. Results in {parent}")
# %%

# Add to summary csv

# Loop through all metrics files in parent
metrics_files = list(parent.glob("metrics_*.json"))

# Loop through all metrics files and add to summary csv
for file in metrics_files:
    with open(file) as f:
        metrics = json.load(f)
    rm.record_summary(metrics)

