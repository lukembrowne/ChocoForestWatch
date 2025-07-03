# NEW FILE: ml_pipeline/raster_utils.py
from __future__ import annotations
import numpy as np
from shapely.geometry import mapping
import rasterio
from rasterio.mask import mask
from rasterio.features import geometry_mask
from rasterio.enums import Resampling
import subprocess
from rasterio.profiles import default_gtiff_profile
from rasterio.warp import calculate_default_transform, reproject
from pyproj import Geod
from shapely.ops import transform
from pyproj import Transformer
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import tempfile
import hashlib

_GEOD = Geod(ellps="WGS84")  # reused for geodesic area calculations

def pixels_to_labels(collection: str, pixels: np.ndarray) -> np.ndarray:
    """Dataset-specific mapping ➜ 'Forest' / 'Non-Forest' / 'Unknown'"""

    if collection == "already-processed":
        # Special case for already-processed data
        out = np.where(pixels == 0, "Non-Forest", np.where(pixels == 1, "Forest", "Unknown"))
        return out

    if "nicfi" in collection:
        out = np.where(pixels == 0, "Non-Forest", np.where(pixels == 1, "Forest", "Unknown"))
    
    elif collection == "datasets-hansen-tree-cover-2022":
        out = np.where(pixels >= 90, "Forest", "Non-Forest")

    elif collection == "datasets-mapbiomes-2022":
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

    elif collection == "datasets-esa-landcover-2020":
        out = np.where(pixels == 10, "Forest", "Non-Forest")

    elif collection == "datasets-jrc-forestcover-2020":
        out = np.where(pixels == 1, "Forest", "Non-Forest")
 
    elif collection == "datasets-palsar-2020":
        out = np.where(
                np.logical_or.reduce([
                    pixels == 1,
                    pixels == 2,
                ]),
                "Forest",
                "Non-Forest",
            )

    elif collection == "datasets-wri-treecover-2020":
        out = np.where(pixels >= 90, "Forest", "Non-Forest")

    else:
        raise ValueError(f"Unknown collection: {collection}")

    return out

def extract_pixels_with_missing(extractor, geom, band_indexes, verbose=True):
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
    
    def vprint(*args, **kwargs):
        """Verbose print - only prints if verbose=True"""
        if verbose:
            print(*args, **kwargs)

    try:
        vprint(f"🔍 Starting pixel extraction with band_indexes: {band_indexes}")
        vprint(f"📐 Input geometry type: {geom.geom_type}, bounds: {geom.bounds}")

        # Pre-transform geometry to both coordinate systems
        # Assume input geometry is in WGS84 (EPSG:4326)
        geom_wgs84 = geom
        
        # Transform to Web Mercator (EPSG:3857)
        vprint("🗺️  Transforming geometry to Web Mercator...")
        transformer_to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        geom_3857 = transform(transformer_to_3857.transform, geom)
        vprint(f"✓ Web Mercator bounds: {geom_3857.bounds}")

        # Get COG URLs for the given geometry
        vprint(f"🔍 Fetching COG URLs for geometry bounds: {geom.bounds}")
        cogs = extractor.get_cog_urls(geom)
        vprint(f"📦 Found {len(cogs)} COGs for the given geometry")
        
        if not cogs:
            vprint("⚠️  No COGs found for this geometry")
            return np.empty((0, len(band_indexes))), missing_px, px_area_m2

        for i, cog in enumerate(cogs):
            vprint(f"\n📊 Processing COG {i+1}/{len(cogs)}: {cog}")
            
            try:
                with rasterio.open(cog) as src:
                    vprint(f"  📋 COG info: CRS={src.crs}, shape={src.shape}, dtype={src.dtypes[0]}")
                    vprint(f"  📏 Resolution: {src.res}, bounds: {src.bounds}")
                    
                    # Choose appropriate geometry based on raster CRS
                    mask_geom = geom_wgs84 if src.crs.to_epsg() == 4326 else geom_3857
                    vprint(f"  🎯 Using {'WGS84' if src.crs.to_epsg() == 4326 else 'Web Mercator'} geometry for masking")
                    
                    # Check if raster is extremely large and might cause memory issues
                    total_pixels = src.width * src.height
                    if total_pixels > 100_000_000:  # 100M pixels
                        vprint(f"  ⚠️  Large raster detected - this may take several minutes or cause memory issues")
                    
                    vprint(f"  ✂️  Applying rasterio mask...")
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
                        vprint(f"  ✓ Mask result shape: {out.shape}, dtype: {out.dtype}")
                        
                        # Check if mask result is reasonable
                        if out.size == 0:
                            vprint(f"  ⚠️  Mask returned empty array - geometry may not intersect raster")
                            continue
                        elif out.size > 50_000_000:  # 50M pixels in result
                            vprint(f"  ⚠️  Large mask result ({out.size:,} pixels) - processing may be slow")
                            
                    except MemoryError as e:
                        vprint(f"  ❌ Memory error during masking: {str(e)}")
                        vprint(f"  💡 Raster too large for available memory - skipping this COG")
                        continue
                    except Exception as e:
                        vprint(f"  ❌ Error during masking operation: {str(e)}")
                        vprint(f"  💥 Mask error type: {type(e).__name__}")
                        raise

                    # ------------------------------------------------------------------
                    # Build a 2-D nodata mask (rows, cols)
                    # ------------------------------------------------------------------
                    nodata = src.nodata
                    vprint(f"  🚫 Nodata value: {nodata}")
                    
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
                    vprint(f"  📊 Missing pixels in this COG: {cog_missing}")

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
                    
                    vprint(f"  📈 Valid pixels: {valid_pixels_after} (from {valid_pixels_before} total)")

                    if arr.size:
                        if px_area_m2 is None:
                            vprint("  📐 Calculating pixel area...")
                            resx, resy = src.res

                            if src.crs and src.crs.is_geographic:
                                # CRS units are degrees – compute geodesic area of one pixel at tile centre
                                vprint("  🌍 Geographic CRS - calculating geodesic area")
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
                                vprint(f"    ✓ Pixel area: {px_area_m2:.2f} m²")
                            else:
                                # CRS units are metres – area = resx * resy
                                vprint("  📏 Projected CRS - using resolution for area")
                                px_area_m2 = abs(resx * resy)
                                vprint(f"    ✓ Pixel area: {px_area_m2:.2f} m²")
                        
                        reshaped_arr = arr.reshape(-1, len(band_indexes))
                        pixels.append(reshaped_arr)
                        vprint(f"  ✅ Added {reshaped_arr.shape[0]} pixels to collection")
                    else:
                        vprint("  ⚠️  No valid pixels in this COG")
                        
            except Exception as e:
                vprint(f"  ❌ Error processing COG {cog}: {str(e)}")
                vprint(f"  💥 Error type: {type(e).__name__}")
                # Continue with next COG instead of failing entirely
                continue

        vprint(f"\n📊 Final summary:")
        vprint(f"  Total COGs processed: {len(cogs)}")
        vprint(f"  Total missing pixels: {missing_px}")
        vprint(f"  Pixel collections: {len(pixels)}")
        
        if not pixels:
            vprint("⚠️  No valid pixels found in any COG")
            return np.empty((0, len(band_indexes))), missing_px, px_area_m2

        final_pixels = np.vstack(pixels)
        vprint(f"✅ Successfully extracted {final_pixels.shape[0]} total pixels")
        return final_pixels, missing_px, px_area_m2
        
    except Exception as e:
        vprint(f"❌ Critical error in extract_pixels_with_missing: {str(e)}")
        vprint(f"💥 Error type: {type(e).__name__}")
        raise

def apply_geometry_mask_to_raster(
    raster_path: Union[str, Path],
    geometry,
    output_path: Union[str, Path],
    nodata_value: Union[int, float] = -999,
    inside: bool = True
) -> bool:
    """
    Apply a geometry mask to a raster file.
    
    Parameters
    ----------
    raster_path : str or Path
        Path to input raster
    geometry : shapely geometry
        Geometry to use for masking
    output_path : str or Path
        Path for output masked raster
    nodata_value : int or float, optional
        Value to use for masked areas (default: -999)
    inside : bool, optional
        If True, keep values inside geometry. If False, keep values outside (default: True)
        
    Returns
    -------
    bool
        True if masking succeeded, False otherwise
    """
    try:
        with rasterio.open(raster_path) as src:
            # Create mask
            mask_array = geometry_mask(
                [geometry],
                transform=src.transform,
                invert=inside,  # invert=True means inside is True, outside is False
                out_shape=(src.height, src.width)
            )
            
            # Read data and apply mask
            data = src.read()
            
            # Apply mask to all bands
            for band_idx in range(data.shape[0]):
                data[band_idx][mask_array] = nodata_value
            
            # Update profile
            profile = src.profile.copy()
            profile.update(nodata=nodata_value)
            
            # Write masked raster
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(data)
        
        return True
        
    except Exception as e:
        vprint(f"Failed to apply geometry mask: {str(e)}")
        return False


def add_overviews_simple(
    raster_path: Union[str, Path],
    levels: List[int] = [2, 4, 8, 16, 32, 64],
    resampling: str = "average"
) -> bool:
    """
    Add overviews to a raster using gdaladdo command.
    
    Parameters
    ----------
    raster_path : str or Path
        Path to the raster file to add overviews to
    levels : List[int], optional
        Overview levels to create (default: [2, 4, 8, 16, 32, 64])
    resampling : str, optional
        Resampling method (default: "average")
        
    Returns
    -------
    bool
        True if overview creation succeeded, False otherwise
    """
    try:
        cmd = ["gdaladdo", "-r", resampling, str(raster_path)] + [str(level) for level in levels]
        
        vprint(f"Adding overviews to {raster_path} with levels {levels}")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        vprint(f"Successfully added overviews to: {raster_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        vprint(f"Failed to add overviews: {e.stderr}")
        return False
    except Exception as e:
        vprint(f"Failed to add overviews: {str(e)}")
        return False


def create_optimized_raster(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    compression: str = 'lzw',
    add_overviews: bool = True,
    overview_levels: List[int] = [2, 4, 8, 16, 32, 64],
    blocksize: int = 512
) -> bool:
    """
    Create an optimized raster with optional overviews using standard GDAL tools.
    
    Parameters
    ----------
    input_path : str or Path
        Path to input raster
    output_path : str or Path
        Path for output optimized raster
    compression : str, optional
        Compression method (default: 'lzw')
    add_overviews : bool, optional
        Whether to add overviews (default: True)
    overview_levels : List[int], optional
        Overview levels to create (default: [2, 4, 8, 16, 32, 64])
    blocksize : int, optional
        Block size for tiling (default: 512)
        
    Returns
    -------
    bool
        True if optimization succeeded, False otherwise
    """
    try:
        # Copy the input to output with optimized settings using gdal_translate
        cmd = [
            "gdal_translate",
            "-co", f"COMPRESS={compression.upper()}",
            "-co", "TILED=YES",
            "-co", f"BLOCKXSIZE={blocksize}",
            "-co", f"BLOCKYSIZE={blocksize}",
            str(input_path),
            str(output_path)
        ]
        
        vprint(f"Creating optimized raster: {output_path}")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Add overviews if requested
        if add_overviews:
            if not add_overviews_simple(output_path, overview_levels):
                return False
        
        vprint(f"Successfully created optimized raster: {output_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        vprint(f"Failed to create optimized raster: {e.stderr}")
        return False
    except Exception as e:
        vprint(f"Failed to create optimized raster: {str(e)}")
        return False
