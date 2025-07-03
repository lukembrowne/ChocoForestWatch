from __future__ import annotations
import logging
import numpy as np
import pandas as pd
import requests
import rasterio
import rasterio.windows
from rasterio.mask import mask
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pyproj import Transformer
import os
import json
from ml_pipeline.extractor import TitilerExtractor
from ml_pipeline.raster_utils import pixels_to_labels, extract_pixels_with_missing

class AOISummaryStats:
    """
    Compute % forest / non-forest + area (ha) + missing % inside an arbitrary AOI.
    Example:
        stats = AOISummaryStats("http://localhost:8083", "datasets-hansen-tree-cover-2022")
        df = stats.summary(aoi_geojson)
    """

    def __init__(self, base_url: str, collection: str, *, band_indexes=[1]):
        self.collection = collection
        self.band_indexes = band_indexes
        self.extractor = TitilerExtractor(base_url.rstrip("/"), collection, band_indexes)
        print(f"Initialized AOISummaryStats with base_url={base_url}, collection={collection}, band_indexes={band_indexes}")

    def summary(self, aoi_geojson: dict = None) -> pd.DataFrame:
        # Load Western Ecuador boundary if no AOI provided
        if aoi_geojson is None:
            boundary_polygon = self._load_western_ecuador_boundary()
            if boundary_polygon is None:
                raise RuntimeError("Could not load Western Ecuador boundary polygon")
        else:
            boundary_polygon = shape(aoi_geojson["geometry"])
        
        return self._extract_pixels_with_boundary_windowed(boundary_polygon)


    def _load_western_ecuador_boundary(self):
        """Load and return the Western Ecuador boundary polygon in WGS84."""
        try:
            # Try environment variable first
            boundary_path = os.environ.get("BOUNDARY_GEOJSON_PATH")
            if not boundary_path:
                # Fallback to default path in the project
                boundary_path = "/Users/luke/apps/ChocoForestWatch/ml_pipeline/notebooks/boundaries/Ecuador-DEM-900m-contour.geojson"
                print(f"⚠️ Using default boundary path: {boundary_path}")
            else:
                print(f"📂 Loading boundary from: {boundary_path}")
            
            # Load GeoJSON file
            if boundary_path.startswith(("http://", "https://")):
                resp = requests.get(boundary_path, timeout=30)
                resp.raise_for_status()
                geojson = resp.json()
            else:
                with open(boundary_path, "r", encoding="utf-8") as f:
                    geojson = json.load(f)
            
            print(f"📄 Loaded GeoJSON with {len(geojson.get('features', []))} features")
            
            # Load geometries and combine them
            geoms = []
            for feat in geojson.get("features", []):
                geom = shape(feat["geometry"])
                geoms.append(geom)
            
            # Combine geometries if multiple
            from shapely.ops import unary_union
            if len(geoms) == 1:
                boundary_polygon = geoms[0]
            else:
                boundary_polygon = unary_union(geoms)
            
            print(f"✓ Boundary geometry ready: {boundary_polygon.geom_type}")
            return boundary_polygon
            
        except Exception as e:
            print(f"❌ Failed to load boundary polygon: {str(e)}")
            return None

    def _extract_pixels_with_boundary_windowed(self, boundary_polygon):
        """
        Extract pixels within boundary using windowed reading for memory efficiency.
        """
        try:
            print(f"🔍 Starting boundary-based pixel extraction for collection: {self.collection}")
            print(f"✓ Boundary loaded: {boundary_polygon.geom_type}")
            
            # Get COGs for western Ecuador bbox
            ecuador_bbox = "-81.5,-5.5,-75.0,1.5"
            print(f"📊 Getting COGs for Western Ecuador bbox: {ecuador_bbox}")
            
            # Get COG URLs using extractor
            cog_urls = list(self.extractor.get_cog_urls(boundary_polygon))
            print(f"📊 Found {len(cog_urls)} COGs intersecting boundary")
            
            if not cog_urls:
                raise RuntimeError(f"No COGs found for collection {self.collection} in Western Ecuador")

            total_forest_px = 0
            total_nonforest_px = 0
            total_missing_px = 0
            px_area_m2 = None
            processed_cogs = 0
            
            print(f"📊 Processing {len(cog_urls)} COGs with windowed reading")
            
            for i, cog_url in enumerate(cog_urls):
                try:
                    if i % 10 == 0:
                        print(f"Processing COG {i+1}/{len(cog_urls)}")
                    
                    with rasterio.open(cog_url) as src:
                        # Calculate pixel area from first COG
                        if px_area_m2 is None:
                            px_area_m2 = self._calculate_pixel_area(src)
                        
                        # Transform boundary to match raster CRS
                        mask_geom = boundary_polygon
                        if src.crs and src.crs.to_epsg() != 4326:
                            transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
                            mask_geom = transform(transformer.transform, boundary_polygon)
                        
                        forest_count = 0
                        nonforest_count = 0
                        missing_count = 0
                        
                        # Check raster size and decide on approach
                        total_pixels = src.width * src.height
                        size_mb = (total_pixels * 1) / (1024**2)  # Rough estimate for 1 byte per pixel
                        print(f"  📏 Raster dimensions: {src.width} x {src.height} = {total_pixels:,} pixels ({size_mb:.1f} MB)")
                        
                        # Set window size
                        window_size = 10000
                        print(f"Set window size to {window_size} x {window_size} pixels")
                        
                        
                        # Calculate total windows for progress tracking
                        rows_windows = (src.height + window_size - 1) // window_size
                        cols_windows = (src.width + window_size - 1) // window_size
                        total_windows = rows_windows * cols_windows
                        processed_windows = 0
                        
                        print(f"  📊 Processing {total_windows} windows ({rows_windows} x {cols_windows})")
                        
                        # Process in windows with boundary checking per window
                        for row in range(0, src.height, window_size):
                            for col in range(0, src.width, window_size):
                                window = rasterio.windows.Window(
                                    col, row, 
                                    min(window_size, src.width - col),
                                    min(window_size, src.height - row)
                                )
                                
                                try:
                                    # Read window data
                                    window_data = src.read(1, window=window)
                                    
                                    # Create boundary mask for just this window (more memory efficient)
                                    from rasterio.features import geometry_mask
                                    window_transform = rasterio.windows.transform(window, src.transform)
                                    
                                    window_mask = geometry_mask(
                                        [mapping(mask_geom)],
                                        transform=window_transform,
                                        invert=True,  # True means inside boundary
                                        out_shape=window_data.shape
                                    )
                                    
                                    # Only count pixels inside boundary
                                    inside_boundary = window_data[window_mask]
                                    
                                    if inside_boundary.size > 0:
                                        forest_count += np.sum(inside_boundary == 1)
                                        nonforest_count += np.sum(inside_boundary == 0)
                                        missing_count += np.sum(inside_boundary == 255)
                                        
                                        # Count nodata pixels if present
                                        if src.nodata is not None:
                                            missing_count += np.sum(inside_boundary == src.nodata)
                                    
                                    processed_windows += 1
                                    
                                    # Progress reporting every 10% or every 100 windows
                                    if processed_windows % max(1, total_windows // 10) == 0 or processed_windows % 100 == 0:
                                        progress = (processed_windows / total_windows) * 100
                                        print(f"    Progress: {progress:.1f}% ({processed_windows}/{total_windows} windows)")
                                        print(f"    Current counts: Forest={forest_count:,}, Non-Forest={nonforest_count:,}, Missing={missing_count:,}")
                                        
                                except Exception as window_error:
                                    print(f"    ⚠️ Error reading window at ({row}, {col}): {str(window_error)}")
                                    processed_windows += 1
                                    continue
                        
                        total_forest_px += forest_count
                        total_nonforest_px += nonforest_count
                        total_missing_px += missing_count
                        processed_cogs += 1
                        
                        if i < 5 or i % 50 == 0:
                            print(f"  COG {i+1}: Forest={forest_count:,}, Non-Forest={nonforest_count:,}, Missing={missing_count:,}")
                        
                except Exception as cog_error:
                    print(f"⚠️ Error processing COG {i+1}: {str(cog_error)}")
                    continue
            
            print(f"✅ Successfully processed {processed_cogs}/{len(cog_urls)} COGs")
            
            if px_area_m2 is None:
                px_area_m2 = 30 * 30  # Default 30m resolution
                print(f"⚠️ Using default pixel area: {px_area_m2} m²")
            
            total_ha = (total_forest_px + total_nonforest_px) * px_area_m2 / 10000
            print(f"✅ Final pixel counts — Forest: {total_forest_px:,}, Non-Forest: {total_nonforest_px:,}, Missing: {total_missing_px:,}")
            print(f"✅ Total area: {total_ha:,.1f} hectares")
            
            # Return summary data
            return self._create_summary_dataframe(total_forest_px, total_nonforest_px, total_missing_px, px_area_m2)
                
        except Exception as e:
            print(f"❌ Error in boundary pixel extraction: {str(e)}")
            raise RuntimeError(f"Failed to extract pixels from collection {self.collection}: {str(e)}")
    
    def _calculate_pixel_area(self, src):
        """Calculate pixel area in square meters."""
        transform = src.transform
        crs = src.crs
        
        pixel_width = abs(transform.a)
        pixel_height = abs(transform.e)
        
        if crs and crs.is_geographic:
            # Convert from degrees to meters
            pixel_width_m = pixel_width * 111320
            pixel_height_m = pixel_height * 111320
            px_area_m2 = pixel_width_m * pixel_height_m
            print(f"✓ Geographic CRS: {px_area_m2:.1f} m² per pixel")
        else:
            # Already in meters
            px_area_m2 = pixel_width * pixel_height
            print(f"✓ Projected CRS: {px_area_m2:.1f} m² per pixel")
        
        # Sanity check with defaults
        if px_area_m2 <= 0 or px_area_m2 > 1000000:
            if 'hansen' in self.collection.lower():
                px_area_m2 = 30 * 30
            else:
                px_area_m2 = 30 * 30
            print(f"⚠️ Using default pixel area: {px_area_m2} m²")
        
        return px_area_m2
    
    def _create_summary_dataframe(self, forest_px, nonforest_px, missing_px, px_area_m2):
        """Create summary DataFrame with statistics."""
        m2_to_ha = px_area_m2 / 10_000
        valid_px = forest_px + nonforest_px
        
        data = {
            "forest_px": forest_px,
            "nonforest_px": nonforest_px,
            "unknown_px": 0,
            "missing_px": missing_px,
            "pct_forest": forest_px / valid_px if valid_px else 0,
            "pct_missing": missing_px / (valid_px + missing_px) if (valid_px + missing_px) else 0,
            "forest_ha": forest_px * m2_to_ha,
            "nonforest_ha": nonforest_px * m2_to_ha,
            "unknown_ha": 0,
        }
        
        print(f"Summary: {data['pct_forest']*100:.1f}% forest, {data['pct_missing']*100:.1f}% missing")
        return pd.DataFrame([data])
