"""
ml_pipeline.trainer
~~~~~~~~~~~~~~~~~~~
Fit an XGBoost land-cover classifier from pixel samples delivered by
ml_pipeline.extractor.TitilerExtractor.

Dependencies
------------
pip install xgboost scikit-learn numpy
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import pickle

import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
)

# ---------------------------------------------------------------------------
#  Config & default hyper-parameters
# ---------------------------------------------------------------------------


@dataclass
class TrainerConfig:
    split_method: str = "feature"   # "feature" or "pixel"
    test_fraction: float = 0.2
    random_state: int = 42
    early_stopping_rounds: int = 10
    class_order: tuple[str, ...] = (
        "Forest",
        "Non-Forest",
        "Cloud",
        "Shadow",
        "Water",
    )


# ---------------------------------------------------------------------------
#  Model training class
# ---------------------------------------------------------------------------


class ModelTrainer:
    """
    Parameters
    ----------
    extractor
        An instance of TitilerExtractor (already written).
    out_dir
        Folder where *.pkl files will be stored.
    cfg
        TrainerConfig with default hyper-parameters.
    """

    def __init__(
        self,
        extractor,
        out_dir: str | Path = "models",
        cfg: TrainerConfig = TrainerConfig(),
    ):
        self.extractor = extractor
        self.cfg = cfg
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.last_saved_model_path = None  # Track the last saved model path

    # ------------------------------------------------------------------
    #  Public entry point
    # ------------------------------------------------------------------

    def train(
        self,
        training_sets: list[dict],
        model_name: str = "landcover_xgb",
        model_description: str = "",
        model_params: dict | None = None,
    ) -> tuple[Path, dict]:
        """
        Parameters
        ----------
        training_sets
            List of dicts, each with keys:
              * 'gdf'           – GeoPandas GeoDataFrame with polygons
              * 'basemap_date'  – string "YYYY-MM"  (optional, used for year/month features)
        """
        print("[ 0%] Extracting pixels…")
        X, y, fids, dates = self._assemble_arrays(training_sets)

        print("[45%] Fitting XGBoost model…")
        model, metrics = self._fit_model(X, y, fids, dates, model_params or {})

        print("[90%] Saving model to disk…")
        path = self._save_model(model_name, model_description, model)
        print(f"[100%] Done ➜ {path}")

        return path, metrics

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _assemble_arrays(self, training_sets):
        xs, ys, fids, ds = [], [], [], []
        for ts in training_sets:
            gdf = ts["gdf"]
            X, y, fid = self.extractor.extract_pixels(gdf)
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

    def _fit_model(self, X, y, feature_ids, dates, model_params):
        cfg = self.cfg

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

        # ---- temporal features -------------------------------------------
        years = np.array([d.split("-")[0] if d else "" for d in dates])
        months = np.array([int(d.split("-")[1]) if d else 0 for d in dates])

        le_year = LabelEncoder().fit(years)
        le_month = LabelEncoder().fit(months)

        # If using dates - add them to the feature set
        # X_feat = np.column_stack(
        #     [X, le_year.transform(years), le_month.transform(months)]
        # )

        # Not using dates during model training
        X_feat = X

        # ---- train/test split --------------------------------------------
        if cfg.split_method == "feature":
            uniq_f, uniq_idx = np.unique(feature_ids, return_index=True)
            strat = y_enc[uniq_idx]
            train_f, test_f = train_test_split(
                uniq_f,
                test_size=cfg.test_fraction,
                random_state=cfg.random_state,
                stratify=strat,
            )
            tr_mask = np.isin(feature_ids, train_f)
            te_mask = np.isin(feature_ids, test_f)
            X_tr, X_te, y_tr, y_te = (
                X_feat[tr_mask],
                X_feat[te_mask],
                y_enc[tr_mask],
                y_enc[te_mask],
            )
        else:  # pixel-level split
            X_tr, X_te, y_tr, y_te = train_test_split(
                X_feat,
                y_enc,
                test_size=cfg.test_fraction,
                random_state=cfg.random_state,
            )

        # ---- choose proper objective -------------------------------------
        params = dict(model_params)  # copy
        if len(present) > 2:
            params["num_class"] = len(present)
            params["objective"] = "multi:softmax"
        else:
            params["objective"] = "binary:logistic"
            params.pop("num_class", None)

        params.setdefault("random_state", cfg.random_state)
        params.setdefault("early_stopping_rounds", cfg.early_stopping_rounds)

        # ---- fit ---------------------------------------------------------
        model = XGBClassifier(**params)
        model.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=True)

        # ---- metrics -----------------------------------------------------
        y_pred = model.predict(X_te)
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
        }

        # keep encoders on the model object
        model.train_map = train_map
        model.year_encoder = le_year
        model.month_encoder = le_month
        model.global_class_to_int = global_class_to_int
        model.consecutive_to_global = consecutive_to_global

        return model, metrics

    def _save_model(self, name, desc, model):
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = self.out_dir / f"{name}_{ts}.pkl"
        meta = {"name": name, "description": desc, "saved_utc": ts}

        with open(path, "wb") as f:
            pickle.dump({"meta": meta, "model": model}, f)

        self.last_saved_model_path = path  # Store the path
        return path

    @property
    def saved_model_path(self):
        """Get the path to the most recently saved model.
        
        Returns:
            Path: Path to the last saved model file, or None if no model has been saved yet.
        """
        return self.last_saved_model_path