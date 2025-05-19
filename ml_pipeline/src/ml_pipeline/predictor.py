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
import boto3
from dotenv import load_dotenv
from datetime import datetime

import numpy as np
import rasterio
from shapely.geometry import shape, mapping

from tqdm import tqdm

from osgeo import gdal, gdalconst
import tempfile
import shutil

# ---------------------------------------------------------------------------
#  Predictor configuration
# ---------------------------------------------------------------------------


@dataclass
class PredictorConfig:
    blocksize: int = 1024          # window size (pixels) – change for memory
    compress: str = "lzw"         # GTiff compression
    dtype: str = "uint8"          # output data type
    nodata: int = 255             # value for pixels we can’t predict
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
        cfg: PredictorConfig = PredictorConfig(),
        upload_to_spaces: bool = False,
    ):
        self.model_path = Path(model_path)
        self.extractor = extractor
        self.cfg = cfg
        # optional Spaces client
        if upload_to_spaces:
            load_dotenv()
            self.s3 = boto3.session.Session().client(
                "s3",
                region_name=os.getenv("AWS_REGION"),
                endpoint_url="https://" + os.getenv("AWS_S3_ENDPOINT"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )
            self.bucket = "choco-forest-watch"
        else:
            self.s3 = None

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
        cog_urls = self.extractor.get_all_cog_urls(collection)
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
                )
            )

        print(f"Saved {len(saved)} prediction rasters ➜ {pred_dir}")
        return saved

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _predict_single_cog(self, cog_url: str, basemap_date: str, pred_dir: str | Path) -> Path:
        # year, month = basemap_date.split("-")
        # year_enc = self.model.year_encoder.transform([year])[0]
        # month_enc = self.model.month_encoder.transform([int(month)])[0]

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
                    img = src.read(window=window, indexes=(1, 2, 3, 4)).astype(
                        np.float32
                    )  # (4, h, w)
                    h, w = img.shape[1], img.shape[2]
                    X = img.reshape(4, -1).T  # -> (n,4)

                    # add temporal features
                    # years = np.full((X.shape[0], 1), year_enc)
                    # months = np.full((X.shape[0], 1), month_enc)
                    # X_full = np.hstack([X, years, months])

                    X_full = X

                    # mask nodata
                    valid_mask = ~np.any(
                        X[:, :4] == src.nodata, axis=1
                    )  # ignore temporal cols
                    preds = np.full(X.shape[0], self.cfg.nodata, dtype=self.cfg.dtype)
                    if valid_mask.any():
                        y_pred = self.model.predict(X_full[valid_mask])
                        # map from consecutive to global indices
                        y_global = np.vectorize(
                            self.model.consecutive_to_global.get
                        )(y_pred)
                        preds[valid_mask] = y_global.astype(self.cfg.dtype)

                    dst.write(preds.reshape(1, h, w), window=window)


            # ➊ run sieve
            self._sieve_inplace(out_path, min_pixels=10)


            # Upload to Spaces if configured after iterating through all the windows
            if self.s3:
                self._upload_to_spaces(out_path, basemap_date)

        return out_path
    

    # ------------------------------------------------------------------
    # helper inside ModelPredictor
    # ------------------------------------------------------------------
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
        
# ..............................................................
    def _upload_to_spaces(self, local_path: Path, basemap_date: str) -> None:
        """Upload a COG to DigitalOcean Spaces using cfg.key_template."""
        if not self.s3:
            return  # uploading disabled
        yyyy, mm = basemap_date.split("-")
        remote_key = f"predictions/{self.meta.get('model_id', 'model')}/{yyyy}/{mm}/{local_path.name}"

        print(f"⤴️  Uploading {local_path.name} → {remote_key}")
        # Upload file with private access (no public ACL)
        self.s3.upload_file(
            Filename=str(local_path),
            Bucket=self.bucket,
            Key=remote_key,
            ExtraArgs={"ContentType": "image/tiff"},
        )

