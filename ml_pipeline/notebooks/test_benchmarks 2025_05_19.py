#%% 
from ml_pipeline.polygon_loader import load_training_polygons
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
from ml_pipeline.extractor import TitilerExtractor
import numpy as np
from ml_pipeline.benchmark_metrics_io import (
    save_metrics_csv,
    load_all_metrics,
    show_accuracy_table,
    plot_accuracy,
)

from ml_pipeline.s3_utils import upload_file
from pathlib import Path
from ml_pipeline.db_utils import get_db_connection
from ml_pipeline.stac_builder import STACManager




#%% 
engine = get_db_connection()

#%% 
# Loop over all months in 2022 and combine results
year = "2022"
all_gdfs = []

for month in range(1, 13):
    month_str = f"{month:02d}"  # Format month as 2-digit string
    print(f"\nProcessing {year}-{month_str}...")
    
    try:
        gdf = load_training_polygons(
            engine,
            project_id=1,
            basemap_date=f"{year}-{month_str}",
        )
        
        if len(gdf) > 0:
            all_gdfs.append(gdf)
            print(f"Found {len(gdf)} polygons for {year}-{month_str}")
        else:
            print(f"No polygons found for {year}-{month_str}")
            
    except Exception as e:
        print(f"Error processing {year}-{month_str}: {str(e)}")

# Combine all GeoDataFrames
if all_gdfs:
    combined_gdf = pd.concat(all_gdfs, ignore_index=True)
    print(f"\nTotal number of polygons across all months: {len(combined_gdf)}")
    print("\nPolygons per month:")
    print(combined_gdf['basemap_date'].value_counts().sort_index())
    
    # Display first few rows of combined dataset
    combined_gdf.head()
else:
    print("No polygons found for any month in 2022")
# %%

#%% Benchmark forest‑cover predictions

# collection
collection = "nicfi-pred-composite-2022"
# collection = "benchmarks-hansen-tree-cover-2022"
# collection = "benchmarks-mapbiomes-2022"
#collection = "benchmarks-esa-landcover-2020"
#collection = "benchmarks-jrc-forestcover-2020"
#collection = "benchmarks-palsar-2020"
#collection = "benchmarks-wri-treecover-2020"
# collection = "nicfi-pred-20250520T2122_rf_test_2022-composite-2022"

pred_extractor  = TitilerExtractor(base_url="http://localhost:8083", 
                                   collection=collection,
                                   band_indexes=[1])

# Test that we can find the correct collection
cog_urls = pred_extractor.get_all_cog_urls(collection)
print(f"Found {len(cog_urls)} COGs for {collection}")
if len(cog_urls) == 0:
    raise ValueError(f"No COGs found for {collection}")


metrics_rows, y_true_all, y_pred_all = [], [], []
months_sorted = sorted(combined_gdf["basemap_date"].unique())

# month = "2022-01"

for month in months_sorted:

    print("-"*100)
    print(f"Processing {month}")
    
    gdf_month = combined_gdf[
        (combined_gdf["basemap_date"] == month)
        & (combined_gdf["classLabel"].isin(["Forest", "Non-Forest"]))
    ]
    if gdf_month.empty:
        print(f"Skipping {month} (no Forest/Non‑Forest polygons)")
        continue

    # Extract pixels and get predictions
    pixels, y_true, fids = pred_extractor.extract_pixels(gdf_month)


    # Check if any pixels are outside the raster
    if pixels.size == 0:
        print(f"Skipping {month} (no pixels inside polygons)")
        continue

    # Convert pixels to either Non-forest == 0 or Forest == 1
    if "nicfi" in collection:
        y_pred = np.where(pixels == 0, "Non-Forest", "Forest")

    elif(collection == "benchmarks-hansen-tree-cover-2022"):
        y_pred = np.where(pixels >= 90, "Forest", "Non-Forest") # Set threshold to 90% tree cover

    elif(collection == "benchmarks-mapbiomes-2022"):
        # # Legend for values - https://ecuador.mapbiomas.org/wp-content/uploads/sites/7/2023/12/Ecuador_Legend-Code-Col-1.pdf
        y_pred = np.where(
            np.logical_or.reduce([
                pixels == 3,
                pixels == 4,
                pixels == 5,
                pixels == 6
            ]),
            "Forest",
            "Non-Forest"
        )

    elif(collection == "benchmarks-esa-landcover-2020"):
        y_pred = np.where(pixels == 10, "Forest", "Non-Forest")

    elif(collection == "benchmarks-jrc-forestcover-2020"):
        y_pred = np.where(pixels == 1, "Forest", "Non-Forest")

    elif(collection == "benchmarks-palsar-2020"):
        y_pred = np.where(
            np.logical_or.reduce([
                pixels == 1,
                pixels == 2,
            ]), "Forest", "Non-Forest")
        
    elif(collection == "benchmarks-wri-treecover-2020"):
        y_pred = np.where(pixels >= 90, "Forest", "Non-Forest")

    else:
        raise ValueError(f"Unknown collection: {collection}")

    # Create a DataFrame with predictions and feature IDs
    pred_df = pd.DataFrame({
        'id': fids,
        'predicted_label': y_pred.squeeze()
    })

    # Debug: Check which polygons have predictions
    polygons_with_preds = set(pred_df['id'].unique())
    all_polygons = set(gdf_month['id'].unique())
    missing_polygons = all_polygons - polygons_with_preds
    
    print(f"\nDebug info for {month}:")
    print(f"Total polygons: {len(all_polygons)}")
    print(f"Polygons with predictions: {len(polygons_with_preds)}")
    print(f"Polygons missing predictions: {len(missing_polygons)}")
    
    if len(missing_polygons) > 0:
        print("\nSample of missing polygons:")
        missing_gdf = gdf_month[gdf_month['id'].isin(missing_polygons)]
        print(missing_gdf[['id', 'classLabel']].head())
        
        # Check if these polygons have COG coverage
        print("\nChecking COG coverage for missing polygons...")
        for idx, row in missing_gdf.head().iterrows():
            cog_urls = pred_extractor.get_cog_urls(row.geometry)
            print(f"Polygon {row['id']}: {len(cog_urls)} COGs found")

    pred_df.predicted_label.value_counts()

    # Merge predictions back into the GeoDataFrame
    gdf_month = gdf_month.merge(
        pred_df,
        left_on='id',
        right_on='id',
        how='left'
    )

    # Count nulls in gdf_month
    null_count = gdf_month['predicted_label'].isnull().sum()
    print(f"Number of null predictions in gdf_month: {null_count}")
    print(f"Percentage of null predictions in gdf_month: {(null_count/len(gdf_month))*100:.2f}%")

    # Drop rows with null predictions
    # Double check why this is happening
    gdf_month = gdf_month[gdf_month['predicted_label'].notna()]

    y_true = gdf_month['classLabel']
    y_pred = gdf_month['predicted_label']
    
    # Calculate accuracy
    acc = accuracy_score(y_true, y_pred)
    print(f"Accuracy: {acc:.3f}")
    
    # Optionally, you can also analyze results by feature ID if needed
    # unique_fids = np.unique(fids)
    # for fid in unique_fids:
    #     mask = fids == fid
    #     fid_acc = accuracy_score(y_true[mask], y_pred[mask])
    #     print(f"Feature {fid} accuracy: {fid_acc:.3f}")

    report = classification_report(
        y_true,
        y_pred,
        labels=["Forest", "Non-Forest"],
        output_dict=True,
        zero_division=0,
    )

    print(report)

    metrics_rows.append(
        {
            "month": month,
            "n_pixels": len(y_true),
            "accuracy": acc,
            "f1_forest": report["Forest"]["f1-score"],
            "f1_nonforest": report["Non-Forest"]["f1-score"],
            "precision_forest": report["Forest"]["precision"],
            "precision_nonforest": report["Non-Forest"]["precision"],
            "recall_forest": report["Forest"]["recall"],
            "recall_nonforest": report["Non-Forest"]["recall"],
        }
    )

    y_true_all.extend(y_true)
    y_pred_all.extend(y_pred)



# Overall 2022 metrics
overall_acc = accuracy_score(y_true_all, y_pred_all)
overall_report = classification_report(
    y_true_all,
    y_pred_all,
    labels=["Forest", "Non-Forest"],
    output_dict=True,
    zero_division=0,
)
metrics_rows.append(
    {
        "month": "overall",
        "n_pixels": len(y_true_all),
        "accuracy": overall_acc,
        "f1_forest": overall_report["Forest"]["f1-score"],
        "f1_nonforest": overall_report["Non-Forest"]["f1-score"],
        "precision_forest": overall_report["Forest"]["precision"],
        "precision_nonforest": overall_report["Non-Forest"]["precision"],
        "recall_forest": overall_report["Forest"]["recall"],
        "recall_nonforest": overall_report["Non-Forest"]["recall"],
    }
)

metrics_df = pd.DataFrame(metrics_rows)

print(metrics_df)



# %%
save_metrics_csv(metrics_df, benchmark_name=collection)

show_accuracy_table(metrics_df)


plot_accuracy(metrics_df)

# %%
