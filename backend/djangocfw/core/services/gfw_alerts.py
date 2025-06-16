"""
Global Forest Watch (GFW) Deforestation Alerts Service

This service fetches and processes GFW deforestation alerts for the Ecuador boundary.
It filters alerts for the year 2022 and returns them as GeoJSON features.
"""

import os
import json
import tempfile
import requests
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

import rasterio
from rasterio.mask import mask
from rasterio import features
from shapely.geometry import shape, mapping, box
from shapely.ops import transform
from pyproj import Transformer

from django.conf import settings
from loguru import logger


class GFWAlertsService:
    """Service for fetching and processing Global Forest Watch deforestation alerts."""
    
    def __init__(self):
        self.api_key = "2d60cd88-8348-4c0f-a6d5-bd9adb585a8c"
        self.base_url = "https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff"
        
        # GFW tiles that cover Ecuador
        self.gfw_tiles = [
            "10N_080W",
            "00N_080W", 
            "00N_090W",
            "10N_090W"
        ]
        
        # Ecuador boundary path from environment variable (same as used in views.py)
        self.ecuador_boundary_path = os.environ.get("BOUNDARY_GEOJSON_PATH")
        
        # Cache directory for GFW tiles
        self.cache_dir = os.path.join(settings.MEDIA_ROOT, 'gfw_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def load_ecuador_boundary(self):
        """Load Ecuador boundary from GeoJSON file or URL (same pattern as views.py)."""
        try:
            # Handle both HTTP URLs and file paths (same logic as views.py)
            if self.ecuador_boundary_path.startswith("http://") or self.ecuador_boundary_path.startswith("https://"):
                resp = requests.get(self.ecuador_boundary_path, timeout=30)
                resp.raise_for_status()
                boundary_geojson = resp.json()
            else:
                with open(self.ecuador_boundary_path, 'r', encoding='utf-8') as f:
                    boundary_geojson = json.load(f)
            
            # Extract geometry from FeatureCollection and create a single shape
            geometries = []
            for feature in boundary_geojson['features']:
                geom = shape(feature['geometry'])
                geometries.append(geom)
            
            # Union all geometries into a single shape
            from shapely.ops import unary_union
            boundary_shape = unary_union(geometries)
            
            logger.info(f"Loaded Ecuador boundary with {len(geometries)} features from {self.ecuador_boundary_path}")
            return boundary_shape
            
        except Exception as e:
            logger.error(f"Failed to load Ecuador boundary from {self.ecuador_boundary_path}: {str(e)}")
            raise
    
    def decode_gfw_date(self, value):
        """Decode GFW alert date and confidence from pixel value."""
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
    
    def download_gfw_tile(self, tile_id):
        """Download a GFW tile if not already cached."""
        # Use a permanent cache filename for historical data (no date expiration)
        cache_filename = f"gfw_{tile_id}_historical.tif"
        cache_path = os.path.join(self.cache_dir, cache_filename)
        
        # Return cached file if it exists (no expiration for historical data)
        if os.path.exists(cache_path):
            logger.info(f"Using cached GFW tile: {cache_filename}")
            return cache_path
        
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
            return cache_path
            
        except Exception as e:
            logger.error(f"Failed to download GFW tile {tile_id}: {str(e)}")
            raise
    
    def get_2022_alerts(self):
        """Get all GFW deforestation alerts for 2022 within Ecuador boundary."""
        try:
            # Load Ecuador boundary
            boundary_shape = self.load_ecuador_boundary()
            
            # Define 2022 date range
            start_date = datetime(2022, 1, 1)
            end_date = datetime(2022, 12, 31)
            
            all_features = []
            
            # Process each GFW tile
            for tile_id in self.gfw_tiles:
                logger.info(f"Processing GFW tile {tile_id}")
                
                try:
                    # Download tile
                    tile_path = self.download_gfw_tile(tile_id)
                    
                    # Process tile for 2022 alerts
                    features = self._process_tile_for_alerts(
                        tile_path, boundary_shape, start_date, end_date
                    )
                    
                    all_features.extend(features)
                    logger.info(f"Found {len(features)} alerts in tile {tile_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing tile {tile_id}: {str(e)}")
                    continue
            
            logger.info(f"Total GFW alerts found for 2022: {len(all_features)}")
            
            # Return as GeoJSON FeatureCollection
            return {
                "type": "FeatureCollection",
                "features": all_features,
                "metadata": {
                    "year": 2022,
                    "source": "Global Forest Watch",
                    "total_alerts": len(all_features),
                    "processed_tiles": self.gfw_tiles,
                    "boundary": "Ecuador DEM 900m contour"
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting 2022 GFW alerts: {str(e)}")
            raise
    
    def _process_tile_for_alerts(self, tile_path, boundary_shape, start_date, end_date):
        """Process a single GFW tile to extract 2022 alerts within boundary."""
        features = []
        tile_name = os.path.basename(tile_path)
        
        logger.info(f"[{tile_name}] Starting tile processing...")
        
        with rasterio.open(tile_path) as src:
            logger.info(f"[{tile_name}] Opened raster - Shape: {src.shape}, Bounds: {src.bounds}")
            
            # Check if tile intersects with boundary
            tile_bounds = box(*src.bounds)
            if not tile_bounds.intersects(boundary_shape):
                logger.info(f"[{tile_name}] Tile does not intersect with Ecuador boundary - skipping")
                return features
            
            try:
                # Clip tile to boundary
                logger.info(f"[{tile_name}] Clipping tile to Ecuador boundary...")
                clipped_data, clipped_transform = mask(src, [boundary_shape], crop=True)
                clipped_shape = clipped_data[0].shape
                total_pixels = clipped_shape[0] * clipped_shape[1]
                logger.info(f"[{tile_name}] Clipped to shape: {clipped_shape} ({total_pixels:,} pixels)")
                
                # Create alert mask for 2022
                logger.info(f"[{tile_name}] Creating alert mask for 2022...")
                alert_mask = np.zeros_like(clipped_data[0], dtype=bool)
                confidence_data = np.zeros_like(clipped_data[0], dtype=np.uint8)
                
                # Process each pixel to find 2022 alerts
                logger.info(f"[{tile_name}] Processing {total_pixels:,} pixels to find 2022 alerts...")
                processed_pixels = 0
                valid_pixels = 0
                alert_pixels = 0
                
                for idx in np.ndindex(clipped_data[0].shape):
                    processed_pixels += 1
                    
                    # Log progress every 100,000 pixels
                    if processed_pixels % 100000 == 0:
                        logger.info(f"[{tile_name}] Processed {processed_pixels:,}/{total_pixels:,} pixels "
                                   f"({processed_pixels/total_pixels*100:.1f}%) - Found {alert_pixels} alerts so far")
                    
                    value = clipped_data[0][idx]
                    if value > 0:  # Skip nodata pixels
                        valid_pixels += 1
                        alert_date, confidence = self.decode_gfw_date(value)
                        if alert_date and start_date <= alert_date <= end_date:
                            alert_mask[idx] = True
                            confidence_data[idx] = confidence
                            alert_pixels += 1
                
                logger.info(f"[{tile_name}] Pixel processing complete - Valid: {valid_pixels:,}, "
                           f"2022 Alerts: {alert_pixels:,} ({alert_pixels/total_pixels*100:.3f}%)")
                
                # Extract shapes from alert mask
                if np.any(alert_mask):
                    logger.info(f"[{tile_name}] Extracting shapes from {alert_pixels} alert pixels...")
                    shapes = features.shapes(
                        alert_mask.astype(np.uint8),
                        mask=alert_mask,
                        transform=clipped_transform
                    )
                    
                    # Convert shapes to features
                    logger.info(f"[{tile_name}] Converting shapes to feature polygons...")
                    shape_count = 0
                    small_polygons_skipped = 0
                    
                    for geom, value in shapes:
                        if value == 1:
                            shape_count += 1
                            polygon = shape(geom)
                            
                            # Calculate area in hectares (convert from m² to ha)
                            # First transform to Web Mercator for accurate area calculation
                            project = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True).transform
                            polygon_3857 = transform(project, polygon)
                            area_ha = polygon_3857.area / 10000
                            
                            # Skip very small alerts (< 0.1 ha)
                            if area_ha < 0.1:
                                small_polygons_skipped += 1
                                continue
                            
                            # Get average confidence for this alert
                            mask_indices = features.rasterize(
                                [(geom, 1)],
                                out_shape=alert_mask.shape,
                                transform=clipped_transform
                            ) == 1
                            
                            if np.any(mask_indices):
                                avg_confidence = float(np.mean(confidence_data[mask_indices]))
                            else:
                                avg_confidence = 1
                            
                            # Create feature
                            feature = {
                                "type": "Feature",
                                "geometry": mapping(polygon),  # Keep in WGS84
                                "properties": {
                                    "area_ha": round(area_ha, 2),
                                    "perimeter_m": round(polygon_3857.length, 2),
                                    "confidence": int(avg_confidence),
                                    "source": "gfw",
                                    "year": 2022,
                                    "centroid_lon": float(polygon.centroid.x),
                                    "centroid_lat": float(polygon.centroid.y)
                                }
                            }
                            
                            features.append(feature)
                    
                    logger.info(f"[{tile_name}] Shape processing complete - "
                               f"Shapes processed: {shape_count}, Small polygons skipped: {small_polygons_skipped}, "
                               f"Final features: {len(features)}")
                else:
                    logger.info(f"[{tile_name}] No alert pixels found in mask - no features to extract")
                
            except Exception as e:
                logger.error(f"[{tile_name}] Error processing tile data: {str(e)}")
                
        logger.info(f"[{tile_name}] Tile processing complete - {len(features)} features extracted")
        return features


# Global instance
gfw_service = GFWAlertsService()