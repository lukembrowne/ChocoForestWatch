#!/usr/bin/env python3
"""
Process GFW Integrated Deforestation Alerts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This script downloads and processes Global Forest Watch (GFW) integrated deforestation alert 
tiles for Ecuador for the years 2022-2024. Instead of converting to polygons, it maintains 
the raster format for display in the web interface with click-to-query functionality.

The script:
1. Downloads GFW alert tiles covering Ecuador
2. Clips them to Ecuador boundary 
3. Creates annual composites
4. Stores in unified dataset structure
5. Creates STAC collections for tile serving

Usage:
    poetry run process_gfw_alerts.py --years 2022 2023 2024
"""

import os
import sys
import json
import tempfile
import requests
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
from multiprocessing import Pool, cpu_count

import rasterio
import numpy as np
from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.enums import Compression
from shapely.geometry import shape, box
from shapely.ops import unary_union

# Add the ml_pipeline source to the path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ml_pipeline.stac_builder import STACManager, STACManagerConfig
from ml_pipeline.s3_utils import upload_file
from ml_pipeline.version import get_version_metadata

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def process_pixel_chunk(args: Tuple[np.ndarray, int, int, datetime, datetime, int]) -> Tuple[List[int], int]:
    """
    Process a chunk of pixel values to find alerts for a specific year.
    
    Args:
        args: Tuple containing (pixel_chunk, chunk_start_idx, raster_width, start_date, end_date, year)
    
    Returns:
        Tuple of (alert_indices, valid_pixel_count) where alert_indices are relative to chunk_start_idx
    """
    pixel_chunk, chunk_start_idx, raster_width, start_date, end_date, year = args
    
    alert_indices = []
    valid_pixel_count = 0
    
    for i, value in enumerate(pixel_chunk):
        if value > 0:  # Skip nodata pixels
            valid_pixel_count += 1
            
            # Decode GFW date and confidence
            if value == 0:
                continue
                
            encoded_str = str(value)
            
            # Handle single digit values (confidence only, no date)
            if len(encoded_str) == 1:
                continue
            
            # Get confidence level from first digit
            confidence = int(encoded_str[0])
            
            # Get days since Dec 31, 2014
            days = int(encoded_str[1:])
            
            # Calculate date
            base_date = datetime(2014, 12, 31)
            alert_date = base_date + timedelta(days=days)
            
            # Check if alert is in target year
            if start_date <= alert_date <= end_date:
                alert_indices.append(chunk_start_idx + i)
    
    return alert_indices, valid_pixel_count


class GFWAlertsProcessor:
    """Process GFW integrated deforestation alerts for raster display."""
    
    def __init__(self, output_dir: str = "gfw_alerts_output"):
        self.api_key = os.environ.get("GFW_API_KEY")
        if not self.api_key:
            raise ValueError("GFW_API_KEY environment variable is required")
        self.base_url = "https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff"
        
        # GFW tiles that cover Ecuador
        self.gfw_tiles = [
            "10N_080W",
            "00N_080W", 
            "00N_090W",
            "10N_090W"
        ]
        
        # Ecuador boundary path - prioritize local file over environment variable
        # to avoid Docker DNS issues when running outside containers
        local_boundary_path = Path(__file__).parent / "boundaries" / "Ecuador-DEM-900m-contour.geojson"
        
        if local_boundary_path.exists():
            self.ecuador_boundary_path = str(local_boundary_path)
            logger.info(f"Using local boundary file: {self.ecuador_boundary_path}")
        else:
            # Fallback to environment variable (for Docker environments)
            self.ecuador_boundary_path = os.environ.get("BOUNDARY_GEOJSON_PATH")
            logger.info(f"Local boundary not found, using environment variable: {self.ecuador_boundary_path}")
        
        # Output directory
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Cache directory for downloaded tiles
        self.cache_dir = self.output_dir / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        logger.info(f"Initialized GFW Alerts Processor")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Cache directory: {self.cache_dir}")
        logger.info(f"Ecuador boundary: {self.ecuador_boundary_path}")
    
    def load_ecuador_boundary(self):
        """Load Ecuador boundary from GeoJSON file or URL."""
        try:
            if not self.ecuador_boundary_path:
                raise ValueError("No Ecuador boundary path configured")
                
            # Handle both HTTP URLs and file paths
            if self.ecuador_boundary_path.startswith(("http://", "https://")):
                logger.info(f"Loading boundary from URL: {self.ecuador_boundary_path}")
                resp = requests.get(self.ecuador_boundary_path, timeout=30)
                resp.raise_for_status()
                boundary_geojson = resp.json()
            else:
                logger.info(f"Loading boundary from file: {self.ecuador_boundary_path}")
                with open(self.ecuador_boundary_path, 'r', encoding='utf-8') as f:
                    boundary_geojson = json.load(f)
            
            # Extract geometry from FeatureCollection and create a single shape
            geometries = []
            for feature in boundary_geojson['features']:
                geom = shape(feature['geometry'])
                geometries.append(geom)
            
            # Union all geometries into a single shape
            boundary_shape = unary_union(geometries)
            
            logger.info(f"Loaded Ecuador boundary with {len(geometries)} features")
            return boundary_shape
            
        except Exception as e:
            logger.error(f"Failed to load Ecuador boundary: {str(e)}")
            raise
    
    def download_gfw_tile(self, tile_id: str, force_download: bool = False) -> str:
        """Download a GFW tile if not already cached."""
        cache_filename = f"gfw_{tile_id}_integrated_alerts.tif"
        cache_path = self.cache_dir / cache_filename
        
        # Return cached file if it exists and force_download is False
        if cache_path.exists() and not force_download:
            logger.info(f"Using cached GFW tile: {cache_filename}")
            return str(cache_path)
        
        # Download the tile
        url = f"{self.base_url}?grid=10/100000&tile_id={tile_id}&pixel_meaning=date_conf&x-api-key={self.api_key}"
        
        logger.info(f"Downloading GFW tile {tile_id} from {url}")
        
        try:
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Downloaded GFW tile to {cache_path}")
            return str(cache_path)
            
        except Exception as e:
            logger.error(f"Failed to download GFW tile {tile_id}: {str(e)}")
            raise
    
    def decode_gfw_date(self, value: int) -> tuple[Optional[datetime], Optional[int]]:
        """
        Decode GFW alert date and confidence from pixel value.
        
        Returns:
            tuple: (alert_date, confidence_level) or (None, None) for nodata
        """
        if value == 0:
            return None, None
        
        # Convert to string for easier processing
        encoded_str = str(value)
        
        # Handle single digit values (confidence only, no date)
        if len(encoded_str) == 1:
            return None, int(encoded_str)
        
        # Get confidence level from first digit
        confidence = int(encoded_str[0])
        
        # Get days since Dec 31, 2014
        days = int(encoded_str[1:])
        
        # Calculate date
        base_date = datetime(2014, 12, 31)
        alert_date = base_date + timedelta(days=days)
        
        return alert_date, confidence
    
    def _build_overviews(self, file_path: str) -> None:
        """Build overviews (pyramids) for better TiTiler performance."""
        try:
            with rasterio.open(file_path, 'r+') as dataset:
                # Build overviews at multiple levels for both bands
                overview_levels = [2, 4, 8, 16, 32]
                dataset.build_overviews(overview_levels, Resampling.nearest)
                dataset.update_tags(ns='rio_overview', resampling='nearest')
                logger.info(f"Built overviews for {file_path}")
        except Exception as e:
            logger.warning(f"Failed to build overviews for {file_path}: {str(e)}")
    
    def process_tile_for_year(self, tile_path: str, boundary_shape, year: int) -> Optional[str]:
        """
        Process a single GFW tile to extract alerts for a specific year.
        
        Returns:
            str: Path to the processed tile, or None if no alerts found
        """
        tile_name = Path(tile_path).stem
        logger.info(f"Processing tile {tile_name} for year {year}")
        
        # Define year date range
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        
        with rasterio.open(tile_path) as src:
            logger.info(f"Opened raster - Shape: {src.shape}, Bounds: {src.bounds}")
            
            # Check if tile intersects with boundary
            tile_bounds = box(*src.bounds)
            if not tile_bounds.intersects(boundary_shape):
                logger.info(f"Tile does not intersect with Ecuador boundary - skipping")
                return None
            
            try:
                # Use the simpler approach: clip the source data to boundary first
                logger.info(f"Clipping source data to boundary...")
                clipped_data, clipped_transform = mask(src, [boundary_shape], crop=True, filled=False)
                clipped_shape = clipped_data[0].shape
                total_pixels = clipped_shape[0] * clipped_shape[1]
                logger.info(f"Clipped to shape: {clipped_shape} ({total_pixels:,} pixels)")
                
                # Create boundary mask for the clipped raster
                logger.info("Creating boundary mask for clipped data...")
                from rasterio.features import geometry_mask
                
                boundary_mask = geometry_mask(
                    [boundary_shape],
                    transform=clipped_transform,
                    invert=True,  # True means inside boundary
                    out_shape=clipped_data[0].shape
                )
                
                # Create output arrays based on clipped dimensions
                logger.info(f"Creating output arrays for {year} alerts...")
                # Band 1: Binary alerts (0=no alert, 1=alert, 255=missing data)
                # Start with ALL pixels as 255 (missing), then set boundary pixels to 0 (no alerts)
                binary_output = np.full_like(clipped_data[0], 255, dtype=np.uint8)
                # Band 2: Original encoded values
                original_output = np.zeros_like(clipped_data[0], dtype=np.uint16)
                
                # Set areas INSIDE boundary to 0 (no alerts by default)
                binary_output[boundary_mask] = 0
                
                # Count boundary pixels
                inside_boundary_count = np.sum(boundary_mask)
                outside_boundary_count = np.sum(~boundary_mask)
                logger.info(f"Boundary masking: {inside_boundary_count:,} pixels inside, {outside_boundary_count:,} pixels outside")
                
                # Now process the clipped data directly (no coordinate transformation needed)
                logger.info("Processing clipped GFW data for alerts...")
                src_data = clipped_data[0]
                
                # Process clipped data directly (no coordinate transformation needed)
                src_height, src_width = src_data.shape
                total_src_pixels = src_height * src_width
                
                # Process source data to find alerts for this year
                alert_count = 0
                logger.info(f"Scanning {total_src_pixels:,} clipped pixels for {year} alerts...")
                
                # First, let's get some sample values to debug
                sample_values = src_data.flat[:1000]
                non_zero_values = sample_values[sample_values > 0]
                logger.info(f"Sample of non-zero values in clipped data: {non_zero_values[:10] if len(non_zero_values) > 0 else 'None found'}")
                
                # Test decode a few sample values to see what dates we get
                if len(non_zero_values) > 0:
                    logger.info(f"Testing date decoding for {year}:")
                    for i, val in enumerate(non_zero_values[:5]):
                        encoded_str = str(val)
                        if len(encoded_str) > 1:
                            try:
                                days = int(encoded_str[1:])
                                base_date = datetime(2014, 12, 31)
                                alert_date = base_date + timedelta(days=days)
                                in_year = start_date <= alert_date <= end_date
                               # logger.info(f"  Value {val} -> Date {alert_date.strftime('%Y-%m-%d')} -> In {year}: {in_year}")
                            except Exception as e:
                                logger.info(f"  Value {val} -> Error: {e}")
                
                # Find all pixels with values > 0 (potential alerts)
                valid_pixels = np.where(src_data > 0)
                valid_count = len(valid_pixels[0])
                logger.info(f"Found {valid_count:,} pixels with data in clipped raster")
                
                if valid_count == 0:
                    logger.warning(f"No valid data found in clipped raster for {tile_name}")
                    
                # Process each valid pixel directly in the clipped coordinate space
                progress_interval = max(1000, valid_count // 50)  # Report 50 times max
                
                for i in range(valid_count):
                    row, col = valid_pixels[0][i], valid_pixels[1][i]
                    value = src_data[row, col]
                    
                    # Only process pixels that are inside the boundary
                    if not boundary_mask[row, col]:
                        continue
                    
                    # Decode GFW date and confidence
                    encoded_str = str(value)
                    
                    # Skip single digit values (confidence only, no date)
                    if len(encoded_str) <= 1:
                        continue
                    
                    try:
                        # Get days since Dec 31, 2014
                        days = int(encoded_str[1:])
                        
                        # Calculate date
                        base_date = datetime(2014, 12, 31)
                        alert_date = base_date + timedelta(days=days)
                        
                        # Check if alert is in target year
                        if start_date <= alert_date <= end_date:
                            # Set alert directly in the clipped coordinate space
                            binary_output[row, col] = 1  # Set alert
                            original_output[row, col] = value
                            alert_count += 1
                    
                    except (ValueError, OverflowError):
                        continue
                    
                    # Progress reporting (much less frequent)
                    if i % progress_interval == 0 and i > 0:
                        progress = (i / valid_count) * 100
                        logger.info(f"  Progress: {progress:.0f}% - Found {alert_count} alerts so far")
                
                # Debug: Check what values we ended up with in the output
                output_unique, output_counts = np.unique(binary_output, return_counts=True)
                logger.info(f"Output raster value distribution:")
                for val, count in zip(output_unique, output_counts):
                    pct = count / binary_output.size * 100
                    logger.info(f"  Value {val}: {count:,} pixels ({pct:.1f}%)")
                
                logger.info(f"Processing complete - Inside boundary: {inside_boundary_count:,}, "
                          f"Alerts for {year}: {alert_count} ({alert_count/inside_boundary_count*100:.3f}% of analyzed area)")
                
                # Always create the file even if no alerts (we want the full raster with 0s)
                if alert_count == 0:
                    logger.info(f"No alerts found for {year} in tile {tile_name}, but creating output raster anyway")
                    # Don't return None - we want the complete raster with 0s
                
                # Create output file
                output_path = self.output_dir / f"{tile_name}_{year}_alerts.tif"
                
                # Create profile for Cloud Optimized GeoTIFF (COG) with 2 bands
                profile = src.profile.copy()
                profile.update({
                    'height': clipped_data.shape[1],
                    'width': clipped_data.shape[2],
                    'transform': clipped_transform,
                    'count': 2,  # Two bands
                    'dtype': 'uint16',  # Use uint16 to accommodate both bands
                    'nodata': 255,  # Set nodata value to 255 for missing areas
                    'compress': 'lzw',  # Better compression for mixed data types
                    'tiled': True,
                    'blockxsize': 512,
                    'blockysize': 512,
                    'interleave': 'pixel',  # Better for multi-band access
                    'BIGTIFF': 'IF_SAFER',  # Handle large files properly
                })
                
                # Write output raster with two bands
                with rasterio.open(output_path, 'w', **profile) as dst:
                    # Band 1: Binary alerts (0=no alert, 1=alert, 255=missing data)
                    dst.write(binary_output.astype(np.uint8), 1)
                    dst.set_band_description(1, f'GFW Binary Alerts {year} (0=no alert, 1=alert, 255=missing)')
                    
                    # Band 2: Original encoded values for date extraction
                    dst.write(original_output, 2)
                    dst.set_band_description(2, f'GFW Original Encoded Values {year}')
                    
                    # Add metadata
                    dst.update_tags(
                        source='Global Forest Watch',
                        year=str(year),
                        alert_count=str(alert_count),
                        processing_date=datetime.now().isoformat(),
                        band_1_description='Binary alerts: 0=no alert, 1=alert, 255=missing data',
                        band_2_description='Original GFW encoded values for date/confidence extraction',
                        encoding_format='First digit: confidence level (1-4), remaining digits: days since 2014-12-31',
                        **get_version_metadata()
                    )
                
                # Build overviews for better TiTiler performance
                logger.info(f"Building overviews for {output_path}...")
                self._build_overviews(output_path)
                
                logger.info(f"Saved {year} alerts to {output_path}")
                return str(output_path)
                
            except Exception as e:
                logger.error(f"Error processing tile {tile_name} for {year}: {str(e)}")
                return None
    
    def merge_tiles_for_year(self, tile_paths: List[str], year: int) -> str:
        """Merge processed tiles for a specific year into a single raster."""
        logger.info(f"Merging {len(tile_paths)} tiles for {year}")
        
        # Debug: log details about each tile before merging
        for tile_path in tile_paths:
            tile_name = Path(tile_path).stem
            with rasterio.open(tile_path) as src:
                # Check alert distribution in this tile
                band1_data = src.read(1)
                unique_vals, counts = np.unique(band1_data, return_counts=True)
                alert_count = counts[unique_vals == 1].sum() if 1 in unique_vals else 0
                no_alert_count = counts[unique_vals == 0].sum() if 0 in unique_vals else 0
                missing_count = counts[unique_vals == 255].sum() if 255 in unique_vals else 0
                
                logger.info(f"  {tile_name}: {alert_count:,} alerts, {no_alert_count:,} no-alerts, {missing_count:,} missing")
                logger.info(f"    Bounds: {src.bounds}, Transform: {src.transform}")
        
        # Open all tiles
        src_files = []
        try:
            for tile_path in tile_paths:
                src_files.append(rasterio.open(tile_path))
            
            # Merge tiles with more debugging
            logger.info("Starting rasterio.merge() operation...")
            merged_data, merged_transform = merge(src_files)
            logger.info(f"Merge complete - Output shape: {merged_data.shape}")
            
            # Debug: Check merged data distribution  
            unique_vals, counts = np.unique(merged_data[0], return_counts=True)  # Check band 1
            logger.info("Merged raster distribution:")
            for val, count in zip(unique_vals, counts):
                pct = count / merged_data[0].size * 100
                logger.info(f"  Value {val}: {count:,} pixels ({pct:.1f}%)")
            
            # Create output path
            output_path = self.output_dir / f"gfw_integrated_alerts_{year}_ecuador.tif"
            
            # Get profile from first tile and update for merged raster
            profile = src_files[0].profile.copy()
            profile.update({
                'height': merged_data.shape[1],
                'width': merged_data.shape[2],
                'transform': merged_transform,
                'dtype': 'uint16',
                'nodata': 255,  # Set nodata value to 255 for missing areas
                'compress': 'deflate',
                'tiled': True,
                'blockxsize': 512,
                'blockysize': 512,
            })
            
            # Write merged raster with two bands
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(merged_data)
                dst.set_band_description(1, f'GFW Binary Alerts {year} - Ecuador (0=no alert, 1=alert, 255=missing)')
                dst.set_band_description(2, f'GFW Original Encoded Values {year} - Ecuador')
                
                # Add metadata
                dst.update_tags(
                    source='Global Forest Watch',
                    year=str(year),
                    region='Ecuador',
                    tiles_merged=str(len(tile_paths)),
                    processing_date=datetime.now().isoformat(),
                    band_1_description='Binary alerts: 0=no alert, 1=alert, 255=missing data',
                    band_2_description='Original GFW encoded values for date/confidence extraction',
                    encoding_format='First digit: confidence level (1-4), remaining digits: days since 2014-12-31',
                    **get_version_metadata()
                )
            
            # Build overviews for the merged raster
            logger.info(f"Building overviews for merged raster {output_path}...")
            self._build_overviews(output_path)
            
            logger.info(f"Merged {year} alerts saved to {output_path}")
            return str(output_path)
            
        finally:
            # Close all source files
            for src in src_files:
                src.close()
    
    def upload_to_s3_and_stac(self, merged_file_path: str, year: int) -> None:
        """Upload merged raster to S3 and create STAC collection in both local and remote databases."""
        logger.info(f"Uploading {year} alerts to S3 and creating STAC collection")
        
        # Upload to unified dataset structure
        s3_key = f"datasets/gfw-integrated-alerts/{year}/gfw_integrated_alerts_{year}_ecuador.tif"
        upload_file(merged_file_path, s3_key)
        logger.info(f"Uploaded to S3: {s3_key}")
        
        # Create STAC collection config
        config = {
            "collection_id": f"datasets-gfw-integrated-alerts-{year}",
            "year": year,
            "s3_prefix": "datasets/gfw-integrated-alerts",
            "asset_title": f"GFW Integrated Deforestation Alerts {year}"
        }
        
        self._create_stac_collection(config)
    
    def _create_stac_collection(self, config: Dict):
        """Create new STAC collection for the processed dataset in both local and remote databases"""
        try:
            # Create collection in remote database (default)
            logger.info(f"Creating STAC collection in remote database: {config['collection_id']}")
            stac_manager = STACManager()
            logger.info(f"Remote DB connection details: Host={stac_manager.cfg.pg_env_vars['PGHOST']}, DB={stac_manager.cfg.pg_env_vars['PGDATABASE']}")
            
            # Test remote connection
            if stac_manager.test_connection():
                logger.info("✅ Remote database connection verified")
            else:
                logger.error("❌ Remote database connection failed")
                
            stac_manager.process_year(
                year=str(config["year"]),
                prefix_on_s3=config["s3_prefix"],
                collection_id=config["collection_id"],
                asset_key="data",
                asset_roles=["data"],
                asset_title=config["asset_title"],
                extra_asset_fields={
                    "gfw:encoding": "two_band",
                    "gfw:band_1_description": "Binary alerts: 0=no alert, 1=alert, 255=missing data",
                    "gfw:band_2_description": "Original encoded values for date/confidence extraction",
                    "gfw:decoding_info": "Band 2 encoding - First digit: confidence level (1-4), remaining digits: days since 2014-12-31"
                }
            )
            logger.info(f"✅ Created STAC collection in remote database: {config['collection_id']}")
            
            # Create collection in local database
            logger.info(f"Creating STAC collection in local database: {config['collection_id']}")
            local_stac_config = STACManagerConfig(use_remote_db=False)
            local_stac_manager = STACManager(local_stac_config)
            logger.info(f"Local DB connection details: Host={local_stac_manager.cfg.pg_env_vars['PGHOST']}, DB={local_stac_manager.cfg.pg_env_vars['PGDATABASE']}")
            
            # Test local connection
            if local_stac_manager.test_connection():
                logger.info("✅ Local database connection verified")
            else:
                logger.error("❌ Local database connection failed")
            
            local_stac_manager.process_year(
                year=str(config["year"]),
                prefix_on_s3=config["s3_prefix"],
                collection_id=config["collection_id"],
                asset_key="data",
                asset_roles=["data"],
                asset_title=config["asset_title"],
                extra_asset_fields={
                    "gfw:encoding": "two_band",
                    "gfw:band_1_description": "Binary alerts: 0=no alert, 1=alert, 255=missing data",
                    "gfw:band_2_description": "Original encoded values for date/confidence extraction",
                    "gfw:decoding_info": "Band 2 encoding - First digit: confidence level (1-4), remaining digits: days since 2014-12-31"
                }
            )
            logger.info(f"✅ Created STAC collection in local database: {config['collection_id']}")
            
        except Exception as e:
            logger.error(f"Failed to create STAC collection {config['collection_id']}: {str(e)}")
            raise
    
    def process_years(self, years: List[int], force_download: bool = False, debug_only: bool = False) -> None:
        """Process GFW alerts for multiple years."""
        logger.info(f"Processing GFW alerts for years: {years}")
        if debug_only:
            logger.info("DEBUG MODE: Will only process tiles, skipping merge and upload")
        
        # Load Ecuador boundary
        boundary_shape = self.load_ecuador_boundary()
        
        for year in years:
            logger.info(f"\n=== Processing Year {year} ===")
            
            # Download and process tiles for this year
            year_tile_paths = []
            
            for tile_id in self.gfw_tiles:
                logger.info(f"Processing tile {tile_id} for {year}")
                
                # Download tile
                tile_path = self.download_gfw_tile(tile_id, force_download)
                
                # Process tile for this year
                processed_tile_path = self.process_tile_for_year(tile_path, boundary_shape, year)
                
                if processed_tile_path:
                    year_tile_paths.append(processed_tile_path)
            
            if year_tile_paths:
                logger.info(f"Successfully processed {len(year_tile_paths)} tiles for {year}")
                
                if not debug_only:
                    # Merge tiles for this year
                    merged_file_path = self.merge_tiles_for_year(year_tile_paths, year)
                    
                    # Upload to S3 and create STAC collection
                    self.upload_to_s3_and_stac(merged_file_path, year)
                else:
                    logger.info("Skipping merge and upload (debug mode)")
                
                # Keep individual tile files for debugging
                logger.info(f"Keeping {len(year_tile_paths)} intermediate tile files for debugging:")
                for tile_path in year_tile_paths:
                    logger.info(f"  Kept: {tile_path}")
                    
                logger.info(f"Completed processing for {year}")
            else:
                logger.warning(f"No alert tiles found for {year}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Process GFW Integrated Deforestation Alerts")
    parser.add_argument("--years", nargs="+", type=int, default=[2022, 2023, 2024],
                        help="Years to process (default: 2022 2023 2024)")
    parser.add_argument("--output-dir", type=str, default="gfw_alerts_output",
                        help="Output directory for processed files")
    parser.add_argument("--force-download", action="store_true",
                        help="Force re-download of cached tiles")
    parser.add_argument("--debug-only", action="store_true",
                        help="Only process tiles, skip merge and upload (for debugging)")
    
    args = parser.parse_args()
    
    # Create processor and run
    processor = GFWAlertsProcessor(args.output_dir)
    processor.process_years(args.years, args.force_download, args.debug_only)
    
    logger.info("GFW alerts processing completed!")


if __name__ == "__main__":
    main()