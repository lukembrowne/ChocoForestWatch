# ml_pipeline/extractor.py
import requests, rasterio
from rasterio.mask import mask
import numpy as np
from shapely.geometry import mapping

class TitilerExtractor:
    def __init__(self, base_url: str , collection: str ):
        self.base_url = base_url
        self.collection = collection

    def get_cog_urls(self, polygon_wgs84) -> list[str]:
        minx, miny, maxx, maxy = polygon_wgs84.bounds
        bbox = f"{minx},{miny},{maxx},{maxy}"
        r = requests.get(f"{self.base_url}/collections/{self.collection}/bbox/{bbox}/assets",
                         headers={"accept": "application/json"})
        r.raise_for_status()
        return [a["assets"]["data"]["href"] for a in r.json()]

    def get_all_cog_urls(self, collection: str, scan_limit: int = 100_000) -> list[str]:
        """Return every COG URL in a collection."""
        bbox = "-180,-90,180,90"                     # whole world
        r = requests.get(
            f"{self.base_url}/collections/{collection}/bbox/{bbox}/assets",
            params={"scan_limit": scan_limit},       # raise if you have > scan_limit items
            headers={"accept": "application/json"},
        )
        r.raise_for_status()
        return [a["assets"]["data"]["href"] for a in r.json()]

    def extract_pixels(self, gdf) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
        gdf_3857  = gdf.to_crs("EPSG:3857")
        pixels, labels, fids = [], [], []
        for (wgs84_geom, webm_geom, fid, label) in zip(
                gdf_wgs84.geometry, gdf_3857.geometry,
                gdf["id"], gdf["classLabel"]):
            for cog in self.get_cog_urls(wgs84_geom):
                with rasterio.open(cog) as src:
                    out, _ = mask(src, [mapping(webm_geom)], crop=True,
                                  indexes=(1, 2, 3, 4), all_touched=True)
                    arr = np.moveaxis(out, 0, -1).reshape(-1, 4)
                    nodata = src.nodata
                    if nodata is not None:
                        arr = arr[~np.all(arr == nodata, axis=1)]
                    pixels.append(arr)
                    labels.extend([label] * len(arr))
                    fids.extend([fid] * len(arr))
        return np.vstack(pixels), np.array(labels), np.array(fids)