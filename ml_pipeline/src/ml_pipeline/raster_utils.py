# NEW FILE: ml_pipeline/raster_utils.py
from __future__ import annotations
import numpy as np
from shapely.geometry import mapping
import rasterio
from rasterio.mask import mask
from rasterio.features import geometry_mask
from rasterio.enums import Resampling
# Removed rio-cogeo imports - using simpler gdaladdo approach for overviews
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


def validate_raster_integrity(raster_path: Union[str, Path]) -> Dict[str, any]:
    """
    Validate raster file integrity and return comprehensive metadata.
    
    Parameters
    ----------
    raster_path : str or Path
        Path to the raster file to validate
        
    Returns
    -------
    dict
        Dictionary containing validation results and metadata
    """
    results = {
        "valid": False,
        "error": None,
        "metadata": {},
        "statistics": {},
        "warnings": []
    }
    
    try:
        with rasterio.open(raster_path) as src:
            # Basic metadata
            results["metadata"] = {
                "driver": src.driver,
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "dtype": str(src.dtypes[0]),
                "crs": str(src.crs) if src.crs else None,
                "nodata": src.nodata,
                "transform": src.transform,
                "bounds": src.bounds,
                "compression": src.compression.name if src.compression else None,
                "tiled": src.is_tiled,
                "blocksize": (src.block_shapes[0] if src.block_shapes else None),
                "overviews": [src.overviews(i) for i in range(1, src.count + 1)]
            }
            
            # Read first band for statistics
            data = src.read(1)
            
            # Calculate statistics
            valid_data = data[data != src.nodata] if src.nodata is not None else data
            
            results["statistics"] = {
                "total_pixels": data.size,
                "valid_pixels": valid_data.size,
                "missing_pixels": data.size - valid_data.size,
                "missing_percentage": ((data.size - valid_data.size) / data.size) * 100,
                "min_value": float(np.min(valid_data)) if valid_data.size > 0 else None,
                "max_value": float(np.max(valid_data)) if valid_data.size > 0 else None,
                "mean_value": float(np.mean(valid_data)) if valid_data.size > 0 else None,
                "std_value": float(np.std(valid_data)) if valid_data.size > 0 else None,
                "unique_values": len(np.unique(valid_data)) if valid_data.size > 0 else 0
            }
            
            # Validation checks
            if src.crs is None:
                results["warnings"].append("No CRS defined")
            
            if src.nodata is None:
                results["warnings"].append("No nodata value defined")
            
            if not src.is_tiled:
                results["warnings"].append("Raster is not tiled (not optimal for COG)")
            
            if not any(src.overviews(i) for i in range(1, src.count + 1)):
                results["warnings"].append("No overviews present")
            
            if src.width > 10000 or src.height > 10000:
                results["warnings"].append("Large raster dimensions may cause performance issues")
            
            results["valid"] = True
            
    except Exception as e:
        results["error"] = str(e)
        results["valid"] = False
    
    return results


def compute_file_checksum(file_path: Union[str, Path], algorithm: str = 'md5') -> str:
    """
    Compute checksum for a file.
    
    Parameters
    ----------
    file_path : str or Path
        Path to the file
    algorithm : str, optional
        Hash algorithm to use (default: 'md5')
        
    Returns
    -------
    str
        Hexadecimal digest of the file
    """
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


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
        print(f"Failed to apply geometry mask: {str(e)}")
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
        
        print(f"Adding overviews to {raster_path} with levels {levels}")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print(f"Successfully added overviews to: {raster_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to add overviews: {e.stderr}")
        return False
    except Exception as e:
        print(f"Failed to add overviews: {str(e)}")
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
        
        print(f"Creating optimized raster: {output_path}")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Add overviews if requested
        if add_overviews:
            if not add_overviews_simple(output_path, overview_levels):
                return False
        
        print(f"Successfully created optimized raster: {output_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to create optimized raster: {e.stderr}")
        return False
    except Exception as e:
        print(f"Failed to create optimized raster: {str(e)}")
        return False


def standardize_forest_labels(
    data: np.ndarray,
    collection_id: str,
    nodata_value: Union[int, float] = -999
) -> np.ndarray:
    """
    Standardize pixel values to forest (1) / non-forest (0) / nodata (-999) labels.
    
    Parameters
    ----------
    data : np.ndarray
        Input raster data
    collection_id : str
        Collection ID for pixel interpretation
    nodata_value : int or float, optional
        Value to use for nodata (default: -999)
        
    Returns
    -------
    np.ndarray
        Standardized array with values 0, 1, or nodata_value
    """
    try:
        # Use existing pixels_to_labels function
        labels = pixels_to_labels(collection_id, data)
        
        # Convert to standardized numeric format
        standardized = np.full_like(data, nodata_value, dtype=np.int16)
        
        forest_mask = (labels == "Forest")
        non_forest_mask = (labels == "Non-Forest")
        
        standardized[forest_mask] = 1
        standardized[non_forest_mask] = 0
        # Keep nodata_value for unknown/missing areas
        
        return standardized
        
    except Exception as e:
        print(f"Failed to standardize forest labels: {str(e)}")
        raise


def compare_raster_statistics(
    raster1_path: Union[str, Path],
    raster2_path: Union[str, Path]
) -> Dict[str, any]:
    """
    Compare statistics between two rasters.
    
    Parameters
    ----------
    raster1_path : str or Path
        Path to first raster
    raster2_path : str or Path
        Path to second raster
        
    Returns
    -------
    dict
        Comparison results
    """
    results = {
        "compatible": False,
        "differences": [],
        "statistics_comparison": {}
    }
    
    try:
        stats1 = validate_raster_integrity(raster1_path)
        stats2 = validate_raster_integrity(raster2_path)
        
        if not (stats1["valid"] and stats2["valid"]):
            results["differences"].append("One or both rasters are invalid")
            return results
        
        # Check spatial compatibility
        meta1 = stats1["metadata"]
        meta2 = stats2["metadata"]
        
        if (meta1["width"] != meta2["width"] or 
            meta1["height"] != meta2["height"]):
            results["differences"].append("Different dimensions")
        
        if meta1["crs"] != meta2["crs"]:
            results["differences"].append("Different CRS")
        
        if meta1["transform"] != meta2["transform"]:
            results["differences"].append("Different transform/resolution")
        
        # Compare statistics
        stat1 = stats1["statistics"]
        stat2 = stats2["statistics"]
        
        for key in ["total_pixels", "valid_pixels", "missing_pixels"]:
            if stat1[key] != stat2[key]:
                results["differences"].append(f"Different {key}")
        
        results["statistics_comparison"] = {
            "raster1": stat1,
            "raster2": stat2
        }
        
        results["compatible"] = len(results["differences"]) == 0
        
    except Exception as e:
        results["differences"].append(f"Comparison failed: {str(e)}")
    
    return results


def get_raster_overview_info(raster_path: Union[str, Path]) -> Dict[str, any]:
    """
    Get detailed information about raster overviews.
    
    Parameters
    ----------
    raster_path : str or Path
        Path to the raster file
        
    Returns
    -------
    dict
        Overview information
    """
    info = {
        "has_overviews": False,
        "overview_count": 0,
        "overview_levels": [],
        "overview_sizes": []
    }
    
    try:
        with rasterio.open(raster_path) as src:
            for band_idx in range(1, src.count + 1):
                overviews = src.overviews(band_idx)
                if overviews:
                    info["has_overviews"] = True
                    info["overview_count"] = len(overviews)
                    info["overview_levels"] = overviews
                    
                    # Calculate overview sizes
                    overview_sizes = []
                    for level in overviews:
                        ov_width = src.width // level
                        ov_height = src.height // level
                        overview_sizes.append((ov_width, ov_height))
                    
                    info["overview_sizes"] = overview_sizes
                break  # Just check first band
    
    except Exception as e:
        info["error"] = str(e)
    
    return info