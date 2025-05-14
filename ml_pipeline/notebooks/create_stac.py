#%%
import boto3
import os
from datetime import datetime
import json
from pathlib import Path
import rasterio
from rasterio.warp import transform_bounds
import numpy as np
from pystac import Item, Asset, MediaType, Collection, Extent, SpatialExtent, TemporalExtent, Link
from pypgstac.load import Loader
import tempfile
import subprocess

#%%
# Configure S3 client for DigitalOcean Spaces
session = boto3.session.Session()
s3_client = session.client('s3',
    region_name='nyc3',  # Change this to your region
    endpoint_url='https://nyc3.digitaloceanspaces.com',
    aws_access_key_id=os.getenv('DO_SPACES_KEY'),
    aws_secret_access_key=os.getenv('DO_SPACES_SECRET')
)

BUCKET_NAME = "choco-forest-watch"

#%%
def list_cogs_for_month(year, month):
    """List all COG files for a specific month and year."""
    prefix = f"NICFI Monthly Mosaics/{year}/{month}"
    
    response = s3_client.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=prefix
    )
    
    cog_files = []
    if 'Contents' in response:
        for obj in response['Contents']:
            if obj['Key'].endswith('.tiff'):
                cog_files.append({
                    'key': obj['Key'],
                    'url': f"s3://{BUCKET_NAME}/{obj['Key']}"
                })
    
    return cog_files

#%%
def create_stac_collection(year):
    """Create a STAC collection for a year of data."""
    collection = Collection(
        id=f"nicfi-{year}",
        description=f"NICFI Monthly Mosaics for {year}",
        license="proprietary",
        extent=Extent(
            spatial=SpatialExtent(bboxes=[[-180, -90, 180, 90]]),
            temporal=TemporalExtent(
                intervals=[[datetime(int(year), 1, 1), datetime(int(year), 12, 31)]]
            )
        )
    )
    
    # Add required collection fields
    collection.add_links([
        Link(
            rel="license",
            target="https://www.planet.com/nicfi/",
            media_type="text/html",
            title="NICFI License"
        )
    ])
    
    return collection

#%%
def create_stac_item(cog_info, year, month):
    """Create a STAC item for a single COG."""
    with rasterio.open(cog_info['url']) as dataset:
        # Get bounds and transform to WGS84
        bounds = transform_bounds(dataset.crs, 'EPSG:4326', *dataset.bounds)
        
        # Create geometry from bounds
        geometry = {
            'type': 'Polygon',
            'coordinates': [[
                [bounds[0], bounds[1]],
                [bounds[2], bounds[1]],
                [bounds[2], bounds[3]],
                [bounds[0], bounds[3]],
                [bounds[0], bounds[1]]
            ]]
        }
        
        # Create bbox
        bbox = [bounds[0], bounds[1], bounds[2], bounds[3]]
        
        # Create datetime
        dt = datetime(int(year), int(month), 1)
        
        # Create item
        item = Item(
            id=cog_info['key'].split('/')[-1].replace('.tiff', ''),
            geometry=geometry,
            bbox=bbox,
            datetime=dt,
            properties={}
        )
        
        # Add asset
        item.add_asset(
            "data",
            Asset(
                href=cog_info['url'],
                media_type=MediaType.COG,
                roles=['data'],
                title='NICFI Monthly Mosaic COG'
            )
        )
        
        return item

#%%
def process_year(year):
    """Process all months for a given year and create a STAC collection."""
    collection = create_stac_collection(year)
    all_items = []
    
    for month in range(1, 13):
        month_str = f"{month:02d}"
        print(f"Processing {year}-{month_str}")
        
        cogs = list_cogs_for_month(year, month_str)
        for cog in cogs:
            try:
                stac_item = create_stac_item(cog, year, month_str)
                all_items.append(stac_item)
                collection.add_item(stac_item)
            except Exception as e:
                print(f"Error processing {cog['url']}: {str(e)}")
    
    return collection, all_items

#%%
def load_to_pgstac(collection, items):
    """Load STAC collection and items into PgSTAC database using command-line interface."""
    # Create a temporary directory to store the STAC files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save collection to a temporary file
        collection_path = os.path.join(tmpdir, "collection.json")
        collection.save_object(dest_href=collection_path)
        
        # Save items to a temporary file
        items_path = os.path.join(tmpdir, "items.ndjson")
        with open(items_path, 'w') as f:
            for item in items:
                f.write(json.dumps(item.to_dict()) + '\n')
        
        # Set database connection environment variables
        os.environ['PGHOST'] = 'localhost'
        os.environ['PGPORT'] = '5432'
        os.environ['PGDATABASE'] = 'cfwdb'
        os.environ['PGUSER'] = 'cfwuser'
        os.environ['PGPASSWORD'] = '1234'
        
        try:
            # Load collection
            print("Loading collection...")
            subprocess.run([
                'pypgstac', 'load', 'collections',
                '--method', 'upsert',
                collection_path
            ], check=True)
            
            # Load items
            print("Loading items...")
            subprocess.run([
                'pypgstac', 'load', 'items',
                '--method', 'upsert',
                items_path
            ], check=True)
            
            print("Data loaded successfully into PgSTAC!")
            
        except subprocess.CalledProcessError as e:
            print(f"Error loading data into PgSTAC: {str(e)}")
            print("Make sure pypgstac is installed and the database is properly configured.")
            raise

#%%
# Example of processing a full year and saving the collection
collection, items = process_year("2022")

#%%
# Print out items in the PySTAC collection
print("\nSTAC Collection Details:")
print(f"Collection ID: {collection.id}")
print(f"Number of items: {len(list(collection.get_all_items()))}")

# Print details for each item
for i, item in enumerate(collection.get_all_items()):
    print(f"\nItem {i+1}:")
    print(f"  ID: {item.id}")
    print(f"  Datetime: {item.datetime}")
    print(f"  Bbox: {item.bbox}")
    print(f"  Assets: {list(item.assets.keys())}")
    
    # Optional: Print the full URL for the data asset
    if "data" in item.assets:
        print(f"  Data URL: {item.assets['data'].href}")

#%%
# Save locally
collection.normalize_and_save("stac_catalog")

#%%
# Load into PgSTAC
load_to_pgstac(collection, items)
