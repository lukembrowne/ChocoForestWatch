# NEW FILE: ml_pipeline/raster_utils.py
from __future__ import annotations
import numpy as np
from shapely.geometry import mapping
import rasterio
from rasterio.mask import mask
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")  # reused for geodesic area calculations

def pixels_to_labels(collection: str, pixels: np.ndarray) -> np.ndarray:
    """Dataset-specific mapping ➜ 'Forest' / 'Non-Forest' / np.nan"""
    if "nicfi" in collection:
        out = np.where(pixels == 0, "Non-Forest", np.where(pixels == 1, "Forest", np.nan))
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

    for cog in extractor.get_cog_urls(geom):
        with rasterio.open(cog) as src:
            out, _ = mask(
                src,
                [mapping(geom)],
                crop=True,
                indexes=band_indexes,
                all_touched=True,
            )                                             # (bands, rows, cols) or (rows, cols)

            # ------------------------------------------------------------------
            # Build a 2-D nodata mask (rows, cols)
            # ------------------------------------------------------------------
            nodata = src.nodata
            if nodata is not None and not np.isnan(nodata):
                if out.ndim == 3:                         # multi-band
                    nodata_mask = np.all(out == nodata, axis=0)
                else:                                    # single band
                    nodata_mask = out == nodata
            else:
                # no nodata metadata – treat everything as valid
                nodata_mask = np.zeros(out.shape[-2:], dtype=bool)

            missing_px += int(nodata_mask.sum())

            # ------------------------------------------------------------------
            # Move bands to the last axis so mask lines up with first two dims
            # ------------------------------------------------------------------
            if out.ndim == 3:                            # (bands, rows, cols) ➜ (rows, cols, bands)
                arr = np.moveaxis(out, 0, -1)
            else:                                        # (rows, cols) ➜ add a bands axis
                arr = out[..., np.newaxis]

            # Apply mask & flatten
            arr = arr[~nodata_mask]                      # (n_valid_px, bands)

            if arr.size:
                if px_area_m2 is None:
                    resx, resy = src.res

                    if src.crs and src.crs.is_geographic:
                        # CRS units are degrees – compute geodesic area of one pixel at tile centre
                        # Use the centre coordinate for latitude-dependent area
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
                    else:
                        # CRS units are metres – area = resx * resy
                        px_area_m2 = abs(resx * resy)
                pixels.append(arr.reshape(-1, len(band_indexes)))

    if not pixels:
        return np.empty((0, len(band_indexes))), missing_px, px_area_m2

    return np.vstack(pixels), missing_px, px_area_m2