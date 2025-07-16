"""
Usage examples for the GEE Dataset Downloader

This script demonstrates how to use the GEEDatasetDownloader class
to download various benchmark datasets for ChocoForestWatch.
"""

from gee_dataset_downloader import GEEDatasetDownloader
import time

# Initialize the downloader
downloader = GEEDatasetDownloader()

# Example 1: Hansen Tree Cover 2000
print("=" * 60)
print("Example 1: Hansen Tree Cover 2000")
print("=" * 60)

hansen_task = downloader.download_dataset(
    collection_id="UMD/hansen/global_forest_change_2022_v1_10",
    band="treecover2000",
    description="TreeCover2000-Hansen_wec",
    scale=30
)

# Example 2: Hansen Loss Data
print("\n" + "=" * 60)
print("Example 2: Hansen Loss Data")
print("=" * 60)

loss_task = downloader.download_dataset(
    collection_id="UMD/hansen/global_forest_change_2022_v1_10",
    band="lossyear",
    description="Loss2000-Hansen_wec",
    scale=30
)

# Example 3: Primary Forest (ImageCollection)
print("\n" + "=" * 60)
print("Example 3: Primary Forest 2001")
print("=" * 60)

primary_task = downloader.download_dataset(
    collection_id="UMD/GLAD/PRIMARY_HUMID_TROPICAL_FORESTS/v1",
    band="Primary_HT_forests",
    description="PrimaryForest2001-Hansen_wec",
    scale=30,
    reduce_method="first"
)

# Example 4: ESA World Cover
print("\n" + "=" * 60)
print("Example 4: ESA World Cover 2020")
print("=" * 60)

esa_task = downloader.download_dataset(
    collection_id="ESA/WorldCover/v100",
    description="LandCover2020-ESA_wec",
    scale=10,
    reduce_method="first"
)

# Example 5: JRC Forest Cover (ImageCollection that needs median)
print("\n" + "=" * 60)
print("Example 5: JRC Forest Cover 2020")
print("=" * 60)

jrc_task = downloader.download_dataset(
    collection_id="JRC/GFC2020/V1",
    description="ForestCover2020-JRC_wec",
    scale=10,
    reduce_method="median"
)

# Example 6: PALSAR (ImageCollection with specific index)
print("\n" + "=" * 60)
print("Example 6: PALSAR 2020")
print("=" * 60)

palsar_task = downloader.download_dataset(
    collection_id="JAXA/ALOS/PALSAR/YEARLY/FNF4",
    description="PALSAR2020_wec",
    scale=25,
    image_index=3  # Index 3 corresponds to 2020
)

# Example 7: WRI Tree Cover (ImageCollection with specific index)
print("\n" + "=" * 60)
print("Example 7: WRI Tree Cover 2020")
print("=" * 60)

wri_task = downloader.download_dataset(
    collection_id="projects/wri-datalab/TropicalTreeCover",
    description="TreeCover2020-WRI_wec",
    scale=10,
    image_index=38  # Based on your original code
)

# Example 8: GEDI Canopy Height (ImageCollection with specific index)
print("\n" + "=" * 60)
print("Example 8: GEDI Canopy Height 2019")
print("=" * 60)

gedi_task = downloader.download_dataset(
    collection_id="projects/sat-io/open-datasets/GLAD/GEDI_V27",
    description="CanopyHeight2019-GEDI_wec",
    scale=30,
    image_index=5  # Based on your original code
)

print("\n" + "=" * 60)
print("All export tasks have been started!")
print("Monitor progress at: https://code.earthengine.google.com/tasks")
print("=" * 60)

print("\nAfter downloads complete, here's how to process the files:")
print("\n# Example: Merge multi-tile exports")
print("file_paths = downloader.get_file_paths('../Benchmarks', 'ForestCover2020-JRC_wec')")
print("if len(file_paths) > 1:")
print("    downloader.merge_rasters(file_paths, '../Benchmarks/ForestCover2020-JRC_wec_merged.tif')")

print("\n# Example: Convert to COG")
print("downloader.convert_to_cog('../Benchmarks/TreeCover2000-Hansen_wec.tif')")

print("\n# Example: Validate COG")
print("downloader.validate_cog('../Benchmarks/TreeCover2000-Hansen_wec.cog.tif')")

print("\n# Example: Create forest cover map for 2022 (like in your original code)")
print("""
import rasterio

# Load cover and loss rasters
cover_raster = rasterio.open("../Benchmarks/TreeCover2000-Hansen_wec.tif")
loss_raster = rasterio.open("../Benchmarks/Loss2000-Hansen_wec.tif")

# Read the data
cover_data = cover_raster.read(1)
loss_data = loss_raster.read(1)

# Create mask for areas with forest loss
mask_non_zero = (loss_data != 0) & (loss_data != -9999)

# Remove forest from areas with loss
cover_data[mask_non_zero] = 0

# Save the modified cover raster
cover_meta = cover_raster.meta.copy()
cover_meta.update({"compress": "LZW"})

with rasterio.open("../Benchmarks/TreeCover2022-Hansen_wec.tif", "w", **cover_meta) as dst:
    dst.write(cover_data, 1)

# Convert to COG
downloader.convert_to_cog("../Benchmarks/TreeCover2022-Hansen_wec.tif")
""")

print("\n" + "=" * 60)
print("Setup complete! Check the tasks page for download progress.")
print("=" * 60)