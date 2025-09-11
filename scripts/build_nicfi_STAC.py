#!/usr/bin/env python3
"""
NICFI STAC Builder

Builds SpatioTemporal Asset Catalog (STAC) metadata for NICFI satellite imagery
and loads it into PGSTAC database for use with TiTiler.

Usage:
    # Navigate to ml_pipeline folder and run with poetry:
    cd ml_pipeline
    poetry run python ../scripts/build_nicfi_STAC.py

Prerequisites:
    - NICFI imagery must be uploaded to object storage (use migrate_nicfi_data.sh first)
    - Database connection configured in environment
    - ml_pipeline package available

Configuration:
    - Modify the years list to process specific years
    - Adjust collection_id format if needed
    - Update S3 prefix path to match your object storage structure
"""

#%%
from ml_pipeline.stac_builder import STACManager, STACManagerConfig

builder = STACManager(STACManagerConfig(use_remote_db=True))

# Test to make sure URLs are correct
# builder.list_cogs(prefix="NICFI Monthly Mosaics/2022/01")
# builder.list_cogs(prefix="NICFI Monthly Mosaics/2022/02")
# builder.list_cogs(prefix="NICFI Monthly Mosaics/2022/03")
# builder.list_cogs(prefix="NICFI Monthly Mosaics/2022/04")


# Loop through each year and month and process the imagery
for year in (["2024"]):      
    for month in range(1, 13):
       # month = 12
        print(f"Processing {year}-{month:02d}")
        builder.process_month(
            year=year,
            month=month,
            prefix_on_s3="NICFI Monthly Mosaics",
            collection_id=f"nicfi-{year}-{month:02d}",
            asset_key="data",
            asset_roles=["data"],
            asset_title="NICFI Monthly Mosaic COG",
        )


# %%
