from __future__ import annotations
import logging
import numpy as np
import pandas as pd
import requests
import rasterio
import rasterio.windows
from shapely.geometry import shape
from ml_pipeline.extractor import TitilerExtractor
from ml_pipeline.raster_utils import pixels_to_labels, extract_pixels_with_missing

class AOISummaryStats:
    """
    Compute % forest / non-forest + area (ha) + missing % inside an arbitrary AOI.
    Example:
        stats = AOISummaryStats("http://localhost:8083", "benchmarks-hansen-tree-cover-2022")
        df = stats.summary(aoi_geojson)
    """

    def __init__(self, base_url: str, collection: str, *, band_indexes=[1], simplified_mode=False):
        self.collection = collection
        self.band_indexes = band_indexes
        self.simplified_mode = simplified_mode
        self.extractor = TitilerExtractor(base_url.rstrip("/"), collection, band_indexes)
        # logger.info(
        #     "Initialized AOISummaryStats with base_url=%s, collection=%s, band_indexes=%s",
        #     base_url, collection, band_indexes
        # )
        print(f"Initialized AOISummaryStats with base_url={base_url}, collection={collection}, band_indexes={band_indexes}, simplified_mode={simplified_mode}")

    def summary(self, aoi_geojson: dict) -> pd.DataFrame:
        if self.simplified_mode:
            return self._simplified_summary()
        else:
            return self._standard_summary(aoi_geojson)

    def _simplified_summary(self) -> pd.DataFrame:
        """
        Simplified summary for pre-processed datasets already clipped to Western Ecuador.
        Assumes pixels are: 1=forest, 0=non-forest, 255=missing data.
        No boundary clipping needed.
        """
        print("Using simplified mode for pre-processed dataset")
        
        # Extract all pixels from the collection without any boundary constraints
        # This returns: (sample_array, missing_px, px_area_m2, actual_totals)
        px, missing_px, px_area_m2, actual_totals = self._extract_all_pixels_simplified()

        if px.size == 0 and (not actual_totals or (actual_totals['forest'] == 0 and actual_totals['nonforest'] == 0)):
            print("⚠️ No pixel data available - collection may not be loaded in TiTiler")
            # Check if this was due to fallback mode
            if missing_px == 1:  # Our fallback indicator
                raise RuntimeError(f"Collection '{self.collection}' is not available in TiTiler/PGSTAC. "
                                 f"This collection needs to be properly ingested before statistics can be calculated.")
            else:
                raise RuntimeError("Collection has no valid pixels.")

        # Use actual totals from full dataset extraction instead of sample array
        if actual_totals:
            forest_px = actual_totals['forest']
            nonforest_px = actual_totals['nonforest']
            missing_px_actual = actual_totals['missing']
            print(f"✅ Using actual totals from full dataset: Forest={forest_px:,}, Non-Forest={nonforest_px:,}, Missing={missing_px_actual:,}")
        else:
            # Fallback to sample array if actual totals not available
            forest_px = np.sum(px == 1)
            nonforest_px = np.sum(px == 0) 
            missing_px_actual = np.sum(px == 255)
            print(f"⚠️ Using sample array counts: Forest={forest_px}, Non-Forest={nonforest_px}, Missing={missing_px_actual}")
        
        unknown_px = 0  # No unknown pixels in simplified mode

        if px_area_m2 is None:
            raise RuntimeError("Could not determine pixel area.")
        m2_to_ha = px_area_m2 / 10_000

        # For percentage calculations, exclude missing pixels
        valid_px = forest_px + nonforest_px
        
        # Use the actual missing pixels from data, not the fallback indicator
        final_missing_px = missing_px_actual if actual_totals or px.size > 0 else missing_px
        
        data = {
            "forest_px": forest_px,
            "nonforest_px": nonforest_px,
            "unknown_px": unknown_px,
            "missing_px": final_missing_px,
            "pct_forest": forest_px / valid_px if valid_px else 0,
            "pct_missing": final_missing_px / (valid_px + final_missing_px) if (valid_px + final_missing_px) else 0,
            "forest_ha": forest_px * m2_to_ha,
            "nonforest_ha": nonforest_px * m2_to_ha,
            "unknown_ha": unknown_px * m2_to_ha,
        }
        
        print(f"Final pixel counts — Forest: {forest_px:,}, Non-Forest: {nonforest_px:,}, Missing: {final_missing_px:,}")
        summary_df = pd.DataFrame([data])
        print("Computed simplified summary statistics")
        return summary_df

    def _standard_summary(self, aoi_geojson: dict) -> pd.DataFrame:
        """Standard summary computation using boundary clipping."""
        geom = shape(aoi_geojson["geometry"])   # keeps CRS WGS84
        print(f"Starting standard summary computation for AOI with bounds: {geom.bounds}")
        px, missing_px, px_area_m2 = extract_pixels_with_missing(
            self.extractor, geom, self.band_indexes
        )

        if px.size == 0:
            raise RuntimeError("AOI has no valid pixels in this collection.")

        logging.info("Converting pixels to labels assuming they are already 0/1 encoded...")
        labels = pixels_to_labels("already-processed", px.squeeze())
        forest_px = (labels == "Forest").sum()
        nonforest_px = (labels == "Non-Forest").sum()
        unknown_px = (labels == "Unknown").sum()

        if px_area_m2 is None:        # defensive; should never happen
            raise RuntimeError("Could not determine pixel area.")
        m2_to_ha = px_area_m2 / 10_000

        # For percentage calculations, exclude unknown pixels to maintain consistency
        valid_px = forest_px + nonforest_px
        
        data = {
            "forest_px": forest_px,
            "nonforest_px": nonforest_px,
            "unknown_px": unknown_px,
            "missing_px": missing_px,
            "pct_forest": forest_px / valid_px if valid_px else 0,
            "pct_missing": missing_px / (valid_px + missing_px) if (valid_px + missing_px) else 0,
            "forest_ha": forest_px * m2_to_ha,
            "nonforest_ha": nonforest_px * m2_to_ha,
            "unknown_ha": unknown_px * m2_to_ha,
        }
        
        print(f"Extracted {px.size} valid pixels and {missing_px} pixels with missing data")
        print(f"Pixel classification counts — Forest: {forest_px}, Non-Forest: {nonforest_px}, Unknown: {unknown_px}")
        summary_df = pd.DataFrame([data])
        print("Computed summary statistics:")
        return summary_df

    def _extract_all_pixels_simplified(self):
        """
        Extract all pixels from the collection without boundary constraints.
        For pre-processed datasets that are already clipped to the desired region.
        Uses simple TiTiler API calls to avoid database connection issues.
        """
        try:
            print(f"🔍 Starting simplified pixel extraction for collection: {self.collection}")
            
            # Use simpler approach - get COGs for western Ecuador bbox only
            # This avoids database connection issues and is more targeted
            ecuador_bbox = "-81.5,-5.5,-75.0,1.5"  # Western Ecuador approximate bounds
            
            print(f"📊 Getting COGs for Western Ecuador bbox: {ecuador_bbox}")
            
            # Use the extractor's direct bbox method to avoid database connection
            import requests
            try:
                response = requests.get(
                    f"{self.extractor.base_url}/collections/{self.collection}/bbox/{ecuador_bbox}/assets",
                    headers={"accept": "application/json"},
                    timeout=60
                )
                response.raise_for_status()
                cog_data = response.json()
                cog_urls = [item["assets"]["data"]["href"] for item in cog_data if "assets" in item and "data" in item["assets"]]
                
            except Exception as api_error:
                print(f"⚠️ Direct API call failed: {str(api_error)}")
                print("🔄 Falling back to extractor method...")
                cog_urls = list(self.extractor.get_all_cog_urls(self.collection, bbox=ecuador_bbox))
            
            print(f"📊 Found {len(cog_urls)} COGs in Western Ecuador")
            
            if not cog_urls:
                raise RuntimeError(f"No COGs found for collection {self.collection} in Western Ecuador")

            total_forest_px = 0
            total_nonforest_px = 0
            total_missing_px = 0
            px_area_m2 = None
            processed_cogs = 0
            
            # Process all COGs but with error handling
            print(f"📊 Processing all {len(cog_urls)} COGs for accurate statistics")
            
            for i, cog_url in enumerate(cog_urls):
                try:
                    if i % 10 == 0:  # Progress every 10 COGs
                        print(f"Processing COG {i+1}/{len(cog_urls)}")
                    
                    # Read the raster data directly
                    with rasterio.open(cog_url) as src:
                        # Get pixel area from first COG
                        if px_area_m2 is None:
                            # Calculate pixel area correctly from transform and CRS
                            transform = src.transform
                            crs = src.crs
                            bounds = src.bounds
                            width = src.width
                            height = src.height
                            
                            print(f"🗺️  CRS: {crs}")
                            print(f"📏 Raster size: {width} x {height} pixels")
                            print(f"🌍 Bounds: {bounds}")
                            print(f"📐 Transform: {transform}")
                            
                            # Method 1: Try transform values
                            pixel_width = abs(transform.a)   # pixel width
                            pixel_height = abs(transform.e)  # pixel height  
                            print(f"📏 Transform pixel size: {pixel_width:.10f} x {pixel_height:.10f}")
                            
                            # Method 2: Calculate from bounds and dimensions
                            bounds_width = bounds.right - bounds.left
                            bounds_height = bounds.top - bounds.bottom
                            calc_pixel_width = bounds_width / width
                            calc_pixel_height = bounds_height / height
                            print(f"📏 Calculated pixel size: {calc_pixel_width:.10f} x {calc_pixel_height:.10f}")
                            
                            # Use calculated values if transform gives zeros
                            if pixel_width == 0 or pixel_height == 0:
                                pixel_width = calc_pixel_width
                                pixel_height = calc_pixel_height
                                print("⚠️ Transform values were zero, using calculated values")
                            
                            # If CRS is in degrees (like EPSG:4326), convert to meters
                            if crs and ('4326' in str(crs) or 'WGS84' in str(crs).upper() or crs.is_geographic):
                                # Convert from degrees to meters at equator (approximate)
                                # 1 degree ≈ 111,320 meters at equator
                                pixel_width_m = abs(pixel_width) * 111320
                                pixel_height_m = abs(pixel_height) * 111320
                                px_area_m2 = pixel_width_m * pixel_height_m
                                print(f"✓ Geographic CRS detected, converted to meters")
                                print(f"✓ Pixel resolution: {pixel_width_m:.1f}m x {pixel_height_m:.1f}m = {px_area_m2:.1f} m²")
                            else:
                                # CRS is already in meters (like UTM, Web Mercator)
                                px_area_m2 = abs(pixel_width) * abs(pixel_height)
                                print(f"✓ Projected CRS detected (already in meters)")
                                print(f"✓ Pixel resolution: {abs(pixel_width):.1f}m x {abs(pixel_height):.1f}m = {px_area_m2:.1f} m²")
                            
                            # Sanity check - if still zero or unreasonable, use defaults based on dataset
                            if px_area_m2 <= 0 or px_area_m2 > 1000000:  # > 1km² pixels seems unreasonable
                                if 'hansen' in self.collection.lower():
                                    px_area_m2 = 30 * 30  # Hansen is ~30m
                                elif 'mapbiomes' in self.collection.lower():
                                    px_area_m2 = 30 * 30  # MapBiomas is ~30m
                                elif 'esa' in self.collection.lower():
                                    px_area_m2 = 10 * 10  # ESA WorldCover is 10m
                                elif 'jrc' in self.collection.lower():
                                    px_area_m2 = 30 * 30  # JRC is ~30m
                                elif 'palsar' in self.collection.lower():
                                    px_area_m2 = 25 * 25  # PALSAR is ~25m
                                elif 'wri' in self.collection.lower():
                                    px_area_m2 = 30 * 30  # WRI is ~30m
                                else:
                                    px_area_m2 = 30 * 30  # Default to 30m
                                print(f"⚠️ Pixel area calculation failed, using dataset default: {px_area_m2} m²")
                        
                        # Check raster size before attempting to read
                        total_pixels = src.width * src.height
                        size_gb = (total_pixels * 1) / (1024**3)  # Rough estimate for 1 byte per pixel
                        print(f"  COG size: {total_pixels:,} pixels ({size_gb:.2f} GB estimated)")
                        
                        # For large rasters, use windowed reading to count ALL pixels
                        if total_pixels > 100_000_000:  # 100M+ pixels - use windowed reading
                            print(f"  ⚠️ Large raster detected ({total_pixels:,} pixels), using windowed reading...")
                            
                            # Process in chunks to avoid memory issues
                            forest_count = 0
                            nonforest_count = 0
                            missing_count = 0
                            
                            # Read in 1000x1000 pixel windows
                            window_size = 1000
                            for row in range(0, src.height, window_size):
                                for col in range(0, src.width, window_size):
                                    window = rasterio.windows.Window(
                                        col, row, 
                                        min(window_size, src.width - col),
                                        min(window_size, src.height - row)
                                    )
                                    
                                    try:
                                        chunk_data = src.read(1, window=window)
                                        forest_count += np.sum(chunk_data == 1)
                                        nonforest_count += np.sum(chunk_data == 0)
                                        missing_count += np.sum(chunk_data == 255)
                                        
                                        # Progress indicator for large rasters - every 10%
                                        progress = (row / src.height) * 100
                                        if int(progress) % 10 == 0 and int(progress) > 0:
                                            total_chunks = (src.height + window_size - 1) // window_size
                                            chunks_processed = (row // window_size) + 1
                                            print(f"    Progress: {progress:.0f}% ({chunks_processed}/{total_chunks} chunks)")
                                            
                                    except Exception as chunk_error:
                                        print(f"    ⚠️ Error reading chunk at ({row}, {col}): {str(chunk_error)}")
                                        continue
                        else:
                            # Read the data for band 1 (first band) - normal size
                            band_data = src.read(1)
                            
                            # Count pixels by value
                            forest_count = np.sum(band_data == 1)
                            nonforest_count = np.sum(band_data == 0)
                            missing_count = np.sum(band_data == 255)
                        
                        total_forest_px += forest_count
                        total_nonforest_px += nonforest_count
                        total_missing_px += missing_count
                        processed_cogs += 1
                        
                        if i < 5 or i % 50 == 0:  # Show details for first few and every 50th
                            print(f"  COG {i+1}: Forest={forest_count:,}, Non-Forest={nonforest_count:,}, Missing={missing_count:,}")
                        
                except Exception as cog_error:
                    print(f"⚠️ Error processing COG {i+1}: {str(cog_error)}")
                    continue
            
            print(f"✅ Successfully processed {processed_cogs}/{len(cog_urls)} COGs")
            
            # Create a small representative array for compatibility with existing code
            if total_forest_px > 0 or total_nonforest_px > 0:
                # Create a representative sample (limit to reasonable size for memory)
                sample_size = min(10000, total_forest_px + total_nonforest_px)
                if total_forest_px + total_nonforest_px > 0:
                    forest_ratio = total_forest_px / (total_forest_px + total_nonforest_px)
                    sample_forest = int(sample_size * forest_ratio)
                    sample_nonforest = sample_size - sample_forest
                    
                    all_pixels = np.concatenate([
                        np.zeros(sample_nonforest, dtype=np.uint8),  # 0 = non-forest
                        np.ones(sample_forest, dtype=np.uint8)       # 1 = forest
                    ])
                else:
                    all_pixels = np.array([], dtype=np.uint8)
            else:
                all_pixels = np.array([], dtype=np.uint8)
            
            if px_area_m2 is None:
                px_area_m2 = 30 * 30  # Default 30m resolution
                print(f"⚠️ Using default pixel area: {px_area_m2} m²")
            
            total_ha = (total_forest_px + total_nonforest_px) * px_area_m2 / 10000
            print(f"✅ Final pixel counts — Forest: {total_forest_px:,}, Non-Forest: {total_nonforest_px:,}, Missing: {total_missing_px:,}")
            print(f"✅ Total area: {total_ha:,.1f} hectares")
            
            # Return actual totals as fourth value for use in summary calculations
            actual_totals = {
                'forest': total_forest_px,
                'nonforest': total_nonforest_px,
                'missing': total_missing_px
            }
            
            return all_pixels, total_missing_px, px_area_m2, actual_totals
                
        except Exception as e:
            print(f"❌ Error in simplified pixel extraction: {str(e)}")
            raise RuntimeError(f"Failed to extract pixels from collection {self.collection}: {str(e)}")
