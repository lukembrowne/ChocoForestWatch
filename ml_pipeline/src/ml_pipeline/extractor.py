# ml_pipeline/extractor.py
"""
Utility class for pixel extraction and sampling from Planet-NICFI COG mosaics
using PostgreSQL/PostGIS database queries.
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Iterator, Optional, List, Dict, Any

import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import Point, mapping
from sqlalchemy import text
import pandas as pd
from ml_pipeline.db_utils import get_db_connection


class TitilerExtractor:
    """High-level helper for listing COGs from database, extracting pixels, and sampling."""

    def __init__(self, collection: str, band_indexes: list[int], db_host: str = "local"):
        """
        Parameters
        ----------
        collection : str
            STAC collection ID that contains the monthly quads.
        band_indexes : list[int]
            1-based band indexes to read from each COG.
        db_host : str, optional
            Database host configuration: 'local' or 'remote', by default "local"
        """
        self.collection = collection
        self.band_indexes = band_indexes
        self.db_host = db_host
        self._db_engine = None

    # ------------------------------------------------------------------ #
    #  Metadata helpers
    # ------------------------------------------------------------------ #


    def get_cog_urls(self, polygon_wgs84=None, collection: Optional[str] = None) -> list[str]:
        """
        Return COG URLs, optionally filtered by polygon intersection.
        
        Parameters
        ----------
        polygon_wgs84 : shapely.geometry, optional
            Polygon in EPSG:4326 to filter COGs by intersection. If None, returns all COGs.
        collection : str, optional
            Collection to query. If None, uses self.collection.
            
        Returns
        -------
        list[str]
            List of COG URLs
        """
        collection = collection or self.collection
        
        if polygon_wgs84 is None:
            # Return all COGs in collection
            return self._get_cogs_from_database(collection)
        else:
            # Return COGs intersecting the polygon
            return self._get_cogs_from_database(collection, polygon_wgs84)



    def get_all_cog_urls(self, collection: Optional[str] = None) -> list[str]:
        """Return every COG URL in *collection* (defaults to ``self.collection``).
        
        Parameters
        ----------
        collection : str, optional
            The collection ID to query. If None, uses self.collection.
            
        Returns
        -------
        list[str]
            List of COG URLs in the collection.
        """
        collection = collection or self.collection
        print(f"Getting all COG URLs for collection {collection}")
        return self._get_cogs_from_database(collection)
    
    @property
    def db_engine(self):
        """Lazy-load database engine."""
        if self._db_engine is None:
            self._db_engine = get_db_connection(host=self.db_host)
        return self._db_engine
    
    def _get_cogs_from_database(self, collection: str, polygon_wgs84=None) -> list[str]:
        """Get COG URLs from database, optionally filtered by spatial intersection.
        
        Parameters
        ----------
        collection : str
            STAC collection ID
        polygon_wgs84 : shapely.geometry, optional
            Polygon in WGS84 to filter by intersection. If None, returns all COGs.
            
        Returns
        -------
        list[str]
            List of COG URLs
        """
        try:
            if polygon_wgs84 is None:
                # Query all COGs in collection
                query = text("""
                    SELECT content->'assets'->'data'->>'href' as href
                    FROM items 
                    WHERE collection = :collection
                    AND content->'assets'->'data' IS NOT NULL
                """)
                
                df = pd.read_sql(query, self.db_engine, params={"collection": collection})
                urls = df['href'].tolist()
                print(f"Retrieved {len(urls)} COGs from database")
                
            else:
                # Spatial intersection query
                ecuador_wkt = polygon_wgs84.wkt
                
                query = text("""
                    SELECT content->'assets'->'data'->>'href' as href,
                           content->'id' as item_id
                    FROM items 
                    WHERE collection = :collection
                    AND content->'assets'->'data' IS NOT NULL
                    AND ST_Intersects(geometry, ST_GeomFromText(:ecuador_wkt, 4326))
                """)
                
                df = pd.read_sql(query, self.db_engine, params={
                    "collection": collection,
                    "ecuador_wkt": ecuador_wkt
                })
                
                urls = df['href'].tolist()
                print(f"Retrieved {len(urls)} COGs intersecting polygon from database")
            
            return urls
            
        except Exception as e:
            print(f"❌ Database query failed: {e}")
            print("❌ No fallback available - database connection required")
            return []
    

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