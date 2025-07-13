"""
ml_pipeline.trainer
~~~~~~~~~~~~~~~~~~~
Fit an XGBoost land‑cover classifier from pixel samples delivered by
ml_pipeline.extractor.TitilerExtractor.

New in this version
-------------------
* **Data/fit decoupling** – you can now run `prepare_training_data()` once to
  extract & cache pixel arrays (`*.npz`) and then call `fit_prepared_data()`
  repeatedly without hitting Titiler again.
* Convenience `train()` still exists and simply chains the two steps.

Dependencies
------------
``pip install xgboost scikit-learn numpy``
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import pickle
import logging
import hashlib
import json
import io
import numpy as np
import comet_ml
from xgboost import XGBClassifier
import xgboost as xgb
import shap
from sklearn.model_selection import (
    train_test_split,
    GroupKFold,
    cross_val_score,
)
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
)
from sklearn.utils.class_weight import compute_sample_weight
import rasterio
from rasterio.mask import mask
import pandas as pd
from .feature_engineering import FeatureManager, FeatureExtractor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import os
from dotenv import load_dotenv
load_dotenv()

# 
# comet_ml.login(api_key=os.getenv("COMETML_API"),
#                project_name="choco-forest-watch",
#                workspace="lukembrowne")


# ---------------------------------------------------------------------------
#  Config & default hyper‑parameters
# ---------------------------------------------------------------------------


@dataclass
class TrainerConfig:
    # Splitting strategy
    split_method: str = "feature"  # "feature" or "pixel"
    test_fraction: float = 0.2      # portion held out as TEST (never seen)
    val_fraction: float = 0.2      # portion of training set for VAL/early‑stop

    # Model and training
    random_state: int = 42
    early_stopping_rounds: int = 20

    # Class imbalance
    class_weighting: str | None = None  # None or "balanced"

    # Cross‑validation
    cv_folds: int = 5   # set to 1 to disable

    # Class order (fixed index mapping)
    class_order: tuple[str, ...] = (
        "Forest",
        "Non-Forest",
        "Cloud",
        "Shadow",
        "Water",
        "Haze",
        "Sensor Error"
    )

    # Data cache directory (optional)
    cache_dir: Path | str | None = "data_cache"  # where *.npz arrays live
    
    # Feature engineering configuration
    feature_extractors: list[FeatureExtractor] | None = None  # List of feature extractors to use
    
    def create_feature_manager(self) -> FeatureManager | None:
        """Create a FeatureManager from the configured extractors.
        
        Returns
        -------
        FeatureManager | None
            FeatureManager instance if extractors are configured, None otherwise.
        """
        if self.feature_extractors:
            return FeatureManager(self.feature_extractors)
        return None

# ---------------------------------------------------------------------------
#  Model training class
# ---------------------------------------------------------------------------


class ModelTrainer:
    """Train an XGBoost classifier with optional caching of extracted arrays.

    Workflow options
    ----------------
    1. **One‑shot** (old behaviour)
       ```python
       trainer = ModelTrainer(extractor)
       trainer.train(training_sets, "model_name")
       ```
    2. **Decoupled**
       ```python
       # First run once – heavy I/O
       npz = trainer.prepare_training_data(training_sets, "arrays_2022_02.npz")
       # Iterate experiments quickly
       trainer.fit_prepared_data(npz, model_name="runA", model_params={...})
       trainer.fit_prepared_data(npz, model_name="runB", model_params={...})
       ```
    """

    # ------------------------------------------------------------------
    #  construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        extractor,
        run_dir: str | Path = "models",
        cfg: TrainerConfig = TrainerConfig(),
        feature_manager: FeatureManager | None = None,
    ):
        self.extractor = extractor
        self.cfg = cfg
        self.run_dir = Path(run_dir)
        # Use provided feature manager or create from config
        self.feature_manager = feature_manager or cfg.create_feature_manager()
        self.last_saved_model_path: Path | None = None

        # ensure cache dir exists
        if self.cfg.cache_dir:
            Path(self.cfg.cache_dir).mkdir(parents=True, exist_ok=True)


    # ------------------------------------------------------------------
    #  PUBLIC API – STEP 1: extract & cache pixel arrays
    # ------------------------------------------------------------------

    def prepare_training_data(
        self,
        training_sets: list[dict],
        cache_name: str | Path | None = None,
        overwrite: bool = False,
    ) -> Path:
        """Extract pixels, save them to a ``.npz`` file, and return its path.

        If *cache_name* is **None** the file name is an SHA‑1 hash of the
        training‑set metadata so the same inputs always map to the same cache
        file.
        """

        if cache_name is None:
            print("Generating cache name since none provided...")
            meta_hash = hashlib.sha1(json.dumps([
                {"len": len(ts["gdf"]), "date": ts.get("basemap_date", "")}
                for ts in training_sets
            ], sort_keys=True).encode()).hexdigest()[:10]
            cache_name = f"train_{meta_hash}.npz"

        cache_path = Path(self.cfg.cache_dir) / cache_name
        if cache_path.exists() and not overwrite:
            print(f"Using cached arrays → {cache_path}")
            return cache_path

        print("Assembling pixel arrays...")
        X, y, fids, dates = self._assemble_arrays(training_sets)
        np.savez_compressed(cache_path, X=X, y=y, fids=fids, dates=dates)
        print(f"Pixel arrays cached at {cache_path}")
        return cache_path

    # ------------------------------------------------------------------
    #  PUBLIC API – STEP 2: fit from cached arrays
    # ------------------------------------------------------------------

    def fit_prepared_data(
        self,
        npz_path: str | Path,
        model_name: str,
        model_description: str = "",
        model_params: dict | None = None,
    ) -> tuple[Path, dict]:
        """Load arrays from *npz_path* and train a model."""
        print("Loading pixel arrays...")
        data = np.load(npz_path, allow_pickle=True)
        X, y, fids, dates = data["X"], data["y"], data["fids"], data["dates"]

        print("Fitting XGBoost model...")
        model, metrics = self._fit_model(
            X,
            y,
            fids,
            dates,
            model_params or {},
        )

        print("Saving model...")
        path = self._save_model(model_name, model_description, model)
        print(f"Done ➜ {path}")
        return path, metrics

    # ------------------------------------------------------------------
    #  INTERNAL helpers – assemble arrays
    # ------------------------------------------------------------------

    def _assemble_arrays(self, training_sets):
        xs, ys, fids, ds = [], [], [], []
        for ts in training_sets:
            gdf = ts["gdf"]

            # Extract pixels
            X, y, fid = self.extractor.extract_pixels(gdf)
            
            # Apply feature engineering if configured
            if self.feature_manager is not None:
                print(f"Applying feature engineering: {X.shape[1]} base bands -> ", end="")
                X = self.feature_manager.extract_all_features(X)
                print(f"{X.shape[1]} total features")
            
            xs.append(X)
            ys.append(y)
            fids.append(fid)
            ds.append(
                np.full_like(fid, ts.get("basemap_date", ""), dtype=object)
            )

        return (
            np.vstack(xs),
            np.concatenate(ys),
            np.concatenate(fids),
            np.concatenate(ds),
        )

    # ------------------------------------------------------------------
    #  INTERNAL helpers – core training routine (unchanged logic)
    # ------------------------------------------------------------------

    def _fit_model(self, X, y, feature_ids, dates, model_params):
        cfg = self.cfg

        # # Get the current experiment
        # experiment = comet_ml.Experiment    (project_name="choco-forest-watch",
        #                                  workspace="lukembrowne")

         # ---- encode class labels -----------------------------------------
        desired = cfg.class_order
        present = np.unique(y).tolist()
        
        # Create global class mapping (fixed indices)
        global_class_to_int = {class_name: idx for idx, class_name in enumerate(desired)}
        
        # Create mapping for XGBoost that uses consecutive integers
        present_classes = [c for c in desired if c in present]
        train_map = {class_name: idx for idx, class_name in enumerate(present_classes)}
        
        # Create reverse mapping from consecutive to global indices
        consecutive_to_global = {
            train_map[class_name]: global_class_to_int[class_name]
            for class_name in present_classes
        }

        # Transform labels using consecutive integers for training
        y_enc = np.array([train_map[c] for c in y])
        
        # Store mappings on the config for later use
        cfg.global_class_to_int = global_class_to_int
        cfg.consecutive_to_global = consecutive_to_global

        # ---- optional temporal features ------------------------------
        years = np.array([d.split("-")[0] if d else "" for d in dates])
        months = np.array([int(d.split("-")[1]) if d else 0 for d in dates])
        le_year, le_month = LabelEncoder().fit(years), LabelEncoder().fit(months)
        X_feat = X  # placeholder – add cyclical encodings if desired

        # ---- outer TEST split ---------------------------------------
        if cfg.split_method == "feature":
            uniq_f, uniq_idx = np.unique(feature_ids, return_index=True)
            strat = y_enc[uniq_idx]
            trainval_f, test_f = train_test_split(
                uniq_f,
                test_size=cfg.test_fraction,
                random_state=cfg.random_state,
                stratify=strat,
            )
            test_mask = np.isin(feature_ids, test_f)
            trval_mask = np.isin(feature_ids, trainval_f)
        else:
            trval_mask, test_mask = train_test_split(
                np.arange(len(y_enc)),
                test_size=cfg.test_fraction,
                random_state=cfg.random_state,
                stratify=y_enc,
            )

        X_trval, y_trval, fid_trval = (
            X_feat[trval_mask],
            y_enc[trval_mask],
            feature_ids[trval_mask],
        )
        X_te, y_te = X_feat[test_mask], y_enc[test_mask]
        feature_ids_te = feature_ids[test_mask]  # Feature IDs for test set
        dates_te = dates[test_mask]  # Dates for test set

        # Save test feature IDs for later reference for running benchmarks
        test_ids_dir = self.run_dir / "feature_ids_testing"
        
        # Create DataFrame with test IDs, dates, and class labels
        test_df = pd.DataFrame({
            'feature_id': feature_ids_te,
            'date': dates_te,
            'class_label': [present_classes[label] for label in y_te]  # Convert encoded labels back to class names
        })

        # Subset to only unique rows
        test_df = test_df.drop_duplicates()
        
        # Save to file
        test_df.to_csv(test_ids_dir / f"test_features_{dates_te[0]}.csv", index=False)
        print(f"Saved test feature IDs to {test_ids_dir}/test_features_{dates_te[0]}.csv")

        # ---- inner VAL split ----------------------------------------
        if cfg.split_method == "feature":
            uniq_tr_f, uniq_tr_idx = np.unique(fid_trval, return_index=True)
            strat_tr = y_trval[uniq_tr_idx]
            train_f, val_f = train_test_split(
                uniq_tr_f,
                test_size=cfg.val_fraction,
                random_state=cfg.random_state,
                stratify=strat_tr,
            )
            tr_mask = np.isin(fid_trval, train_f)
            val_mask = np.isin(fid_trval, val_f)
        else:
            tr_mask, val_mask = train_test_split(
                np.arange(len(y_trval)),
                test_size=cfg.val_fraction,
                random_state=cfg.random_state,
                stratify=y_trval,
            )

        X_tr, y_tr = X_trval[tr_mask], y_trval[tr_mask] # Used for training
        X_val, y_val = X_trval[val_mask], y_trval[val_mask] # Used for validation during training

        # ---- class imbalance ----------------------------------------
        sample_weight_tr = sample_weight_val = None
        if cfg.class_weighting == "balanced":
            sample_weight_tr = compute_sample_weight("balanced", y_tr)
            sample_weight_val = compute_sample_weight("balanced", y_val)

        # ---- choose objective ---------------------------------------
        params = dict(model_params)
        if len(present) > 2:
            params["num_class"] = len(present)
            params["objective"] = "multi:softmax"
        else:
            params["objective"] = "binary:logistic"
            params.pop("num_class", None)
        params.setdefault("random_state", cfg.random_state)
        params.setdefault("early_stopping_rounds", cfg.early_stopping_rounds)



        # Log Pandas Profile Train
        # experiment.log_dataframe_profile(X_tr, "pandas_profiling_train", minimal=True, log_raw_dataframe=False)


        # ---- models for CV and final fit ----------------------------
        model_final = XGBClassifier(**params)
        cv_scores = None
        if cfg.cv_folds > 1:
            print(f"Cross-validating model with {cfg.cv_folds} folds")
            params_cv = dict(params)
            params_cv.pop("early_stopping_rounds", None)  # disable ES inside CV
            model_cv = XGBClassifier(**params_cv)
            if cfg.split_method == "feature":
                gkf = GroupKFold(n_splits=cfg.cv_folds)
                cv_scores = cross_val_score(
                    model_cv,
                    X_tr,
                    y_tr,
                    groups=fid_trval[tr_mask],
                    cv=gkf,
                    scoring="accuracy",
                    n_jobs=-1,
                )
            else:
                cv_scores = cross_val_score(
                    model_cv,
                    X_tr,
                    y_tr,
                    cv=cfg.cv_folds,
                    scoring="accuracy",
                    n_jobs=-1,
                )

        # ---- final training ----------------------------------------
        print(f"Final training model with {X_tr.shape[0]} training samples and {X_val.shape[0]} validation samples")

        print("Label data (first 5 values): ", y_tr[:5])
        print("Covariate data (first 5 rows):\n", X_tr[:5])
        model_final.fit(
            X_tr,
            y_tr,
            sample_weight=sample_weight_tr,
            eval_set=[(X_val, y_val)],
            sample_weight_eval_set=[sample_weight_val] if sample_weight_val is not None else None,
            verbose=True,
        )

        # ---- unseen TEST metrics -----------------------------------
        y_pred = model_final.predict(X_te)
        acc = accuracy_score(y_te, y_pred)
        pr, rc, f1, _ = precision_recall_fscore_support(
            y_te, y_pred, average=None, zero_division=0
        )

        metrics = {
            "accuracy": float(acc),
            "precision": [float(v) for v in pr],
            "recall": [float(v) for v in rc],
            "f1": [float(v) for v in f1],
            "confusion_matrix": confusion_matrix(y_te, y_pred).tolist(),
            "classes_present": present,
            "cv_accuracy": cv_scores.tolist() if cv_scores is not None else None,
        }

        # Save model to comet
       # experiment.log_model('model_final', 'models/model_final.pkl')

        # #feature importance plot
        # booster = model_final.get_booster()
        # importances = booster.get_score(importance_type='weight')
        # print(importances)
        # for key in importances:
        #     experiment.log_other(key, importances[key])
            
        # experiment.log_asset_data(importances)

        # # Create figure and save to BytesIO buffer
        # ax = xgb.plot_importance(booster)
        # buf = io.BytesIO()
        # ax.figure.savefig(buf, format='png')
        # buf.seek(0)
        # experiment.log_image(buf, name='feature_importance')

        # # Log the confusion matrix
        # experiment.log_confusion_matrix(y_te, y_pred, labels=present)

        # # Log scalar metrics
        # experiment.log_metric("accuracy", metrics["accuracy"])
        # experiment.log_metric("cv_accuracy_mean", sum(metrics["cv_accuracy"]) / len(metrics["cv_accuracy"]))

        # # Log class-wise precision, recall, f1 with per-class index
        # for i, class_name in enumerate(metrics["classes_present"]):
        #     experiment.log_metric(f"precision_{class_name}", metrics["precision"][i])
        #     experiment.log_metric(f"recall_{class_name}", metrics["recall"][i])
        #     experiment.log_metric(f"f1_{class_name}", metrics["f1"][i])

        # # Log unique dates
        # experiment.log_metric("dates", list(set(dates)))

        #### Log SHAP values

        # model_bytearray = booster.save_raw()[4:]
        # def myfunc(self=None):
        #     return model_bytearray
        # booster.save_raw = myfunc

        # explainer = shap.TreeExplainer(booster)

        # shap_values = explainer.shap_values(X_tr)
        # shap.initjs()
        # feature_names = y_tr


        # # log decision plot
        # shap.decision_plot(explainer.expected_value, shap_values, feature_names, show=False)
        # plt.savefig('decision_plot.png')
        # plt.clf()

        # # log Summary plot
        # shap.summary_plot(shap_values, feature_names, show=False)
        # plt.savefig('summary_plot.png')


        # End experiment
        # experiment.end()


        # ---- stash encoders & mappings -----------------------------
        model_final.train_map = train_map
        model_final.year_encoder = le_year
        model_final.month_encoder = le_month
        model_final.global_class_to_int = global_class_to_int
        model_final.consecutive_to_global = consecutive_to_global

        return model_final, metrics

    # ------------------------------------------------------------------
    #  persistence helpers
    # ------------------------------------------------------------------

    def _save_model(self, name, desc, model):
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = self.run_dir / "saved_models" / f"{name}.pkl"
        
        # Include feature engineering metadata
        meta = {"name": name, "description": desc, "saved_utc": ts}
        if self.feature_manager is not None:
            meta["feature_config"] = self.feature_manager.get_config()
            meta["feature_names"] = self.feature_manager.get_all_feature_names()
        
        with open(path, "wb") as f:
            pickle.dump({"meta": meta, "model": model, "feature_manager": self.feature_manager}, f)
        self.last_saved_model_path = path
        return path

    @property
    def saved_model_path(self) -> Path | None:
        """Return path of the most recently saved model, if any."""
        return self.last_saved_model_path

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
                try:
                    with rasterio.open(cog) as src:
                        mask_geom = wgs84_geom if src.crs.to_epsg() == 4326 else webm_geom
                        try:
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
                        except rasterio.errors.RasterioIOError as e:
                            print(f"Warning: Failed to read data from {cog}: {str(e)}")
                            continue
                except Exception as e:
                    print(f"Warning: Failed to open {cog}: {str(e)}")
                    continue

        if not pixels:
            raise ValueError("No valid pixels were extracted from any of the input files")

        print("Pixels :", sum(len(p) for p in pixels))
        print("Labels :", len(labels))
        print("Fids   :", len(fids))
        return np.vstack(pixels), np.array(labels), np.array(fids)
