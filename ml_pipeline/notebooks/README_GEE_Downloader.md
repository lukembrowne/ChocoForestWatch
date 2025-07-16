# GEE Dataset Downloader

A streamlined Python class for downloading and processing datasets from Google Earth Engine for the ChocoForestWatch project.

## Features

- **Automatic clipping** to Western Ecuador boundary
- **COG conversion** with tiles and overviews for optimal STAC/TiTiler integration
- **Consistent naming** and nodata handling (-9999)
- **Multi-tile export support** with automatic merging
- **Progress tracking** and error handling
- **Validation tools** for COG compliance

## Installation

Ensure you have the required dependencies:

```bash
pip install earthengine-api geemap rasterio[cogeo] geopandas
```

## Quick Start

```python
from gee_dataset_downloader import GEEDatasetDownloader

# Initialize downloader
downloader = GEEDatasetDownloader()

# Download a dataset
task = downloader.download_dataset(
    collection_id="UMD/hansen/global_forest_change_2022_v1_10",
    band="treecover2000",
    description="TreeCover2000-Hansen_wec",
    scale=30
)

# After download completes, convert to COG
downloader.convert_to_cog("TreeCover2000-Hansen_wec.tif")
```

## Common Usage Patterns

### 1. Simple Image Download

```python
# Download Hansen tree cover
task = downloader.download_dataset(
    collection_id="UMD/hansen/global_forest_change_2022_v1_10",
    band="treecover2000",
    description="TreeCover2000-Hansen_wec",
    scale=30
)
```

### 2. ImageCollection with Median Reduction

```python
# Download JRC Forest Cover (requires median composite)
task = downloader.download_dataset(
    collection_id="JRC/GFC2020/V1",
    description="ForestCover2020-JRC_wec",
    scale=10,
    reduce_method="median"
)
```

### 3. ImageCollection with Specific Index

```python
# Download specific year from PALSAR collection
task = downloader.download_dataset(
    collection_id="JAXA/ALOS/PALSAR/YEARLY/FNF4",
    description="PALSAR2020_wec",
    scale=25,
    image_index=3  # Index 3 = 2020
)
```

### 4. Handle Multi-tile Exports

```python
# Find all tiles for a dataset
file_paths = downloader.get_file_paths("../Benchmarks", "ForestCover2020-JRC_wec")

# Merge if multiple tiles
if len(file_paths) > 1:
    downloader.merge_rasters(file_paths, "../Benchmarks/ForestCover2020-JRC_wec_merged.tif")
    
# Convert merged file to COG
downloader.convert_to_cog("../Benchmarks/ForestCover2020-JRC_wec_merged.tif")
```

### 5. COG Processing

```python
# Convert to COG
cog_file = downloader.convert_to_cog("input.tif", "output.cog.tif")

# Validate COG
is_valid = downloader.validate_cog(cog_file)

# Batch convert directory
from utils.cog_processor import COGProcessor
processor = COGProcessor()
converted_files = processor.batch_convert_to_cog("../Benchmarks/")
```

## Dataset Examples

Based on your existing datasets.json, here are common patterns:

### Hansen Global Forest Change

```python
# Tree cover 2000
downloader.download_dataset(
    collection_id="UMD/hansen/global_forest_change_2022_v1_10",
    band="treecover2000",
    description="TreeCover2000-Hansen_wec",
    scale=30
)

# Forest loss
downloader.download_dataset(
    collection_id="UMD/hansen/global_forest_change_2022_v1_10",
    band="lossyear",
    description="Loss2000-Hansen_wec",
    scale=30
)
```

### ESA WorldCover

```python
downloader.download_dataset(
    collection_id="ESA/WorldCover/v100",
    description="LandCover2020-ESA_wec",
    scale=10,
    reduce_method="first"
)
```

### JRC Forest Cover

```python
downloader.download_dataset(
    collection_id="JRC/GFC2020/V1",
    description="ForestCover2020-JRC_wec",
    scale=10,
    reduce_method="median"
)
```

### PALSAR

```python
downloader.download_dataset(
    collection_id="JAXA/ALOS/PALSAR/YEARLY/FNF4",
    description="PALSAR2020_wec",
    scale=25,
    image_index=3
)
```

### MapBiomas (External)

For MapBiomas Ecuador, use the existing rasterio-based approach:

```python
import rasterio
from rasterio.mask import mask
import geopandas as gpd

# Load AOI
aoi_gdf = gpd.read_file("./shapefiles/Ecuador DEM 900m contour.shp")
aoi_geometry = aoi_gdf.geometry.values[0]

# Clip downloaded MapBiomas data
with rasterio.open("ecuador_coverage_2022.tif") as src:
    clipped_raster, transform = mask(src, [aoi_geometry], crop=True)
    # ... rest of processing
```

## Configuration

The downloader uses these default settings:

- **Boundary shapefile**: `./shapefiles/Ecuador DEM 900m contour.shp`
- **Output directory**: `./dataset_rasters`
- **Nodata value**: -9999
- **COG tile size**: 512x512
- **Compression**: LZW

Override during initialization:

```python
downloader = GEEDatasetDownloader(
    boundary_shapefile="./custom_boundary.shp",
    output_dir="./custom_output",
    nodata_value=-32768
)
```

## Monitoring Downloads

All downloads are exported to Google Drive. Monitor progress at:
https://code.earthengine.google.com/tasks

## Post-processing Workflow

1. **Download from Drive** to local machine
2. **Merge tiles** if multiple files exist
3. **Convert to COG** for optimal performance
4. **Validate COG** to ensure compliance
5. **Upload to STAC** collection via your existing pipeline

## Error Handling

The downloader includes comprehensive error handling:

- **EE initialization** failures
- **Shapefile loading** errors
- **Dataset access** issues
- **COG conversion** failures
- **File validation** problems

Check logs for detailed error information.

## Integration with Existing Workflow

This downloader is designed to work seamlessly with your existing:

- **datasets.json** configuration (manual updates)
- **STAC/TiTiler** pipeline (COG-optimized outputs)
- **merge_rasters()** function (compatible interface)
- **Docker environment** (all dependencies available)

## Tips

1. **Always convert to COG** for best performance with TiTiler
2. **Check for multi-tile exports** and merge before COG conversion
3. **Use consistent naming** patterns for easy identification
4. **Monitor Earth Engine quotas** to avoid rate limiting
5. **Validate COGs** before uploading to STAC collections