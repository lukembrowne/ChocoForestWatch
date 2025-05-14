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
import requests
import leafmap
from rasterio.transform import from_origin
import tempfile
import leafmap
from localtileserver import get_leaflet_tile_layer, TileClient

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

# Step 3: Initialize storage for pixels and labels
all_pixels = []
all_labels = []

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
# Testing out using titiler-pgstac to get the assets for a polygon

# Convert to WGS84 for the titiler-pgstac API request
gdf_wgs84 = gdf.to_crs("EPSG:4326")

# Get the first polygon
polygon_wgs84 = gdf_wgs84.iloc[0].geometry

# Get the assets for the polygon
minx, miny, maxx, maxy = polygon_wgs84.bounds
print("Bounds: ", minx, miny, maxx, maxy)

titiler_url = "http://localhost:8083"

# Make the request to titiler-pgstac API

# Format the bbox string
bbox_str = f"{minx},{miny},{maxx},{maxy}"

# Make the request to get assets
response = requests.get(
    f"{titiler_url}/collections/nicfi-2022/bbox/{bbox_str}/assets",
    headers={"accept": "application/json"}
)

# Check if request was successful
if response.status_code == 200:
    assets = response.json()
    print(f"Found {len(assets)} assets:")
    for asset in assets:
        print(f"  {asset}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)

cog_url = assets[0]['assets']['data']['href']

# Get the original polygon in Web Mercator
polygon_web_mercator = gdf.iloc[0].geometry

# Now you can use these assets for further processing
with rasterio.open(cog_url) as src:
    # Print bounds of the raster
    print(src.bounds)

    # Convert the raster to Web Mercator if needed
    if src.crs != "EPSG:3857":
        print("Converting raster to Web Mercator...")
        # You might need to add transformation logic here if the raster needs to be reprojected

    out_image, out_transform = mask(
        src, [mapping(polygon_web_mercator)], crop=True, indexes=(1,2,3,4)
    )
    print(out_image.shape)
    print(out_transform)

#%% 
# Display the masked raster using localtileserver

# Create a temporary file
temp_dir = tempfile.mkdtemp()
temp_file = os.path.join(temp_dir, 'masked_raster.tif')

# Save the masked raster as a GeoTIFF
with rasterio.open(
    temp_file,
    'w',
    driver='GTiff',
    height=out_image.shape[1],
    width=out_image.shape[2],
    count=out_image.shape[0],
    dtype=out_image.dtype,
    crs=src.crs,
    transform=out_transform,
) as dst:
    dst.write(out_image)

# Create a tile server from the temporary file
client = TileClient(temp_file)

# Create ipyleaflet tile layer from the server
t = get_leaflet_tile_layer(client)

# Create a map centered on the raster
m = leafmap.Map(center=client.center(), zoom=client.default_zoom)
m.add(t)

# Add the polygon to the map
m.add_gdf(gdf.iloc[[0]], layer_name='Polygon')

# Display the map
m

# Clean up the temporary file
os.remove(temp_file)
os.rmdir(temp_dir)

#%% 
