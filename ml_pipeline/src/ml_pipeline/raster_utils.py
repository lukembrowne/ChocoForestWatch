# NEW FILE: ml_pipeline/raster_utils.py
from __future__ import annotations
import numpy as np
from shapely.geometry import mapping
import rasterio
from rasterio.mask import mask
from pyproj import Geod
from shapely.ops import transform
from pyproj import Transformer

_GEOD = Geod(ellps="WGS84")  # reused for geodesic area calculations

def pixels_to_labels(collection: str, pixels: np.ndarray) -> np.ndarray:
    """Dataset-specific mapping ➜ 'Forest' / 'Non-Forest' / 'Unknown'"""
    if "nicfi" in collection:
        out = np.where(pixels == 0, "Non-Forest", np.where(pixels == 1, "Forest", "Unknown"))
    elif collection == "benchmarks-hansen-tree-cover-2022":
        out = np.where(pixels >= 90, "Forest", "Non-Forest")

    elif collection == "benchmarks-mapbiomes-2022":
        out = np.where(
                np.logical_or.reduce([
                    pixels == 3,
                    pixels == 4,
                    pixels == 5,
                    pixels == 6,
                ]),
                "Forest",
                "Non-Forest",
            )

    elif collection == "benchmarks-esa-landcover-2020":
        out = np.where(pixels == 10, "Forest", "Non-Forest")

    elif collection == "benchmarks-jrc-forestcover-2020":
        out = np.where(pixels == 1, "Forest", "Non-Forest")
 
    elif collection == "benchmarks-palsar-2020":
        out = np.where(
                np.logical_or.reduce([
                    pixels == 1,
                    pixels == 2,
                ]),
                "Forest",
                "Non-Forest",
            )

    elif collection == "benchmarks-wri-treecover-2020":
        out = np.where(pixels >= 90, "Forest", "Non-Forest")

    else:
        raise ValueError(f"Unknown collection: {collection}")

    return out

def extract_pixels_with_missing(extractor, geom, band_indexes):
    """
    Extract pixels that fall inside *geom* (WGS-84) from every COG returned
    by *extractor*.  Also counts nodata pixels.

    Returns
    -------
    pixels      : (N, n_bands) ndarray – valid pixels only
    missing_px  : int           – total nodata pixels inside the AOI
    px_area_m2  : float | None  – square metres per pixel (None if no pixels)
    """
    pixels, missing_px = [], 0
    px_area_m2 = None

    try:
        print(f"🔍 Starting pixel extraction with band_indexes: {band_indexes}")
        print(f"📐 Input geometry type: {geom.geom_type}, bounds: {geom.bounds}")

        # Pre-transform geometry to both coordinate systems
        # Assume input geometry is in WGS84 (EPSG:4326)
        geom_wgs84 = geom
        
        # Transform to Web Mercator (EPSG:3857)
        print("🗺️  Transforming geometry to Web Mercator...")
        transformer_to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        geom_3857 = transform(transformer_to_3857.transform, geom)
        print(f"✓ Web Mercator bounds: {geom_3857.bounds}")

        # Get COG URLs for the given geometry
        print(f"🔍 Fetching COG URLs for geometry bounds: {geom.bounds}")
        cogs = extractor.get_cog_urls(geom)
        print(f"📦 Found {len(cogs)} COGs for the given geometry")
        
        if not cogs:
            print("⚠️  No COGs found for this geometry")
            return np.empty((0, len(band_indexes))), missing_px, px_area_m2

        for i, cog in enumerate(cogs):
            print(f"\n📊 Processing COG {i+1}/{len(cogs)}: {cog}")
            
            try:
                with rasterio.open(cog) as src:
                    print(f"  📋 COG info: CRS={src.crs}, shape={src.shape}, dtype={src.dtypes[0]}")
                    print(f"  📏 Resolution: {src.res}, bounds: {src.bounds}")
                    
                    # Choose appropriate geometry based on raster CRS
                    mask_geom = geom_wgs84 if src.crs.to_epsg() == 4326 else geom_3857
                    print(f"  🎯 Using {'WGS84' if src.crs.to_epsg() == 4326 else 'Web Mercator'} geometry for masking")
                    
                    # Check if raster is extremely large and might cause memory issues
                    total_pixels = src.width * src.height
                    if total_pixels > 100_000_000:  # 100M pixels
                        print(f"  ⚠️  Large raster detected - this may take several minutes or cause memory issues")
                    
                    print(f"  ✂️  Applying rasterio mask...")
                    try:
                        # Add explicit memory and error handling for the mask operation
                        import gc
                        gc.collect()  # Free up memory before large operation
                        
                        out, transform_out = mask(
                            src,
                            [mapping(mask_geom)],
                            crop=True,
                            indexes=band_indexes,
                            all_touched=True,
                            nodata=src.nodata
                        )
                        print(f"  ✓ Mask result shape: {out.shape}, dtype: {out.dtype}")
                        
                        # Check if mask result is reasonable
                        if out.size == 0:
                            print(f"  ⚠️  Mask returned empty array - geometry may not intersect raster")
                            continue
                        elif out.size > 50_000_000:  # 50M pixels in result
                            print(f"  ⚠️  Large mask result ({out.size:,} pixels) - processing may be slow")
                            
                    except MemoryError as e:
                        print(f"  ❌ Memory error during masking: {str(e)}")
                        print(f"  💡 Raster too large for available memory - skipping this COG")
                        continue
                    except Exception as e:
                        print(f"  ❌ Error during masking operation: {str(e)}")
                        print(f"  💥 Mask error type: {type(e).__name__}")
                        raise

                    # ------------------------------------------------------------------
                    # Build a 2-D nodata mask (rows, cols)
                    # ------------------------------------------------------------------
                    nodata = src.nodata
                    print(f"  🚫 Nodata value: {nodata}")
                    
                    if nodata is not None and not np.isnan(nodata):
                        if out.ndim == 3:                         # multi-band
                            nodata_mask = np.all(out == nodata, axis=0)
                        else:                                    # single band
                            nodata_mask = out == nodata
                    else:
                        # no nodata metadata – treat everything as valid
                        nodata_mask = np.zeros(out.shape[-2:], dtype=bool)

                    cog_missing = int(nodata_mask.sum())
                    missing_px += cog_missing
                    print(f"  📊 Missing pixels in this COG: {cog_missing}")

                    # ------------------------------------------------------------------
                    # Move bands to the last axis so mask lines up with first two dims
                    # ------------------------------------------------------------------
                    if out.ndim == 3:                            # (bands, rows, cols) ➜ (rows, cols, bands)
                        arr = np.moveaxis(out, 0, -1)
                    else:                                        # (rows, cols) ➜ add a bands axis
                        arr = out[..., np.newaxis]

                    # Apply mask & flatten
                    valid_pixels_before = arr.size
                    arr = arr[~nodata_mask]                      # (n_valid_px, bands)
                    valid_pixels_after = arr.size
                    
                    print(f"  📈 Valid pixels: {valid_pixels_after} (from {valid_pixels_before} total)")

                    if arr.size:
                        if px_area_m2 is None:
                            print("  📐 Calculating pixel area...")
                            resx, resy = src.res

                            if src.crs and src.crs.is_geographic:
                                # CRS units are degrees – compute geodesic area of one pixel at tile centre
                                print("  🌍 Geographic CRS - calculating geodesic area")
                                bounds = src.bounds
                                center_lon = (bounds.left + bounds.right) / 2.0
                                center_lat = (bounds.top + bounds.bottom) / 2.0

                                lon_left = center_lon - resx / 2.0
                                lon_right = center_lon + resx / 2.0
                                lat_bottom = center_lat - resy / 2.0
                                lat_top = center_lat + resy / 2.0

                                lons = [lon_left, lon_right, lon_right, lon_left, lon_left]
                                lats = [lat_bottom, lat_bottom, lat_top, lat_top, lat_bottom]

                                # polygon_area_perimeter returns negative area when ring is CW; take abs
                                area_m2, _ = _GEOD.polygon_area_perimeter(lons, lats)
                                px_area_m2 = abs(area_m2)
                                print(f"    ✓ Pixel area: {px_area_m2:.2f} m²")
                            else:
                                # CRS units are metres – area = resx * resy
                                print("  📏 Projected CRS - using resolution for area")
                                px_area_m2 = abs(resx * resy)
                                print(f"    ✓ Pixel area: {px_area_m2:.2f} m²")
                        
                        reshaped_arr = arr.reshape(-1, len(band_indexes))
                        pixels.append(reshaped_arr)
                        print(f"  ✅ Added {reshaped_arr.shape[0]} pixels to collection")
                    else:
                        print("  ⚠️  No valid pixels in this COG")
                        
            except Exception as e:
                print(f"  ❌ Error processing COG {cog}: {str(e)}")
                print(f"  💥 Error type: {type(e).__name__}")
                # Continue with next COG instead of failing entirely
                continue

        print(f"\n📊 Final summary:")
        print(f"  Total COGs processed: {len(cogs)}")
        print(f"  Total missing pixels: {missing_px}")
        print(f"  Pixel collections: {len(pixels)}")
        
        if not pixels:
            print("⚠️  No valid pixels found in any COG")
            return np.empty((0, len(band_indexes))), missing_px, px_area_m2

        final_pixels = np.vstack(pixels)
        print(f"✅ Successfully extracted {final_pixels.shape[0]} total pixels")
        return final_pixels, missing_px, px_area_m2
        
    except Exception as e:
        print(f"❌ Critical error in extract_pixels_with_missing: {str(e)}")
        print(f"💥 Error type: {type(e).__name__}")
        raise