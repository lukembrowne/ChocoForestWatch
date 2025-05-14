#%% 
import pandas as pd
import os
from dotenv import load_dotenv
import geopandas as gpd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import json
from shapely.geometry import shape
import numpy as np
from rio_tiler.io import COGReader
from rio_tiler.mosaic import mosaic_reader
from rio_tiler.mosaic.methods import FirstMethod
from shapely.geometry import mapping
import rasterio
from rasterio.mask import mask

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
# Read training polygons from PostGIS
TRAINING_POLYGON_TABLE = "core_trainingpolygonset"
TRAINING_POLYGON_GEOM_COL = "polygons"

# Read the training polygons into a DataFrame first
query = f"""
SELECT id, project_id, basemap_date, feature_count, {TRAINING_POLYGON_GEOM_COL}
FROM {TRAINING_POLYGON_TABLE}
WHERE excluded = false AND basemap_date = '2022-01' AND project_id = 1
"""

df = pd.read_sql(query, engine)

# Convert GeoJSON to geometries
def convert_geojson_to_geometry(geojson_str):
    if isinstance(geojson_str, dict) and geojson_str.get('type') == 'FeatureCollection':
        # Extract all polygons from the feature collection
        geometries = []
        for feature in geojson_str.get('features', []):
            if feature.get('geometry'):
                geometries.append(shape(feature['geometry']))
        
        # If we have multiple geometries, return a MultiPolygon
        if len(geometries) > 1:
            from shapely.geometry import MultiPolygon
            return MultiPolygon(geometries)
        elif len(geometries) == 1:
            return geometries[0]
    return None

# Create GeoDataFrame with class labels
gdf = gpd.GeoDataFrame(columns=['id', 'project_id', 'basemap_date', 'feature_count', 'class_label'])

# Process each row in the dataframe
for _, row in df.iterrows():
    if isinstance(row[TRAINING_POLYGON_GEOM_COL], dict) and row[TRAINING_POLYGON_GEOM_COL].get('type') == 'FeatureCollection':
        for feature in row[TRAINING_POLYGON_GEOM_COL].get('features', []):
            if feature.get('geometry'):
                new_row = row.copy()
                new_row['geometry'] = shape(feature['geometry'])
                new_row['class_label'] = feature.get('properties', {}).get('classLabel', '')
                gdf = pd.concat([gdf, gpd.GeoDataFrame([new_row])], ignore_index=True)

# Set the geometry column and CRS
gdf = gdf.set_geometry('geometry')
gdf.crs = "EPSG:3857"  # Web Mercator coordinate system

#%% 
# Display basic information about the training polygons
print(f"Number of training sets: {len(gdf)}")
print("\nTraining sets by project:")
print(gdf['project_id'].value_counts())
print("\nTraining sets by date:")
print(gdf['basemap_date'].value_counts().sort_index())

# Print some debugging information about the geometries
print("\nGeometry types in the dataset:")
print(gdf.geometry.type.value_counts())

# Check for any invalid geometries
invalid_geoms = gdf[~gdf.geometry.is_valid]
if len(invalid_geoms) > 0:
    print("\nWarning: Found invalid geometries:")
    print(invalid_geoms[['id', 'project_id', 'basemap_date']])

#%% 
# Plot the training polygons for a specific project
project_id = 1
project_gdf = gdf[gdf['project_id'] == project_id]

# Create figure and axis
fig, ax = plt.subplots(figsize=(12, 8))

# Plot with explicit aspect ratio and color by class_label
project_gdf.plot(ax=ax, column='class_label', aspect='equal', legend=True, cmap='viridis')

# Add title and adjust layout
plt.title(f'Training Polygons for Project {project_id} (colored by class_label)')
plt.tight_layout()

# Print the bounds of the plot
bounds = project_gdf.total_bounds
print("\nPlot bounds:")
print(f"X: {bounds[0]:.4f} to {bounds[2]:.4f}")
print(f"Y: {bounds[1]:.4f} to {bounds[3]:.4f}")

plt.show()

#%% 
# Step 1: Import required packages
import numpy as np
import rasterio
from shapely.geometry import mapping
from rasterio.mask import mask

#%% 
# Step 2: Set up the COG URL and band indexes
# Get the first COG URL from the list
cog_url = "s3://choco-forest-watch/NICFI Monthly Mosaics/2022/01/570-1026_2022_01.tiff"

indexes = (1, 2, 3, 4)  # Adjust these band indexes as needed

print(f"Testing with COG: {cog_url}")

#%% 
# Step 3: Initialize storage for pixels and labels
all_pixels = []
all_labels = []

#%% 
# Step 4: Process first polygon as a test
test_row = gdf.iloc[0]
print(f"\nProcessing polygon with class label: {test_row['class_label']}")

# Get the geometry and label
geom = test_row.geometry
label = test_row['class_label']

# Convert Shapely geometry to GeoJSON
geom_geojson = mapping(geom)
print(f"Geometry type: {geom.geom_type}")

# Extract pixels for this polygon
with rasterio.open(cog_url) as src:
    print(f"COG info - Bands: {src.count}, Resolution: {src.res}")
    
    # Get the data for the polygon
    out_image, out_transform = mask(src, [geom_geojson], crop=True, indexes=indexes)
    
    # Reshape the data: (bands, height, width) -> (height*width, bands)
    pix = out_image.reshape(len(indexes), -1).T
    print(f"Extracted data shape: {out_image.shape}")
    print(f"Reshaped data shape: {pix.shape}")
    
    # Remove nodata pixels
    valid = ~np.any(pix == src.nodata, axis=1)
    print(f"Number of valid pixels: {valid.sum()}")
    
    if valid.any():
        all_pixels.append(pix[valid])
        all_labels.extend([label] * valid.sum())
        print(f"Added {valid.sum()} pixels to the dataset")

#%% 
# Step 5: Process all remaining polygons
for idx, row in gdf.iloc[1:].iterrows():
    print(f"\nProcessing polygon {idx} with class label: {row['class_label']}")
    
    geom = row.geometry
    label = row['class_label']
    
    # Convert Shapely geometry to GeoJSON
    geom_geojson = mapping(geom)
    
    with rasterio.open(cog_url) as src:
        out_image, out_transform = mask(src, [geom_geojson], crop=True, indexes=indexes)
        
        pix = out_image.reshape(len(indexes), -1).T
        valid = ~np.any(pix == src.nodata, axis=1)
        
        if valid.any():
            all_pixels.append(pix[valid])
            all_labels.extend([label] * valid.sum())
            print(f"Added {valid.sum()} pixels to the dataset")

#%% 
# Step 6: Combine all pixels and labels
if not all_pixels:
    raise ValueError("No pixels found in the provided polygons")

X = np.vstack(all_pixels).astype("float32")
y = np.array(all_labels)

print("\nFinal dataset statistics:")
print(f"Total number of pixels: {len(X)}")
print(f"Number of unique classes: {len(np.unique(y))}")
print(f"Shape of X: {X.shape}")
print(f"Shape of y: {y.shape}")

#%% 
from cogeo_mosaic.backends import MosaicBackend
from shapely.geometry import mapping

# Point this at your existing MosaicJSON (the same one Titiler is serving):
mosaic_url = "file:///titiler/mosaicJsons/mosaicjson/2022-01.json"

mosaic_url = "file:///Users/luke/apps/ChocoForestWatch/titiler/mosaicJsons/2022-01-mosaic.json"


gdf = gdf.to_crs("EPSG:4326")

# Open the mosaic
with MosaicBackend(mosaic_url) as mosaic:
    # For each training polygon:
    for idx, row in gdf.iterrows():
        geom = row.geometry
        lng, lat = geom.centroid.x, geom.centroid.y
        # You can either:
        #  • ask for all COGs overlapping the polygon's bounding box:
        minx, miny, maxx, maxy = geom.bounds
        print("Bounds: ", minx, miny, maxx, maxy)
        assets = mosaic.assets_for_bbox(minx, miny, maxx, maxy)

        mosaic.assets_for_point(lng, lat)              # method - Find assets for a specific point


        #  • or ask for all COGs overlapping a point (for very small features):
        # lon, lat = geom.centroid.x, geom.centroid.y
        # assets = mosaic.assets_for_point(lon, lat)

        print(f"Polygon {idx} overlaps {len(assets)} assets:")
        for url in assets:
            print("  ", url)

        # Then do your masking exactly as before:
        for cog_url in assets:
            with rasterio.open(cog_url) as src:
                out_image, out_transform = mask(
                    src, [mapping(geom)], crop=True, indexes=(1,2,3,4)
                )
                # … process the pixels …

# Pre-extract the footprints & hrefs
mosaic = MosaicBackend(mosaic_url)

tiles = mosaic.mosaic_def["features"]
footprints = [
    (shape(feat["geometry"]), feat["properties"]["location"])
    for feat in tiles
]

for idx, row in gdf.iterrows():
    poly = row.geometry  # in EPSG:4326

    # Only keep those whose actual polygon footprint intersects
    hits = [href for fp, href in footprints if fp.intersects(poly)]

    print(f"Polygon {idx} → {len(hits)} true overlaps:")
    for url in hits:
        print("   ", url)
    # …then mask against each url as before…