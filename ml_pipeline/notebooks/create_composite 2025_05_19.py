#%%
import xarray as xr
import rioxarray
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path
from osgeo import gdal, gdalconst
from ml_pipeline.stac_builder import STACBuilder, STACBuilderConfig
from ml_pipeline.s3_utils import upload_file
import rasterio

#%% 
# ---- list the 12 monthly COGs for one quad ----

year = 2022
months = [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12]

run_name = "20250520T2122_rf_test_2022"

# quad_name = "570-1025" 
quad_name = "570-1026"

cogs = [
    f"s3://choco-forest-watch/predictions/{run_name}//{year}/{m:02d}/{quad_name}_{year}_{m:02d}.tiff"
    for m in months
]

def open_month(url):
    da = rioxarray.open_rasterio(url, masked=True)      # (band=N, y, x)
    month = url.split('_')[-1].split('.')[0]           # '01' … '12'
    return da.expand_dims(time=[month])                # (time, band, y, x)

# Get band count from first COG
with rasterio.open(cogs[0]) as src:
    band_count = src.count
    band_descriptions = src.descriptions if src.descriptions else [f"Band {i+1}" for i in range(band_count)]

stacked = xr.concat([open_month(u) for u in cogs], dim="time").load()

print(f"Number of bands: {band_count}")
print(f"Band descriptions: {band_descriptions}")
stacked

#%% 
# 
# # --- drop the extra band axis that rioxarray added (it's always length-1 here) ---
data = stacked.sel(band=1)         # (time, y, x) – integer class values


# --- 1. count clear observations per pixel ---
valid = (~data.isin([2, 3, 255])).sum("time")   # clouds, shadows & nodata are "invalid"

# --- 2. majority vote across clear months ---
masked = data.where(~data.isin([2, 3]))         # ignore clouds/shadows
class_counts = xr.concat(
    [(masked == v).sum("time").assign_coords(class_val=v)  # Forest, Non-Forest, Water
     for v in [0, 1, 4]],
    dim="class_val"
)                                               # (class_val, y, x)

majority = class_counts.argmax("class_val").astype(np.uint8)

# --- 3. derive a 0/1 forest flag (255 = missing) ---
forest_flag = majority.where(valid >= 2, 255)   # demand ≥ 2 clear looks
forest_flag = (forest_flag == 0).astype(np.uint8)   # Forest→1, else→0
forest_flag = forest_flag.where(valid >= 2, 255)

# --- 4. build a multiband DataArray ---
bands = [forest_flag.rename("forest_flag")] + [
    data.isel(time=i).astype(np.uint8).rename(f"month_{str(t)}")
    for i, t in enumerate(data["time"].values)
]

# Stacke

# remove the length-1 'band' dim that rioxarray added
stacked_stack = stacked.squeeze("band", drop=True)        # dims now: (time, y, x)

stacked_stack = (
    stacked_stack.rename(time="band")                     # 'time' → 'band'
      .assign_coords(band=("band", months))# label bands 1-6
      .transpose("band", "y", "x")             # (band, y, x) – GDAL-friendly
)

print(stacked_stack.dims)  # ('band', 'y', 'x')


tif_path = f"{quad_name}_{year}_forest_stacked.tif"

out = xr.concat([forest_flag, stacked_stack], dim="band").transpose("band", "y", "x")              # (band, y, x)
out.rio.to_raster(
    tif_path,
    dtype="uint8", tiled=True, compress="deflate"
)
print(f"✓ wrote {tif_path}")

# Just forest flag
tif_path = f"{quad_name}_{year}_forest_cover.tif"

out = xr.concat([forest_flag], dim="band").transpose("band", "y", "x")              # (band, y, x)
out.rio.to_raster(
    tif_path,
    dtype="uint8", tiled=True, compress="deflate"
)
print(f"✓ wrote {tif_path}")


#%% 

min_pixels = 10

print(f"Applying sieve filter with {min_pixels} pixels to {tif_path}")

gdal.UseExceptions()

# open in UPDATE mode
ds = gdal.Open(str(tif_path), gdalconst.GA_Update)
if ds is None:
    raise RuntimeError(f"GDAL failed to open {tif_path!s}")

band = ds.GetRasterBand(1)      
nodata = band.GetNoDataValue()

# run sieve: dest == src for in-place, mask = None, 8-connected
gdal.SieveFilter(srcBand=band,
                maskBand=None,
                dstBand=band,
                threshold=min_pixels,
                connectedness=8)

# restore nodata (GDAL sometimes drops it)
if nodata is not None:
    band.SetNoDataValue(nodata)

band.FlushCache()
ds = None  # close dataset

# %%

# Add STAC and S3 upload functionality


# Upload the composite to S3
remote_key = f"predictions/{run_name}-composites/{year}/{quad_name}_{year}_forest_cover.tif"
upload_file(Path(tif_path), remote_key)

# Create STAC builder instance
builder = STACBuilder(STACBuilderConfig(use_remote_db=True))



#%%
  
# Create STAC collection and items for the composite

# Will build a stac from whatever files are in the prefix on the remote server

builder.process_year(
    year=year,
    prefix_on_s3=f"predictions/{run_name}-composites",
    collection_id=f"nicfi-pred-{run_name}-composite-{year}",
    asset_key="data",
    asset_roles=["classification"],
    asset_title=f"Annual Forest Cover Composite for {run_name}",
    extra_asset_fields={
        "raster:bands": [
            {
                "name": "forest_flag",
                "nodata": 255,
                "data_type": "uint8",
                "description": "Forest flag (1=Forest, 0=Non-Forest, 255=No Data)"
            },
            *[
                {
                    "name": f"month_{m:02d}",
                    "nodata": 255,
                    "data_type": "uint8",
                    "description": f"Monthly classification for {m:02d}/2022"
                }
                for m in months
            ],
            *[
                {
                    "name": f"band_{i+1}",
                    "nodata": 255,
                    "data_type": "uint8",
                    "description": desc
                }
                for i, desc in enumerate(band_descriptions)
            ]
        ]
    }
)

print("✓ Uploaded composite and created STAC collection")

# %%
