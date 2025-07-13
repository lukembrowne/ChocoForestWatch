"""
Standalone prediction worker functions for multiprocessing.
"""

import pickle
from pathlib import Path
import numpy as np
import rasterio
from osgeo import gdal, gdalconst
from ml_pipeline.s3_utils import upload_file
from dataclasses import dataclass


@dataclass
class PredictorConfig:
    blocksize: int = 1024          # window size (pixels) – change for memory
    compress: str = "lzw"         # GTiff compression
    dtype: str = "uint8"          # output data type
    nodata: int = 255             # value for pixels we can't predict
    predictor: int = 2            # GDAL "predictor" tag for compression


def predict_single_cog_standalone(cog_url, model_path, basemap_date, pred_dir, save_local, cfg_dict, s3_path, upload_to_s3):
    """Standalone function for parallel COG prediction processing."""
    
    # Recreate config object from dict
    cfg = PredictorConfig(**cfg_dict)
    
    try:
        # Load model and feature manager
        with open(model_path, "rb") as f:
            bundle = pickle.load(f)
        model = bundle["model"]
        feature_manager = bundle.get("feature_manager")  # Load feature manager if available
        
        with rasterio.open(cog_url) as src:
            profile = src.profile.copy()
            profile.update(
                count=1,
                dtype=cfg.dtype,
                compress=cfg.compress,
                predictor=cfg.predictor,
                nodata=cfg.nodata,
            )

            # build output filename
            tile_id = Path(cog_url).stem
            out_path = Path(pred_dir) / f"{tile_id}.tiff"

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

                    # Apply feature engineering if configured
                    if feature_manager is not None:
                        X_full = feature_manager.extract_all_features(X)
                    else:
                        X_full = X

                    # mask nodata
                    valid_mask = ~np.any(
                        X[:, :4] == src.nodata, axis=1
                    )  # ignore temporal cols
                    preds = np.full(X.shape[0], cfg.nodata, dtype=cfg.dtype)
                    if valid_mask.any():
                        try:
                            y_pred = model.predict(X_full[valid_mask])
                            # map from consecutive to global indices
                            y_global = np.vectorize(
                                model.consecutive_to_global.get
                            )(y_pred)
                            preds[valid_mask] = y_global.astype(cfg.dtype)
                        except Exception as e:
                            print(f"Error predicting window {window} from {cog_url}: {e}")
                            continue

                    dst.write(preds.reshape(1, h, w), window=window)

            # Apply sieve filter
            try:
                _sieve_inplace(out_path, min_pixels=10)
            except Exception as e:
                print(f"Error applying sieve filter to {out_path}: {e}")

            # Upload to S3 if configured
            try:
                if upload_to_s3 and s3_path:
                    yyyy, mm = basemap_date.split("-")
                    remote_key = f"{s3_path}/{yyyy}/{mm}/{out_path.name}"
                    upload_file(out_path, remote_key)
            except Exception as e:
                print(f"Error uploading {out_path} to S3: {e}")

            # Delete local file if not saving locally
            if not save_local:
                out_path.unlink()
                return None

        return out_path

    except Exception as e:
        print(f"⚠️ Skipping Predicting this COG due to error: {cog_url} — {e}")
        return None


def _sieve_inplace(tif_path, min_pixels: int) -> None:
    """In-place GDAL sieve: remove connected components smaller than *min_pixels*."""
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