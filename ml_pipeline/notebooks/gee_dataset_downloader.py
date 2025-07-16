"""
GEE Dataset Downloader for ChocoForestWatch

This module provides a simple interface for downloading and processing datasets
from Google Earth Engine, with automatic clipping to Western Ecuador boundary
and COG conversion for optimal STAC/TiTiler integration.
"""

import ee
import geemap
import os
import rasterio
from rasterio.merge import merge
from pathlib import Path
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GEEDatasetDownloader:
    """
    A class for downloading and processing datasets from Google Earth Engine.
    
    Features:
    - Automatic clipping to Western Ecuador boundary
    - COG conversion with tiles and overviews
    - Consistent naming and nodata handling
    - Support for multi-tile exports with merging
    """
    
    def __init__(self, boundary_shapefile=None, output_dir=None, nodata_value=-9999):
        """
        Initialize the GEE Dataset Downloader.
        
        Args:
            boundary_shapefile (str): Path to Western Ecuador boundary shapefile
            output_dir (str): Directory to save downloaded datasets
            nodata_value (int): Standard nodata value to use
        """
        self.nodata_value = nodata_value
        
        # Set default paths
        if boundary_shapefile is None:
            boundary_shapefile = "./shapefiles/Ecuador DEM 900m contour.shp"
        if output_dir is None:
            output_dir = "./dataset_rasters"
            
        self.boundary_shapefile = boundary_shapefile
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize Earth Engine
        try:
            ee.Initialize()
            logger.info("Earth Engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Earth Engine: {e}")
            raise
            
        # Load Western Ecuador boundary
        try:
            self.wec_aoi = geemap.shp_to_ee(self.boundary_shapefile).first()
            logger.info(f"Loaded boundary from {self.boundary_shapefile}")
        except Exception as e:
            logger.error(f"Failed to load boundary shapefile: {e}")
            raise
    
    def export_to_drive(self, image, description, folder="Benchmarks", scale=30, max_pixels=1e12):
        """
        Export an image to Google Drive.
        
        Args:
            image (ee.Image): The image to export
            description (str): Description for the exported image
            folder (str): Folder path in Google Drive
            scale (int): Scale of the exported image in meters
            max_pixels (int): Maximum number of pixels allowed
            
        Returns:
            ee.batch.Task: The export task
        """
        task = ee.batch.Export.image.toDrive(**{
            'image': image,
            'description': description,
            'folder': folder,
            'region': self.wec_aoi.geometry(),
            'scale': scale,
            'maxPixels': max_pixels
        }, formatOptions={
            'noData': self.nodata_value
        })
        task.start()
        logger.info(f"Started export task: {description}")
        return task
    
    def download_dataset(self, collection_id, band=None, description=None, scale=30, 
                        image_index=None, date_range=None, reduce_method='median'):
        """
        Download a dataset from Google Earth Engine.
        
        Args:
            collection_id (str): GEE collection ID or image ID
            band (str): Specific band to select (optional)
            description (str): Description for the export
            scale (int): Scale in meters
            image_index (int): Index for ImageCollection (optional)
            date_range (tuple): Date range for filtering (start, end)
            reduce_method (str): Method for reducing ImageCollection ('median', 'mosaic', etc.)
            
        Returns:
            ee.batch.Task: The export task
        """
        try:
            # Try to load as Image first, then as ImageCollection
            try:
                dataset = ee.Image(collection_id)
                logger.info(f"Loaded as Image: {collection_id}")
            except:
                dataset = ee.ImageCollection(collection_id)
                logger.info(f"Loaded as ImageCollection: {collection_id}")
                
                # Filter by date range if provided
                if date_range:
                    dataset = dataset.filterDate(date_range[0], date_range[1])
                    logger.info(f"Filtered by date range: {date_range}")
                
                # Select specific image by index if provided
                if image_index is not None:
                    image_list = dataset.toList(dataset.size())
                    dataset = ee.Image(image_list.get(image_index))
                    logger.info(f"Selected image at index: {image_index}")
                else:
                    # Reduce ImageCollection to single image
                    if reduce_method == 'median':
                        dataset = dataset.median()
                    elif reduce_method == 'mosaic':
                        dataset = dataset.mosaic()
                    elif reduce_method == 'first':
                        dataset = dataset.first()
                    else:
                        raise ValueError(f"Unsupported reduce method: {reduce_method}")
                    logger.info(f"Reduced ImageCollection using: {reduce_method}")
            
            # Select specific band if provided
            if band:
                dataset = dataset.select(band)
                logger.info(f"Selected band: {band}")
            
            # Clip to Western Ecuador boundary
            dataset = dataset.clip(self.wec_aoi)
            
            # Set nodata values
            dataset = dataset.unmask(value=self.nodata_value, sameFootprint=False)
            
            # Generate description if not provided
            if description is None:
                description = f"{collection_id.replace('/', '-').replace('_', '-')}_wec"
            
            # Export to Drive
            task = self.export_to_drive(dataset, description, scale=scale)
            
            logger.info(f"Dataset download initiated: {description}")
            return task
            
        except Exception as e:
            logger.error(f"Failed to download dataset {collection_id}: {e}")
            raise
    
    def merge_rasters(self, file_paths, output_file):
        """
        Merge multiple rasters into one and save it to the output file.
        
        Args:
            file_paths (list): List of file paths of the input rasters
            output_file (str): File path of the output merged raster
        """
        # Check if any of the file names contain 'merged'
        for file_path in file_paths:
            if 'merged' in file_path:
                raise ValueError("File names with 'merged' are not allowed.")
        
        logger.info(f"Merging {len(file_paths)} rasters:")
        for file_path in file_paths:
            logger.info(f"  - {file_path}")
        
        # Open the input rasters
        rasters = [rasterio.open(file_path) for file_path in file_paths]
        
        try:
            # Merge the rasters into one
            merged_raster, merged_transform = merge(rasters)
            
            # Update the metadata of the merged raster
            merged_meta = rasters[0].meta.copy()
            merged_meta.update({
                "driver": "GTiff",
                "height": merged_raster.shape[1],
                "width": merged_raster.shape[2],
                "transform": merged_transform,
                "compress": "LZW",
            })
            
            # Save the merged raster to the output file
            with rasterio.open(output_file, "w", **merged_meta) as dst:
                dst.write(merged_raster)
            
            logger.info(f"Merged raster saved to: {output_file}")
            
        finally:
            # Close all rasters
            for raster in rasters:
                raster.close()
    
    def get_file_paths(self, directory, search_string):
        """
        Returns a list of file paths in the given directory that match the search string.
        
        Args:
            directory (str): The directory to search for files
            search_string (str): The string to search for in file names
            
        Returns:
            list: List of file paths that match the search string
        """
        file_paths = []
        directory = Path(directory)
        
        if not directory.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return file_paths
        
        for filename in directory.iterdir():
            if filename.is_file() and search_string in filename.name:
                file_paths.append(str(filename))
        
        return sorted(file_paths)
    
    def convert_to_cog(self, input_file, output_file=None, tile_size=512, 
                      compression='LZW', overview_levels=None):
        """
        Convert a GeoTIFF to Cloud Optimized GeoTIFF format.
        
        Args:
            input_file (str): Path to input GeoTIFF
            output_file (str): Path to output COG file (optional)
            tile_size (int): Internal tile size
            compression (str): Compression method
            overview_levels (list): Overview levels to generate
            
        Returns:
            str: Path to the output COG file
        """
        input_path = Path(input_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Generate output filename if not provided
        if output_file is None:
            output_file = input_path.with_suffix('.cog.tif')
        
        output_path = Path(output_file)
        
        # Default overview levels if not provided
        if overview_levels is None:
            overview_levels = [2, 4, 8, 16, 32]
        
        try:
            # Use rio cogeo to convert to COG
            cmd = [
                'rio', 'cogeo', 'create',
                '--blocksize', str(tile_size),
                '--compress', compression,
                '--overview-level', str(overview_levels[0]),
                str(input_path),
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"COG conversion failed: {result.stderr}")
                raise RuntimeError(f"COG conversion failed: {result.stderr}")
            
            logger.info(f"Successfully converted to COG: {output_file}")
            return str(output_path)
            
        except FileNotFoundError:
            logger.error("rio cogeo not found. Please install rasterio with: pip install rasterio[cogeo]")
            raise
        except Exception as e:
            logger.error(f"COG conversion failed: {e}")
            raise
    
    def validate_cog(self, file_path):
        """
        Validate that a file is a proper Cloud Optimized GeoTIFF.
        
        Args:
            file_path (str): Path to the file to validate
            
        Returns:
            bool: True if valid COG, False otherwise
        """
        try:
            result = subprocess.run(['rio', 'cogeo', 'validate', file_path], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Valid COG: {file_path}")
                return True
            else:
                logger.warning(f"Invalid COG: {file_path}")
                logger.warning(result.stdout)
                return False
                
        except FileNotFoundError:
            logger.error("rio cogeo not found. Please install rasterio with: pip install rasterio[cogeo]")
            return False
        except Exception as e:
            logger.error(f"COG validation failed: {e}")
            return False
    
    def plot_map(self, image, title="Dataset"):
        """
        Plot a map with the given image and area of interest.
        
        Args:
            image (ee.Image): The image to plot
            title (str): Title for the map
            
        Returns:
            geemap.Map: The map object
        """
        Map = geemap.Map()
        Map.addLayer(self.wec_aoi, {}, 'Western Ecuador AOI')
        Map.addLayer(image, {}, title)
        Map.centerObject(self.wec_aoi, zoom=8)
        return Map