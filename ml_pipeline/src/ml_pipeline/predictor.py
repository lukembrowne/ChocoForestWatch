"""
ml_pipeline.predictor
~~~~~~~~~~~~~~~~~~~~~
Generate land-cover prediction rasters from a trained model.

Requires
--------
pip install rasterio numpy tqdm
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pickle
import os
from dotenv import load_dotenv
from datetime import datetime

import numpy as np
import rasterio
from shapely.geometry import shape, mapping

from tqdm import tqdm

from osgeo import gdal, gdalconst
import tempfile
import shutil

from ml_pipeline.s3_utils import upload_file

# ---------------------------------------------------------------------------
#  Predictor configuration
# ---------------------------------------------------------------------------


@dataclass
class PredictorConfig:
    blocksize: int = 1024          # window size (pixels) – change for memory
    compress: str = "lzw"         # GTiff compression
    dtype: str = "uint8"          # output data type
    nodata: int = 255             # value for pixels we can't predict
    predictor: int = 2            # GDAL "predictor" tag for compression


# ---------------------------------------------------------------------------
#  Predictor class
# ---------------------------------------------------------------------------


class ModelPredictor:
    """
    Parameters
    ----------
    model_path
        `.pkl` file produced by ModelTrainer.
    extractor
        The same TitilerExtractor (or any obj with `.get_cog_urls()`).
    cfg
        PredictorConfig with I/O settings.
    """

    def __init__(
        self,
        model_path: str | Path,
        extractor,
        upload_to_s3: bool,
        s3_path: str,
        cfg: PredictorConfig = PredictorConfig(),
    ):
        self.model_path = Path(model_path)
        self.extractor = extractor
        self.cfg = cfg
        self.upload_to_s3 = upload_to_s3
        self.s3_path = s3_path

        with open(self.model_path, "rb") as f:
            bundle = pickle.load(f)
        self.model = bundle["model"]
        self.meta = bundle["meta"]

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def predict_aoi(
        self,
        aoi_geojson: dict,
        basemap_date: str,
        pred_dir: str | Path,
        collection: str = "nicfi-2022",
    ) -> list[Path]:
        """
        Returns
        -------
        list of Path objects pointing to saved prediction COGs
        """
        # 1️⃣ get all COG URLs intersecting the AOI bbox
        bbox_poly = shape(aoi_geojson)  # EPSG:3857 polygon
        cog_urls = self.extractor.get_cog_urls(collection, bbox_poly)

        # Print cog_urls
        print(f"Found {len(cog_urls)} COG URLs")

        saved = []
        for url in tqdm(cog_urls, desc="Predicting"):
            out_path = self._predict_single_cog(
                cog_url=url,
                basemap_date=basemap_date,
            )
            saved.append(out_path)

        print(f"Saved {len(saved)} prediction rasters ➜ {pred_dir}")
        return saved
    
    def predict_collection(
        self,
        basemap_date: str,
        collection: str,
        pred_dir: str | Path,
        save_local: bool = True,
    ) -> list[Path]:
        """
        Run the model on *every* COG in a STAC collection.
        
        Warning: This will overwrite any existing prediction files with the same names
        in the prediction directory.

        Returns
        -------
        list[Path]
            Paths to the saved prediction COGs.
        """

        # Limit to northern Choco for now
        bbox = "-80.325,-0.175,-78.2523342311799439,1.4466469335460774"

        # Get all COG URLs intersecting the bounding box
        cog_urls = self.extractor.get_all_cog_urls(collection, bbox=bbox)


        print(f"Found {len(cog_urls)} COGs in collection '{collection}'")
        print(f"Warning: This will overwrite any existing prediction files in {pred_dir}")

        # If pred_dir is a string, convert it to a Path object
        if isinstance(pred_dir, str):
            pred_dir = Path(pred_dir)

        # Create the prediction directory if it doesn't exist
        pred_dir.mkdir(parents=True, exist_ok=True)

        saved: list[Path] = []
        for url in tqdm(cog_urls, desc=f"Predicting {collection}"):
            saved.append(
                self._predict_single_cog(
                    cog_url=url,
                    basemap_date=basemap_date,
                    pred_dir=pred_dir,
                    save_local=save_local,
                )
            )

        print(f"Saved {len(saved)} prediction rasters ➜ {pred_dir}")
        return saved

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _predict_single_cog(self, cog_url: str, basemap_date: str, pred_dir: str | Path, save_local: bool = True) -> Path:
        try:
            with rasterio.open(cog_url) as src:
                profile = src.profile.copy()
                profile.update(
                    count=1,
                    dtype=self.cfg.dtype,
                    compress=self.cfg.compress,
                    predictor=self.cfg.predictor,
                    nodata=self.cfg.nodata,
                )

                # build output filename
                tile_id = Path(cog_url).stem
                out_path = pred_dir / f"{tile_id}.tiff"

                with rasterio.open(out_path, "w", **profile) as dst:
                    # iterate by window to keep memory small
                    for ji, window in src.block_windows(1):
                        try:
                            img = src.read(window=window, indexes=(1, 2, 3, 4)).astype(
                                np.float32
                            )  # (4, h, w)
                        except Exception as e:
                            print(f"Error reading window {window} from {cog_url}: {e}")
                            continue

                        h, w = img.shape[1], img.shape[2]
                        X = img.reshape(4, -1).T  # -> (n,4)

                        X_full = X

                        # mask nodata
                        valid_mask = ~np.any(
                            X[:, :4] == src.nodata, axis=1
                        )  # ignore temporal cols
                        preds = np.full(X.shape[0], self.cfg.nodata, dtype=self.cfg.dtype)
                        if valid_mask.any():
                            try:
                                y_pred = self.model.predict(X_full[valid_mask])
                                # map from consecutive to global indices
                                y_global = np.vectorize(
                                    self.model.consecutive_to_global.get
                                )(y_pred)
                                preds[valid_mask] = y_global.astype(self.cfg.dtype)
                            except Exception as e:
                                print(f"Error predicting window {window} from {cog_url}: {e}")
                                continue

                        dst.write(preds.reshape(1, h, w), window=window)

                # ➊ run sieve
                try:
                    self._sieve_inplace(out_path, min_pixels=10)
                except Exception as e:
                    print(f"Error applying sieve filter to {out_path}: {e}")

                # Upload to Spaces if configured
                try:
                    if self.upload_to_s3:
                        self._upload_to_s3(out_path, basemap_date)
                except Exception as e:
                    print(f"Error uploading {out_path} to Spaces: {e}")

                # Delete local file if not saving locally
                if not save_local:
                    out_path.unlink()
                    return None

            return out_path

        except Exception as e:
            print(f"⚠️ Skipping COG due to error: {cog_url} — {e}")
            return None

    def _sieve_inplace(self, tif_path: Path, min_pixels: int) -> None:
        """
        In-place GDAL sieve: remove connected components smaller than *min_pixels*.
        Keeps compression and nodata tags.
        """
        print(f"Applying sieve filter with {min_pixels} pixels")

        gdal.UseExceptions()

        # open in UPDATE mode
        ds = gdal.Open(str(tif_path), gdalconst.GA_Update)
        if ds is None:
            raise RuntimeError(f"GDAL failed to open {tif_path!s}")

        band = ds.GetRasterBand(1)
        nodata = band.GetNoDataValue()

        # run sieve: dest == src for in-place, mask = None, 8-connected
        gdal.SieveFilter(srcBand=band,
                        maskBand=None,
                        dstBand=band,
                        threshold=min_pixels,
                        connectedness=8)

        # restore nodata (GDAL sometimes drops it)
        if nodata is not None:
            band.SetNoDataValue(nodata)

        band.FlushCache()
        ds = None  # close dataset

    def _upload_to_s3(self, local_path: Path, basemap_date: str) -> None:
        """Upload a COG to DigitalOcean Spaces."""
        if not self.upload_to_s3:
            return  # uploading disabled
            
        yyyy, mm = basemap_date.split("-")
        remote_key = f"{self.s3_path}/{yyyy}/{mm}/{local_path.name}"
        
        upload_file(local_path, remote_key)

