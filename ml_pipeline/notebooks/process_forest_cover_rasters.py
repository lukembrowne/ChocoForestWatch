#!/usr/bin/env python3
"""
Enhanced Forest Cover Raster Re-processing Script

This script re-processes forest cover benchmark datasets with:
- Building overviews for optimal map display
- Masking values outside geojson bounds to missing data (255)
- Converting pixels to standardized forest/non-forest labels (0/1)
- Uploading optimized COGs to S3
- Managing STAC collections with backup/restore functionality

Based on the original build_benchmarks_stac.py but with significant enhancements.
"""

import argparse
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys
import os

# Add ml_pipeline to path for imports
sys.path.append(str(Path(__file__).parent.parent / "ml_pipeline" / "src"))

from ml_pipeline.stac_builder import STACManager, STACManagerConfig
from ml_pipeline.s3_utils import upload_file, get_s3_client
from ml_pipeline.raster_utils import pixels_to_labels
import rasterio
from rasterio.mask import mask
from rasterio.features import geometry_mask
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject, transform_geom
from rasterio.crs import CRS
# Removed rasterio.cog import - using simpler gdaladdo approach
import subprocess
from rasterio.profiles import default_gtiff_profile
from shapely.geometry import shape
import numpy as np
import pyproj
from pyproj import Transformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dataset configurations - each dataset has specific processing parameters
DATASET_CONFIGS = {
    "cfw-2022": {
        "input_path": "./benchmark_rasters/northern_choco_test_2025_06_20_2022_merged_composite.tif",
        "s3_prefix": "benchmarks/CFW",
        "collection_id": "northern_choco_test_2025_06_20_2022_merged_composite",
        "asset_title": "CFW 2022",
        "year": 2022,
        "description": "CFW 2022 for Western Ecuador"
    },

    "hansen-tree-cover-2022": {
        "input_path": "./benchmark_rasters/TreeCover2022-Hansen_wec.tif",
        "s3_prefix": "benchmarks/HansenTreeCover",
        "collection_id": "benchmarks-hansen-tree-cover-2022",
        "asset_title": "Hansen Tree Cover 2022",
        "year": 2022,
        "description": "Hansen Global Forest Change Tree Cover 2022 for Western Ecuador"
    },
    "mapbiomes-2022": {
        "input_path": "./benchmark_rasters/ecuador_coverage_2022_wec.tif",
        "s3_prefix": "benchmarks/MapBiomes",
        "collection_id": "benchmarks-mapbiomes-2022",
        "asset_title": "MapBiomes 2022",
        "year": 2022,
        "description": "MapBiomes Ecuador Land Cover 2022 for Western Ecuador"
    },
    "esa-landcover-2020": {
        "input_path": "./benchmark_rasters/LandCover2020-ESA_wec_merged.tif",
        "s3_prefix": "benchmarks/ESA-Landcover",
        "collection_id": "benchmarks-esa-landcover-2020",
        "asset_title": "ESA Land Cover 2020",
        "year": 2020,
        "description": "ESA Land Cover Classification 2020 for Western Ecuador"
    },
    "jrc-forestcover-2020": {
        "input_path": "./benchmark_rasters/ForestCover2020-JRC_wec_merged.tif",
        "s3_prefix": "benchmarks/JRC-ForestCover",
        "collection_id": "benchmarks-jrc-forestcover-2020",
        "asset_title": "JRC Forest Cover 2020",
        "year": 2020,
        "description": "JRC Forest Cover Classification 2020 for Western Ecuador"
    },
    "palsar-2020": {
        "input_path": "./benchmark_rasters/PALSAR2020_wec.tif",
        "s3_prefix": "benchmarks/PALSAR",
        "collection_id": "benchmarks-palsar-2020",
        "asset_title": "PALSAR 2020",
        "year": 2020,
        "description": "PALSAR-2 Forest/Non-Forest Classification 2020 for Western Ecuador"
    },
    "wri-treecover-2020": {
        "input_path": "./benchmark_rasters/TreeCover2020-WRI_wec_merged.tif",
        "s3_prefix": "benchmarks/WRI-TreeCover",
        "collection_id": "benchmarks-wri-treecover-2020",
        "asset_title": "WRI Tree Cover 2020",
        "year": 2020,
        "description": "WRI Tree Cover Classification 2020 for Western Ecuador"
    }
}

class RasterProcessor:
    """Handles all raster processing operations"""
    
    def __init__(self, boundary_geojson_path: Optional[str] = None):
        """
        Initialize the raster processor.
        
        Parameters
        ----------
        boundary_geojson_path : str, optional
            Path to GeoJSON file for boundary masking
        """
        self.boundary_geojson_path = boundary_geojson_path
        self.boundary_geom = None
        self.boundary_crs = None
        
        if boundary_geojson_path:
            self._load_boundary()
    
    def _load_boundary(self):
        """Load boundary geometry from GeoJSON file with CRS detection"""
        try:
            logger.info(f"Loading boundary from: {self.boundary_geojson_path}")
            with open(self.boundary_geojson_path, 'r') as f:
                geojson = json.load(f)
            
            # Detect CRS from GeoJSON
            crs_info = geojson.get('crs')
            if crs_info:
                # Handle CRS from GeoJSON CRS object
                if 'properties' in crs_info and 'name' in crs_info['properties']:
                    crs_name = crs_info['properties']['name']
                    self.boundary_crs = CRS.from_string(crs_name)
                else:
                    self.boundary_crs = CRS.from_dict(crs_info)
            else:
                # Default to WGS84 (lat/long) for GeoJSON without explicit CRS
                self.boundary_crs = CRS.from_epsg(4326)
                logger.info("No CRS found in GeoJSON, assuming WGS84 (EPSG:4326)")
            
            logger.info(f"Boundary CRS: {self.boundary_crs}")
            
            # Combine all features into a single geometry
            geoms = [shape(feat['geometry']) for feat in geojson.get('features', [])]
            
            if len(geoms) == 1:
                self.boundary_geom = geoms[0]
            elif len(geoms) > 1:
                from shapely.ops import unary_union
                self.boundary_geom = unary_union(geoms)
            else:
                raise ValueError("No features found in GeoJSON")
                
            logger.info(f"Loaded boundary geometry: {self.boundary_geom.geom_type}")
            
        except Exception as e:
            logger.error(f"Failed to load boundary: {str(e)}")
            raise
    
    def _reproject_boundary_to_raster_crs(self, raster_crs: CRS):
        """
        Reproject boundary geometry to match raster CRS if needed.
        
        Parameters
        ----------
        raster_crs : CRS
            The CRS of the raster to match
            
        Returns
        -------
        shapely.geometry
            Boundary geometry in raster CRS
        """
        if not self.boundary_geom or not self.boundary_crs:
            return self.boundary_geom
            
        if self.boundary_crs == raster_crs:
            logger.info("Boundary and raster CRS match, no reprojection needed")
            return self.boundary_geom
            
        logger.info(f"Reprojecting boundary from {self.boundary_crs} to {raster_crs}")
        
        try:
            # Use shapely's __geo_interface__ to get proper GeoJSON representation
            # This handles complex geometries like MultiPolygon correctly
            geom_dict = self.boundary_geom.__geo_interface__
            
            # Use rasterio's transform_geom for reprojection
            reprojected_geom_dict = transform_geom(
                self.boundary_crs, 
                raster_crs, 
                geom_dict
            )
            
            # Convert back to shapely geometry
            reprojected_geom = shape(reprojected_geom_dict)
            
            logger.info(f"Successfully reprojected boundary geometry from {self.boundary_crs.to_string()} to {raster_crs.to_string()}")
            return reprojected_geom
            
        except Exception as e:
            logger.error(f"Failed to reproject boundary geometry: {str(e)}")
            logger.warning("Using original boundary geometry (may cause incorrect masking)")
            return self.boundary_geom
    
    def get_projection_info(self, raster_path: str) -> dict:
        """
        Get projection information for debugging purposes.
        
        Parameters
        ----------
        raster_path : str
            Path to raster file
            
        Returns
        -------
        dict
            Dictionary with projection information
        """
        info = {}
        
        try:
            with rasterio.open(raster_path) as src:
                info['raster_crs'] = src.crs
                info['raster_crs_string'] = src.crs.to_string() if src.crs else 'Unknown'
                info['raster_bounds'] = src.bounds
                
        except Exception as e:
            info['raster_error'] = str(e)
        
        if self.boundary_crs:
            info['boundary_crs'] = self.boundary_crs
            info['boundary_crs_string'] = self.boundary_crs.to_string()
        else:
            info['boundary_crs'] = None
            info['boundary_crs_string'] = 'No boundary loaded'
            
        return info
    
    def process_raster(self, input_path: str, output_path: str, collection_id: str) -> bool:
        """
        Process a single raster with all required transformations.
        
        Parameters
        ----------
        input_path : str
            Path to input raster file
        output_path : str
            Path for output processed raster
        collection_id : str
            Collection ID for pixel label conversion
            
        Returns
        -------
        bool
            True if processing succeeded, False otherwise
        """
        try:
            logger.info(f"Processing raster: {input_path}")
            
            with rasterio.open(input_path) as src:
                logger.info(f"Input raster info: {src.width}x{src.height}, CRS: {src.crs}")
                logger.info(f"Raster bounds: {src.bounds}")
                
                # Read the data
                data = src.read(1)
                profile = src.profile.copy()
                
                # Step 1: Apply boundary mask if provided
                if self.boundary_geom:
                    logger.info("Applying boundary mask...")
                    data = self._apply_boundary_mask(data, src)
                
                # Step 2: Convert pixels to forest/non-forest labels
                if collection_id not in ["northern_choco_test_2025_06_20_2022_merged_composite"]:
                    logger.info("Converting pixels to forest/non-forest labels...")
                    data = self._convert_to_forest_labels(data, collection_id)  
                
                    # Step 3: Set missing data consistently to 255
                    logger.info("Standardizing missing data values...")
                    data = self._standardize_missing_data(data)
                
                # Step 4: Update profile for COG output
                profile.update({
                    'driver': 'GTiff',
                    'compress': 'lzw',
                    'tiled': True,
                    'blockxsize': 512,
                    'blockysize': 512,
                    'nodata': 255,
                    'dtype': 'int16'  # Use int16 to accommodate 255, 0, 1
                })
                
                # Write temporary file first
                temp_path = output_path + '.tmp'
                with rasterio.open(temp_path, 'w', **profile) as dst:
                    dst.write(data, 1)
                
                # Step 5: Convert to COG with overviews
                logger.info("Converting to Cloud Optimized GeoTIFF with overviews...")
                self._create_optimized_raster_with_overviews(temp_path, output_path)
                
                # Clean up temporary file
                Path(temp_path).unlink()
                
                logger.info(f"Successfully processed raster: {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to process raster {input_path}: {str(e)}")
            return False
    
    def _apply_boundary_mask(self, data: np.ndarray, src: rasterio.DatasetReader) -> np.ndarray:
        """Apply boundary mask to set values outside bounds to missing data"""
        try:
            # Reproject boundary geometry to match raster CRS
            boundary_in_raster_crs = self._reproject_boundary_to_raster_crs(src.crs)
            
            if boundary_in_raster_crs is None:
                logger.warning("No boundary geometry available for masking")
                return data
                
            # Create a mask where True means outside the boundary
            out_mask = geometry_mask(
                [boundary_in_raster_crs],
                transform=src.transform,
                invert=False,  # False means inside is False, outside is True
                out_shape=data.shape
            )
            
            # Set values outside boundary to nodata
            data_masked = data.copy()
            data_masked[out_mask] = 255
            
            masked_count = np.sum(out_mask)
            total_pixels = data.size
            masked_percentage = (masked_count / total_pixels) * 100
            
            logger.info(f"Masked {masked_count:,} pixels outside boundary ({masked_percentage:.1f}% of total)")
            
            return data_masked
            
        except Exception as e:
            logger.error(f"Failed to apply boundary mask: {str(e)}")
            raise
    
    def _convert_to_forest_labels(self, data: np.ndarray, collection_id: str) -> np.ndarray:
        """Convert pixel values to standardized forest (1) / non-forest (0) labels"""
        try:
            # Preserve boundary mask values (255) before processing
            boundary_mask = (data == 255)
            
            # Use the existing pixels_to_labels function but convert to numeric
            labels = pixels_to_labels(collection_id, data)
            
            # Convert string labels to numeric
            numeric_data = np.full_like(data, 255, dtype=np.int16)
            forest_mask = (labels == "Forest")
            non_forest_mask = (labels == "Non-Forest")
            
            numeric_data[forest_mask] = 1
            numeric_data[non_forest_mask] = 0
            
            # Restore boundary mask values (ensure they stay 255)
            numeric_data[boundary_mask] = 255
            
            forest_count = np.sum(forest_mask)
            non_forest_count = np.sum(non_forest_mask)
            boundary_count = np.sum(boundary_mask)
            unknown_count = np.sum(~(forest_mask | non_forest_mask | boundary_mask))
            
            logger.info(f"Converted labels - Forest: {forest_count}, Non-Forest: {non_forest_count}, Boundary masked: {boundary_count}, Unknown: {unknown_count}")
            
            return numeric_data
            
        except Exception as e:
            logger.error(f"Failed to convert pixel labels: {str(e)}")
            raise
    
    def _standardize_missing_data(self, data: np.ndarray) -> np.ndarray:
        """Ensure all missing data values are consistently 255"""
        # This step is mostly handled in the conversion step above
        # but we can do a final check here
        missing_count = np.sum(data == 255)
        logger.info(f"Standardized missing data: {missing_count} pixels set to 255")
        return data
    
    def _create_optimized_raster_with_overviews(self, input_path: str, output_path: str):
        """Create optimized raster with overviews using GDAL tools"""
        try:
            # Create optimized raster using gdal_translate
            cmd = [
                "gdal_translate",
                "-co", "COMPRESS=LZW",
                "-co", "TILED=YES",
                "-co", "BLOCKXSIZE=512",
                "-co", "BLOCKYSIZE=512",
                str(input_path),
                str(output_path)
            ]
            
            logger.info(f"Creating optimized raster: {output_path}")
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Add overviews using gdaladdo
            overview_levels = [2, 4, 8, 16, 32, 64]
            cmd = ["gdaladdo", "-r", "nearest", str(output_path)] + [str(level) for level in overview_levels]
            
            logger.info(f"Adding overviews with levels {overview_levels}")
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            logger.info(f"Created optimized raster with overviews: {output_path}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create optimized raster: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Failed to create optimized raster: {str(e)}")
            raise

class ForestCoverProcessor:
    """Main class for processing forest cover datasets"""
    
    def __init__(self, boundary_geojson_path: Optional[str] = None, dry_run: bool = False):
        """
        Initialize the forest cover processor.
        
        Parameters
        ----------
        boundary_geojson_path : str, optional
            Path to GeoJSON file for boundary masking
        dry_run : bool, optional
            If True, only simulate operations without making changes
        """
        self.dry_run = dry_run
        self.raster_processor = RasterProcessor(boundary_geojson_path)
        self.stac_manager = STACManager(STACManagerConfig(use_remote_db=True))
        self.s3_client, self.bucket = get_s3_client()
        
        logger.info(f"Initialized ForestCoverProcessor (dry_run={dry_run})")
    
    def process_dataset(self, dataset_key: str, input_dir: str = ".") -> bool:
        """
        Process a single dataset.
        
        Parameters
        ----------
        dataset_key : str
            Key for the dataset in DATASET_CONFIGS
        input_dir : str, optional
            Directory containing input raster files
            
        Returns
        -------
        bool
            True if processing succeeded, False otherwise
        """
        if dataset_key not in DATASET_CONFIGS:
            logger.error(f"Unknown dataset: {dataset_key}")
            return False
        
        config = DATASET_CONFIGS[dataset_key]
        logger.info(f"Processing dataset: {dataset_key}")
        
        try:
            # Resolve input path
            input_path = Path(input_dir) / config["input_path"]
            if not input_path.exists():
                logger.error(f"Input file not found: {input_path}")
                return False
            
            # Create temporary output file
            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
                output_path = tmp.name
            
            try:
                # Step 1: Process the raster
                logger.info("Step 1: Processing raster...")
                if not self.raster_processor.process_raster(
                    str(input_path), output_path, config["collection_id"]
                ):
                    return False
                
                # Step 2: Backup existing STAC collection if it exists
               # logger.info("Step 2: Backing up existing STAC collection...")
                #if not self.dry_run:
                #    self._backup_existing_collection(config["collection_id"])
                
                # Step 3: Upload processed raster to S3
                logger.info("Step 3: Uploading processed raster to S3...")
                if not self.dry_run:
                    # Add year to S3 path for proper nesting (e.g., "benchmarks/HansenTreeCover/2022/file.tif")
                    remote_key = f"{config['s3_prefix']}/{config['year']}/{Path(input_path).name}"
                    upload_file(Path(output_path), remote_key)
                    logger.info(f"Uploaded to S3: {remote_key}")
                else:
                    logger.info(f"[DRY RUN] Would upload to: {config['s3_prefix']}/{config['year']}/{Path(input_path).name}")
                
                # Step 4: Delete existing STAC collection from both databases
                logger.info("Step 4: Deleting existing STAC collection from both databases...")
                if not self.dry_run:
                    # Delete from remote database (default)
                    logger.info(f"Deleting collection from remote database: {config['collection_id']}")
                    logger.info(f"Remote DB Host: {self.stac_manager.cfg.pg_env_vars['PGHOST']}")
                    self.stac_manager.delete_collection(config["collection_id"])
                    
                    # Delete from local database  
                    logger.info(f"Deleting collection from local database: {config['collection_id']}")
                    local_stac_config = STACManagerConfig(use_remote_db=False)
                    local_stac_manager = STACManager(local_stac_config)
                    logger.info(f"Local DB Host: {local_stac_manager.cfg.pg_env_vars['PGHOST']}")
                    local_stac_manager.delete_collection(config["collection_id"])
                else:
                    logger.info(f"[DRY RUN] Would delete collection from both databases: {config['collection_id']}")
                
                # Step 5: Create new STAC collection
                logger.info("Step 5: Creating new STAC collection...")
                if not self.dry_run:
                    self._create_stac_collection(config)
                else:
                    logger.info(f"[DRY RUN] Would create collection: {config['collection_id']}")
                
                logger.info(f"Successfully processed dataset: {dataset_key}")
                return True
                
            finally:
                # Clean up temporary file
                Path(output_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Failed to process dataset {dataset_key}: {str(e)}")
            return False
    
    def _backup_existing_collection(self, collection_id: str):
        """Backup existing STAC collection before deletion"""
        try:
            if self.stac_manager.verify_collection_exists(collection_id):
                backup_path = self.stac_manager.backup_collection(collection_id)
                if backup_path:
                    logger.info(f"Backed up collection {collection_id} to {backup_path}")
                else:
                    logger.warning(f"Failed to backup collection {collection_id}")
            else:
                logger.info(f"Collection {collection_id} does not exist, no backup needed")
        except Exception as e:
            logger.error(f"Error backing up collection {collection_id}: {str(e)}")
    
    def _create_stac_collection(self, config: Dict):
        """Create new STAC collection for the processed dataset in both local and remote databases"""
        try:
            # Create collection in remote database (default)
            logger.info(f"Creating STAC collection in remote database: {config['collection_id']}")
            logger.info(f"Remote DB connection details: Host={self.stac_manager.cfg.pg_env_vars['PGHOST']}, DB={self.stac_manager.cfg.pg_env_vars['PGDATABASE']}")
            
            # Test remote connection
            if self.stac_manager.test_connection():
                logger.info("✅ Remote database connection verified")
            else:
                logger.error("❌ Remote database connection failed")
                
            self.stac_manager.process_year(
                year=str(config["year"]),
                prefix_on_s3=config["s3_prefix"],
                collection_id=config["collection_id"],
                asset_key="data",
                asset_roles=["benchmark"],
                asset_title=config["asset_title"]
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
                asset_roles=["benchmark"],
                asset_title=config["asset_title"]
            )
            logger.info(f"✅ Created STAC collection in local database: {config['collection_id']}")
            
        except Exception as e:
            logger.error(f"Failed to create STAC collection {config['collection_id']}: {str(e)}")
            raise
    
    def process_all_datasets(self, input_dir: str = ".") -> Dict[str, bool]:
        """
        Process all configured datasets.
        
        Parameters
        ----------
        input_dir : str, optional
            Directory containing input raster files
            
        Returns
        -------
        dict
            Dictionary mapping dataset keys to success status
        """
        results = {}
        
        logger.info(f"Processing {len(DATASET_CONFIGS)} datasets...")
        
        for dataset_key in DATASET_CONFIGS:
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing {dataset_key}...")
                logger.info(f"{'='*60}")
                
                success = self.process_dataset(dataset_key, input_dir)
                results[dataset_key] = success
                
                if success:
                    logger.info(f"✅ Successfully processed {dataset_key}")
                else:
                    logger.error(f"❌ Failed to process {dataset_key}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing {dataset_key}: {str(e)}")
                results[dataset_key] = False
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("PROCESSING SUMMARY")
        logger.info(f"{'='*60}")
        
        successful = sum(results.values())
        total = len(results)
        
        for dataset_key, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"{dataset_key}: {status}")
        
        logger.info(f"\nOverall: {successful}/{total} datasets processed successfully")
        
        return results

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description="Re-process forest cover rasters with optimization and standardization"
    )
    parser.add_argument(
        '--dataset', 
        choices=list(DATASET_CONFIGS.keys()) + ['all'],
        default='all',
        help='Dataset to process (default: all)'
    )
    parser.add_argument(
        '--input-dir',
        default='.',
        help='Directory containing input raster files (default: current directory)'
    )
    parser.add_argument(
        '--boundary-geojson',
        help='Path to GeoJSON file for boundary masking'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate operations without making changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--show-projections',
        action='store_true',
        help='Show projection information for datasets and exit'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        processor = ForestCoverProcessor(
            boundary_geojson_path=args.boundary_geojson,
            dry_run=args.dry_run
        )
        
        # Show projection information if requested
        if args.show_projections:
            logger.info("=== PROJECTION INFORMATION ===")
            
            if args.dataset == 'all':
                datasets_to_check = list(DATASET_CONFIGS.keys())
            else:
                datasets_to_check = [args.dataset]
            
            for dataset_key in datasets_to_check:
                if dataset_key not in DATASET_CONFIGS:
                    logger.error(f"Unknown dataset: {dataset_key}")
                    continue
                    
                config = DATASET_CONFIGS[dataset_key]
                input_path = Path(args.input_dir) / config["input_path"]
                
                logger.info(f"\nDataset: {dataset_key}")
                logger.info(f"Input file: {input_path}")
                
                if input_path.exists():
                    proj_info = processor.raster_processor.get_projection_info(str(input_path))
                    logger.info(f"Raster CRS: {proj_info['raster_crs_string']}")
                    logger.info(f"Raster bounds: {proj_info['raster_bounds']}")
                    logger.info(f"Boundary CRS: {proj_info['boundary_crs_string']}")
                    
                    if 'raster_error' in proj_info:
                        logger.error(f"Error reading raster: {proj_info['raster_error']}")
                else:
                    logger.warning(f"File not found: {input_path}")
            
            sys.exit(0)
        
        # Normal processing
        if args.dataset == 'all':
            results = processor.process_all_datasets(args.input_dir)
            success = all(results.values())
        else:
            success = processor.process_dataset(args.dataset, args.input_dir)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()