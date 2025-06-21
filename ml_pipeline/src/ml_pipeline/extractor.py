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


    def get_cog_urls(self, polygon_wgs84) -> list[str]:
        """Return COG URLs intersecting *polygon_wgs84* (EPSG:4326)."""
        minx, miny, maxx, maxy = polygon_wgs84.bounds
        bbox = f"{minx},{miny},{maxx},{maxy}"
        r = requests.get(
            f"{self.base_url}/collections/{self.collection}/bbox/{bbox}/assets",
            headers={"accept": "application/json"},
            timeout=30,
        )
        r.raise_for_status()
        return [a["assets"]["data"]["href"] for a in r.json()]



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

        print(f"Getting all COG URLs for collection {collection} with bbox {bbox}")
        
        # If bbox is the whole world, query database directly to get all URLs
        if bbox == "-180,-90,180,90":
            return self._get_all_cog_urls_from_db(collection, scan_limit)
        else:
            # Use the bbox endpoint for spatial filtering
            r = requests.get(
                f"{self.base_url}/collections/{collection}/bbox/{bbox}/assets",
                params={"scan_limit": scan_limit},
                headers={"accept": "application/json"},
                timeout=60,
            )
            r.raise_for_status()
            return [a["assets"]["data"]["href"] for a in r.json()]
    
    def _get_all_cog_urls_from_db(self, collection: str, scan_limit: int) -> list[str]:
        """Get all COG URLs directly from the database when no bbox filtering is needed."""
        import psycopg2
        import os
        
        try:
            # Connect to the database
            conn = psycopg2.connect(
                host=os.getenv("PGHOST", "localhost"),
                port=os.getenv("PGPORT", "5432"),
                database=os.getenv("POSTGRES_DB", "postgis"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "")
            )
            
            with conn.cursor() as cur:
                # Query all items from the collection
                cur.execute("""
                    SELECT content->'assets'->'data'->>'href' as href
                    FROM items 
                    WHERE collection = %s 
                    AND content->'assets'->'data' IS NOT NULL
                    LIMIT %s
                """, (collection, scan_limit))
                
                urls = [row[0] for row in cur.fetchall() if row[0]]
                print(f"Retrieved {len(urls)} COGs from database")
                return urls
                
        except Exception as e:
            print(f"Database query failed: {e}")
            print("Falling back to API method with smaller chunks...")
            return self._get_all_cog_urls_chunked(collection, scan_limit)
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _get_all_cog_urls_chunked(self, collection: str, scan_limit: int) -> list[str]:
        """Get all COG URLs by splitting the world into smaller chunks to work around API limits."""
        all_urls = set()  # Use set to avoid duplicates
        
        # Split world into 4x4 grid (16 chunks)
        lon_step = 90  # 360/4
        lat_step = 45  # 180/4
        
        for lon_start in range(-180, 180, lon_step):
            for lat_start in range(-90, 90, lat_step):
                lon_end = lon_start + lon_step
                lat_end = lat_start + lat_step
                chunk_bbox = f"{lon_start},{lat_start},{lon_end},{lat_end}"
                
                try:
                    r = requests.get(
                        f"{self.base_url}/collections/{collection}/bbox/{chunk_bbox}/assets",
                        params={"scan_limit": scan_limit},
                        headers={"accept": "application/json"},
                        timeout=30,
                    )
                    r.raise_for_status()
                    chunk_urls = [a["assets"]["data"]["href"] for a in r.json()]
                    all_urls.update(chunk_urls)
                    
                    if chunk_urls:
                        print(f"Chunk {chunk_bbox}: {len(chunk_urls)} COGs (total unique: {len(all_urls)})")
                        
                except Exception as e:
                    print(f"Failed to query chunk {chunk_bbox}: {e}")
                    continue
                    
                # Stop if we've reached the scan limit
                if len(all_urls) >= scan_limit:
                    break
            
            if len(all_urls) >= scan_limit:
                break
        
        result = list(all_urls)[:scan_limit]
        print(f"Total unique COGs retrieved: {len(result)}")
        return result

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
               # print("Extracting pixels from COG:", cog, "for polygon:", fid)
                try:
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
                except Exception as e:
                    print(f"⚠️  Skipping Extracting pixels from this COG due to error: {cog} — {str(e)}")
                    continue

        if not pixels:
            raise RuntimeError("No valid pixels were extracted from any COGs.")

        print("Pixels :", sum(len(p) for p in pixels))
        print("Labels :", len(labels))
        print("Fids   :", len(fids))
        return np.vstack(pixels), np.array(labels), np.array(fids)
    
# Get one random sample point per quad (deterministic with a seed)
# for sample in ext.iter_one_random_point_per_quad(seed=42):
#     print(sample["quad_id"], sample["lon"], sample["lat"])