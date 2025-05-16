#%%
import boto3
import os
from datetime import datetime
import calendar
import json
from pathlib import Path
import rasterio
from rasterio.warp import transform_bounds
import numpy as np
from pystac import Item, Asset, MediaType, Collection, Extent, SpatialExtent, TemporalExtent, Link
from pypgstac.load import Loader
import tempfile
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv("../../.env")

# Set database connection environment variables needed by pypgstac
os.environ['PGHOST'] = 'localhost'
os.environ['PGPORT'] = os.getenv('DB_PORT')
os.environ['PGDATABASE'] = os.getenv('POSTGRES_DB')
os.environ['PGUSER'] = os.getenv('POSTGRES_USER')
os.environ['PGPASSWORD'] = os.getenv('POSTGRES_PASSWORD')

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

list_cogs_for_month("2022", "01")

#%%
def create_stac_collection(year, month):
    """Create a STAC collection for a specific year‑month."""
    first_day = datetime(int(year), int(month), 1)
    last_day = datetime(int(year), int(month), calendar.monthrange(int(year), int(month))[1])
    collection = Collection(
        id=f"nicfi-{year}-{month}",
        description=f"NICFI Monthly Mosaic for {year}-{month}",
        license="proprietary",
        extent=Extent(
            spatial=SpatialExtent(bboxes=[[-180, -90, 180, 90]]),
            temporal=TemporalExtent(intervals=[[first_day, last_day]])
        ),
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
    """Process each month in a year and create a separate STAC collection per month."""
    monthly_collections = []
    for month in range(1, 13):
        month_str = f"{month:02d}"
        print(f"Processing {year}-{month_str}")

        collection = create_stac_collection(year, month_str)
        items = []

        cogs = list_cogs_for_month(year, month_str)

        print(f"Found {len(cogs)} COG files for {year}-{month_str}")

        for cog in cogs:
            try:
                stac_item = create_stac_item(cog, year, month_str)
                items.append(stac_item)
                collection.add_item(stac_item)
            except Exception as e:
                print(f"Error processing {cog['url']}: {str(e)}")

        monthly_collections.append((collection, items))
    return monthly_collections

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
        
        # Database connection environment variables are now loaded from .env
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
# Example: process a year and save / load each monthly collection
monthly_collections = process_year("2022")

#%%

# This will load them into the PgSTAC database. 
# Will overwrite any existing collections with the same id.
# Upsert will add anything new and replace anything with the same id

for collection, items in monthly_collections:
    print(f"\nSTAC Collection {collection.id} contains {len(items)} items")
    collection_path = Path("stac_catalog") / collection.id
    collection.normalize_and_save(str(collection_path))
    load_to_pgstac(collection, items)



# %%


# Testing out stac_builder.py
from ml_pipeline.stac_builder import STACBuilder

builder = STACBuilder()

builder.list_cogs(prefix="NICFI Monthly Mosaics/2022/01")
builder.list_cogs(prefix="NICFI Monthly Mosaics/2022/02")
builder.list_cogs(prefix="NICFI Monthly Mosaics/2022/03")

for year in (["2022"]):      
    for month in range(1, 4):
        print(f"Processing {year}-{month:02d}")
        builder.process_month(
            year=year,
            month=month,
            prefix="NICFI Monthly Mosaics",
            collection_id=f"nicfi-{year}-{month:02d}",
            asset_key="data",
            asset_roles=["data"],
            asset_title="NICFI Monthly Mosaic COG",
        )

