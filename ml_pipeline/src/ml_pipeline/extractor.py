# ml_pipeline/extractor.py
"""
Utility class for pixel extraction and sampling from Planet-NICFI COG mosaics
served by a TiTiler/pgSTAC API.
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Iterator, Optional, List, Dict, Any

import numpy as np
import requests
import rasterio
from rasterio.mask import mask
from shapely.geometry import Point, mapping


class TitilerExtractor:
    """High-level helper for listing COGs, extracting pixels, and sampling."""

    def __init__(self, base_url: str, collection: str, band_indexes: list[int]):
        """
        Parameters
        ----------
        base_url : str
            Root of the TiTiler service (e.g. ``http://localhost:8083``).
        collection : str
            STAC collection ID that contains the monthly quads.
        band_indexes : list[int]
            1-based band indexes to read from each COG.
        """
        self.base_url = base_url.rstrip("/")
        self.collection = collection
        self.band_indexes = band_indexes

    # ------------------------------------------------------------------ #
    #  Metadata helpers
    # ------------------------------------------------------------------ #

    def get_all_cog_urls(self, collection: Optional[str] = None,
                         bbox: Optional[str] = None,
                         scan_limit: int = 100_000) -> list[str]:
        """Return every COG URL in *collection* (defaults to ``self.collection``).
        
        Parameters
        ----------
        collection : str, optional
            The collection ID to query. If None, uses self.collection.
        bbox : str, optional
            Bounding box in format "minx,miny,maxx,maxy". If None, uses the whole world.
        scan_limit : int, optional
            Maximum number of items to scan, by default 100_000.
            
        Returns
        -------
        list[str]
            List of COG URLs in the collection within the bbox.
        """
        collection = collection or self.collection
        bbox = bbox or "-180,-90,180,90"  # whole world if no bbox provided
        
        r = requests.get(
            f"{self.base_url}/collections/{collection}/bbox/{bbox}/assets",
            params={"scan_limit": scan_limit},
            headers={"accept": "application/json"},
            timeout=60,
        )
        r.raise_for_status()
        return [a["assets"]["data"]["href"] for a in r.json()]

    # ------------------------------------------------------------------ #
    #  Random point generation
    # ------------------------------------------------------------------ #

    def random_points_in_quad(
        self,
        cog_url: str,
        count: int,
        rng: Optional[random.Random] = None,
    ) -> List[Dict[str, Any]]:
        """
        Draw multiple random geographic points inside the bounding box of one quad / COG.

        Parameters
        ----------
        cog_url : str
            HREF to a Cloud-Optimised GeoTIFF (one NICFI quad).
        count : int
            Number of points to generate for this quad.
        rng : random.Random, optional
            Supply your own RNG (e.g. ``random.Random(seed)``) for repeatability.

        Returns
        -------
        list[dict]
            List of point dictionaries, each containing:
            {"quad_id": str, "cog_url": str, "x": float, "y": float,
            "point": shapely.geometry.Point}
        """
        rng = rng or random
        points = []
        
        with rasterio.open(cog_url) as src:
            # Uses metadata only – no raster blocks read.
            bounds = src.bounds
            # Draw uniform random lon/lat within bounding box
            for _ in range(count):
                x = rng.uniform(bounds.left, bounds.right)
                y = rng.uniform(bounds.bottom, bounds.top)
                points.append({
                    "quad_id": Path(cog_url).stem,
                    "cog_url": cog_url,
                    "x": x,
                    "y": y,
                    "point": Point(x, y),
                })
        
        return points

    # ------------------------------------------------------------------ #
    #  Pixel extraction
    # ------------------------------------------------------------------ #

    def extract_pixels(self, gdf) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extract pixels for each labelled polygon in *gdf*.

        Parameters
        ----------
        gdf : geopandas.GeoDataFrame
            Must contain geometry column and fields ``id`` and ``classLabel``.

        Returns
        -------
        X : np.ndarray
            2-D array of shape (n_samples, n_bands) with predictor values.
        y : np.ndarray
            1-D array of class labels.
        fid : np.ndarray
            1-D array of polygon IDs corresponding to each sample.
        """
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
        gdf_3857 = gdf.to_crs("EPSG:3857")

        pixels, labels, fids = [], [], []

        for wgs84_geom, webm_geom, fid, label in zip(
            gdf_wgs84.geometry,
            gdf_3857.geometry,
            gdf["id"],
            gdf["classLabel"],
        ):
            for cog in self.get_cog_urls(wgs84_geom):
                with rasterio.open(cog) as src:
                    mask_geom = wgs84_geom if src.crs.to_epsg() == 4326 else webm_geom
                    out, _ = mask(
                        src,
                        [mapping(mask_geom)],
                        crop=True,
                        indexes=self.band_indexes,
                        all_touched=True,
                    )
                    arr = np.moveaxis(out, 0, -1).reshape(-1, len(self.band_indexes))
                    nodata = src.nodata
                    if nodata is not None:
                        arr = arr[~np.all(arr == nodata, axis=1)]

                pixels.append(arr)
                labels.extend([label] * len(arr))
                fids.extend([fid] * len(arr))

        print("Pixels :", sum(len(p) for p in pixels))
        print("Labels :", len(labels))
        print("Fids   :", len(fids))
        return np.vstack(pixels), np.array(labels), np.array(fids)
    
# Get one random sample point per quad (deterministic with a seed)
# for sample in ext.iter_one_random_point_per_quad(seed=42):
#     print(sample["quad_id"], sample["lon"], sample["lat"])