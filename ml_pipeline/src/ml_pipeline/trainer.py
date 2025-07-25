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
    f1_score,
)
from sklearn.utils.class_weight import compute_sample_weight
import rasterio
from rasterio.mask import mask
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import seaborn as sns
from sklearn.calibration import calibration_curve
from sklearn.metrics import roc_curve, auc, precision_recall_curve
from sklearn.preprocessing import label_binarize
from itertools import cycle
from shapely.geometry import mapping
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
        
        # Create diagnostics path
        diagnostics_path = self.run_dir / "model_diagnostics" / model_name
        diagnostics_path.mkdir(parents=True, exist_ok=True)
        
        model, metrics = self._fit_model(
            X,
            y,
            fids,
            dates,
            model_params or {},
            diagnostics_path,
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

    def _fit_model(self, X, y, feature_ids, dates, model_params, diagnostics_path: Path = None):
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
        
        # Check for class_weight parameter from hyperparameter tuning
        class_weight_setting = model_params.get('class_weight', cfg.class_weighting)
        
        if class_weight_setting == "balanced":
            sample_weight_tr = compute_sample_weight("balanced", y_tr)
            sample_weight_val = compute_sample_weight("balanced", y_val)

        # ---- choose objective ---------------------------------------
        params = dict(model_params)
        
        # Remove class_weight parameter as it's handled through sample weights
        params.pop('class_weight', None)
        
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
            
            # Manual cross-validation to properly handle sample weights
            cv_f1_scores = []
            
            if cfg.split_method == "feature":
                gkf = GroupKFold(n_splits=cfg.cv_folds)
                cv_splits = gkf.split(X_tr, y_tr, groups=fid_trval[tr_mask])
            else:
                from sklearn.model_selection import StratifiedKFold
                skf = StratifiedKFold(n_splits=cfg.cv_folds, shuffle=True, random_state=cfg.random_state)
                cv_splits = skf.split(X_tr, y_tr)
            
            for fold_idx, (train_idx, val_idx) in enumerate(cv_splits):
                # Split data for this fold
                X_fold_train, X_fold_val = X_tr[train_idx], X_tr[val_idx]
                y_fold_train, y_fold_val = y_tr[train_idx], y_tr[val_idx]
                
                # Compute sample weights for this fold if class weighting is enabled
                fold_sample_weight = None
                if class_weight_setting == "balanced":
                    fold_sample_weight = compute_sample_weight("balanced", y_fold_train)
                
                # Train model for this fold
                model_cv = XGBClassifier(**params_cv)
                model_cv.fit(X_fold_train, y_fold_train, sample_weight=fold_sample_weight, verbose=False)
                
                # Predict and compute F1-macro for this fold
                y_fold_pred = model_cv.predict(X_fold_val)
                fold_f1 = f1_score(y_fold_val, y_fold_pred, average='macro', zero_division=0)
                cv_f1_scores.append(fold_f1)
                
                print(f"  Fold {fold_idx + 1}/{cfg.cv_folds}: F1-macro = {fold_f1:.4f}")
            
            cv_scores = np.array(cv_f1_scores)
            print(f"CV F1-macro: {np.mean(cv_scores):.4f} ± {np.std(cv_scores):.4f}")

        # ---- final training ----------------------------------------
        print(f"Final training model with {X_tr.shape[0]} training samples and {X_val.shape[0]} validation samples")

        print("Label data (first 5 values): ", y_tr[:5])
        # Format covariate data to avoid scientific notation
        print("Covariate data (first 5 rows):")
        np.set_printoptions(suppress=True, precision=6, floatmode='fixed')
        print(X_tr[:5])
        np.set_printoptions()  # Reset to default
        model_final.fit(
            X_tr,
            y_tr,
            sample_weight=sample_weight_tr,
            eval_set=[(X_val, y_val)],
            sample_weight_eval_set=[sample_weight_val] if sample_weight_val is not None else None,
            verbose=False,
        )

        # ---- unseen TEST metrics -----------------------------------
        y_pred = model_final.predict(X_te)
        y_pred_proba = model_final.predict_proba(X_te) if hasattr(model_final, 'predict_proba') else None
        acc = accuracy_score(y_te, y_pred)
        f1_macro = f1_score(y_te, y_pred, average='macro', zero_division=0)
        pr, rc, f1, _ = precision_recall_fscore_support(
            y_te, y_pred, average=None, zero_division=0
        )

        metrics = {
            "accuracy": float(acc),
            "f1_macro": float(f1_macro),
            "precision": [float(v) for v in pr],
            "recall": [float(v) for v in rc],
            "f1": [float(v) for v in f1],
            "confusion_matrix": confusion_matrix(y_te, y_pred).tolist(),
            "classes_present": present,
            "cv_accuracy": cv_scores.tolist() if cv_scores is not None else None,
            "cv_f1_macro": cv_scores.tolist() if cv_scores is not None else None,
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

        # ---- generate model diagnostics (if path provided) ----------
        if diagnostics_path is not None:
            try:
                self._generate_all_diagnostics(
                    model_final, X_te, y_te, y_pred, y_pred_proba, 
                    present_classes, diagnostics_path
                )
            except Exception as e:
                logger.warning(f"Failed to generate diagnostics: {e}")

        # ---- stash encoders & mappings -----------------------------
        model_final.train_map = train_map
        model_final.year_encoder = le_year
        model_final.month_encoder = le_month
        model_final.global_class_to_int = global_class_to_int
        model_final.consecutive_to_global = consecutive_to_global
        
        # Store class_weight_setting for metadata
        model_final.class_weight_setting = class_weight_setting

        return model_final, metrics

    # ------------------------------------------------------------------
    #  model diagnostics helpers
    # ------------------------------------------------------------------

    def _plot_feature_importance(self, model, diagnostics_path: Path, feature_names=None):
        """Generate feature importance plots for XGBoost model."""
        try:
            booster = model.get_booster()
            importance_types = ['weight', 'gain', 'cover']
            
            # Get feature names - either from parameter or from feature manager
            if feature_names is None and self.feature_manager is not None:
                feature_names = self.feature_manager.get_all_feature_names()
            
            fig, axes = plt.subplots(1, 3, figsize=(18, 6))
            fig.suptitle('XGBoost Feature Importance', fontsize=16)
            
            for i, imp_type in enumerate(importance_types):
                ax = axes[i]
                
                if feature_names is not None:
                    # Get importance scores and map to feature names
                    scores = booster.get_score(importance_type=imp_type)
                    
                    # Create mapping from XGBoost feature names (f0, f1, etc.) to descriptive names
                    feature_mapping = {}
                    for xgb_name, score in scores.items():
                        # Extract feature index from XGBoost name (e.g., "f0" -> 0)
                        if xgb_name.startswith('f') and xgb_name[1:].isdigit():
                            idx = int(xgb_name[1:])
                            if idx < len(feature_names):
                                feature_mapping[feature_names[idx]] = score
                    
                    # Sort by importance and get top 20
                    sorted_features = sorted(feature_mapping.items(), key=lambda x: x[1], reverse=True)[:20]
                    
                    if sorted_features:
                        names, values = zip(*sorted_features)
                        y_pos = np.arange(len(names))
                        
                        ax.barh(y_pos, values)
                        ax.set_yticks(y_pos)
                        ax.set_yticklabels(names, fontsize=8)
                        ax.set_xlabel(f'{imp_type.title()} Importance')
                        ax.set_title(f'Feature Importance ({imp_type})')
                        ax.invert_yaxis()  # Show highest importance at top
                    else:
                        # Fallback to default XGBoost plot
                        xgb.plot_importance(booster, importance_type=imp_type, max_num_features=20, 
                                          ax=ax, title=f'Feature Importance ({imp_type})')
                else:
                    # Use default XGBoost plotting if no feature names available
                    xgb.plot_importance(booster, importance_type=imp_type, max_num_features=20, 
                                      ax=ax, title=f'Feature Importance ({imp_type})')
                
                ax.tick_params(axis='y', labelsize=8)
            
            plt.tight_layout()
            plt.savefig(diagnostics_path / 'feature_importance.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # Save feature importance scores as CSV with meaningful names
            importance_df = pd.DataFrame()
            for imp_type in importance_types:
                scores = booster.get_score(importance_type=imp_type)
                
                # Create DataFrame with meaningful feature names
                if feature_names is not None:
                    data = []
                    for xgb_name, score in scores.items():
                        if xgb_name.startswith('f') and xgb_name[1:].isdigit():
                            idx = int(xgb_name[1:])
                            if idx < len(feature_names):
                                data.append({
                                    'feature_name': feature_names[idx],
                                    'xgb_feature': xgb_name,
                                    f'{imp_type}_importance': score
                                })
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame(list(scores.items()), columns=['xgb_feature', f'{imp_type}_importance'])
                    df['feature_name'] = df['xgb_feature']  # Fallback to XGBoost names
                
                if importance_df.empty:
                    importance_df = df
                else:
                    merge_cols = ['feature_name', 'xgb_feature'] if 'xgb_feature' in df.columns else ['feature_name']
                    importance_df = importance_df.merge(df, on=merge_cols, how='outer')
            
            importance_df = importance_df.fillna(0).sort_values('gain_importance', ascending=False)
            importance_df.to_csv(diagnostics_path / 'feature_importance_scores.csv', index=False)
            
        except Exception as e:
            logger.warning(f"Failed to generate feature importance plots: {e}")

    def _plot_learning_curves(self, model, diagnostics_path: Path):
        """Generate learning curves from XGBoost training history."""
        try:
            results = model.evals_result()
            if not results:
                logger.warning("No evaluation results found for learning curves")
                return
                
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot training and validation curves
            for eval_set, metrics in results.items():
                for metric_name, values in metrics.items():
                    epochs = range(len(values))
                    label = f"{eval_set}_{metric_name}"
                    ax.plot(epochs, values, label=label, marker='o', markersize=2)
            
            ax.set_xlabel('Boosting Rounds')
            ax.set_ylabel('Metric Value')
            ax.set_title('XGBoost Learning Curves')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(diagnostics_path / 'learning_curves.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.warning(f"Failed to generate learning curves: {e}")

    def _plot_confusion_matrix(self, y_true, y_pred, class_names, diagnostics_path: Path):
        """Generate confusion matrix heatmap."""
        try:
            cm = confusion_matrix(y_true, y_pred)
            
            plt.figure(figsize=(10, 8))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                       xticklabels=class_names, yticklabels=class_names)
            plt.title('Confusion Matrix')
            plt.xlabel('Predicted Label')
            plt.ylabel('True Label')
            plt.tight_layout()
            plt.savefig(diagnostics_path / 'confusion_matrix.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.warning(f"Failed to generate confusion matrix: {e}")

    def _plot_roc_curves(self, y_true, y_pred_proba, class_names, diagnostics_path: Path):
        """Generate ROC curves for multiclass classification."""
        try:
            n_classes = len(class_names)
            
            if n_classes == 2:
                # Binary classification
                fpr, tpr, _ = roc_curve(y_true, y_pred_proba[:, 1])
                roc_auc = auc(fpr, tpr)
                
                plt.figure(figsize=(8, 6))
                plt.plot(fpr, tpr, color='darkorange', lw=2, 
                        label=f'ROC curve (AUC = {roc_auc:.2f})')
                plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
                plt.xlim([0.0, 1.0])
                plt.ylim([0.0, 1.05])
                plt.xlabel('False Positive Rate')
                plt.ylabel('True Positive Rate')
                plt.title('Receiver Operating Characteristic')
                plt.legend(loc="lower right")
            else:
                # Multiclass classification
                y_true_bin = label_binarize(y_true, classes=range(n_classes))
                
                fpr = dict()
                tpr = dict()
                roc_auc = dict()
                
                plt.figure(figsize=(10, 8))
                colors = cycle(['aqua', 'darkorange', 'cornflowerblue', 'red', 'green', 'purple', 'brown'])
                
                for i, color in zip(range(n_classes), colors):
                    fpr[i], tpr[i], _ = roc_curve(y_true_bin[:, i], y_pred_proba[:, i])
                    roc_auc[i] = auc(fpr[i], tpr[i])
                    plt.plot(fpr[i], tpr[i], color=color, lw=2,
                            label=f'{class_names[i]} (AUC = {roc_auc[i]:.2f})')
                
                plt.plot([0, 1], [0, 1], 'k--', lw=2)
                plt.xlim([0.0, 1.0])
                plt.ylim([0.0, 1.05])
                plt.xlabel('False Positive Rate')
                plt.ylabel('True Positive Rate')
                plt.title('ROC Curves - Multiclass')
                plt.legend(loc="lower right")
            
            plt.tight_layout()
            plt.savefig(diagnostics_path / 'roc_curves.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.warning(f"Failed to generate ROC curves: {e}")

    def _plot_precision_recall_curves(self, y_true, y_pred_proba, class_names, diagnostics_path: Path):
        """Generate precision-recall curves."""
        try:
            n_classes = len(class_names)
            
            if n_classes == 2:
                # Binary classification
                precision, recall, _ = precision_recall_curve(y_true, y_pred_proba[:, 1])
                
                plt.figure(figsize=(8, 6))
                plt.plot(recall, precision, color='darkorange', lw=2)
                plt.xlabel('Recall')
                plt.ylabel('Precision')
                plt.title('Precision-Recall Curve')
                plt.grid(True, alpha=0.3)
            else:
                # Multiclass classification
                y_true_bin = label_binarize(y_true, classes=range(n_classes))
                
                plt.figure(figsize=(10, 8))
                colors = cycle(['aqua', 'darkorange', 'cornflowerblue', 'red', 'green', 'purple', 'brown'])
                
                for i, color in zip(range(n_classes), colors):
                    precision, recall, _ = precision_recall_curve(y_true_bin[:, i], y_pred_proba[:, i])
                    plt.plot(recall, precision, color=color, lw=2, label=f'{class_names[i]}')
                
                plt.xlabel('Recall')
                plt.ylabel('Precision')
                plt.title('Precision-Recall Curves - Multiclass')
                plt.legend(loc="lower left")
                plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(diagnostics_path / 'precision_recall_curves.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.warning(f"Failed to generate precision-recall curves: {e}")

    def _plot_calibration(self, y_true, y_pred_proba, class_names, diagnostics_path: Path):
        """Generate calibration plots for probability calibration."""
        try:
            n_classes = len(class_names)
            
            if n_classes == 2:
                # Binary classification
                fraction_pos, mean_pred = calibration_curve(y_true, y_pred_proba[:, 1], n_bins=10)
                
                plt.figure(figsize=(8, 6))
                plt.plot(mean_pred, fraction_pos, "s-", label="Model")
                plt.plot([0, 1], [0, 1], "k:", label="Perfectly calibrated")
                plt.xlabel('Mean Predicted Probability')
                plt.ylabel('Fraction of Positives')
                plt.title('Calibration Plot')
                plt.legend()
                plt.grid(True, alpha=0.3)
            else:
                # Multiclass - plot for each class vs rest
                fig, axes = plt.subplots(2, (n_classes + 1) // 2, figsize=(15, 10))
                axes = axes.flatten() if n_classes > 2 else [axes]
                
                for i in range(n_classes):
                    y_binary = (y_true == i).astype(int)
                    fraction_pos, mean_pred = calibration_curve(y_binary, y_pred_proba[:, i], n_bins=10)
                    
                    ax = axes[i] if i < len(axes) else plt.gca()
                    ax.plot(mean_pred, fraction_pos, "s-", label=f"{class_names[i]}")
                    ax.plot([0, 1], [0, 1], "k:", label="Perfect")
                    ax.set_xlabel('Mean Predicted Probability')
                    ax.set_ylabel('Fraction of Positives')
                    ax.set_title(f'Calibration - {class_names[i]}')
                    ax.legend()
                    ax.grid(True, alpha=0.3)
                
                # Hide unused subplots
                for i in range(n_classes, len(axes)):
                    axes[i].set_visible(False)
            
            plt.tight_layout()
            plt.savefig(diagnostics_path / 'calibration_plot.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.warning(f"Failed to generate calibration plots: {e}")

    def _generate_shap_plots(self, model, X_sample, diagnostics_path: Path, max_samples=1000):
        """Generate SHAP analysis plots."""
        try:
            # Limit sample size for SHAP analysis
            if len(X_sample) > max_samples:
                sample_idx = np.random.choice(len(X_sample), max_samples, replace=False)
                X_shap = X_sample[sample_idx]
            else:
                X_shap = X_sample
            
            # Create SHAP explainer
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_shap)
            
            # Summary plot
            plt.figure(figsize=(10, 8))
            if isinstance(shap_values, list):  # Multiclass
                shap.summary_plot(shap_values[1], X_shap, show=False)  # Use class 1 for binary, or first class
            else:
                shap.summary_plot(shap_values, X_shap, show=False)
            plt.tight_layout()
            plt.savefig(diagnostics_path / 'shap_summary.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            # Feature importance plot
            plt.figure(figsize=(10, 6))
            if isinstance(shap_values, list):
                shap.summary_plot(shap_values[1], X_shap, plot_type="bar", show=False)
            else:
                shap.summary_plot(shap_values, X_shap, plot_type="bar", show=False)
            plt.tight_layout()
            plt.savefig(diagnostics_path / 'shap_importance.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            logger.warning(f"Failed to generate SHAP plots: {e}")

    def _generate_all_diagnostics(self, model, X_test, y_test, y_pred, y_pred_proba, 
                                 class_names, diagnostics_path: Path):
        """Generate all diagnostic plots and save them."""
        print("Generating model diagnostics...")
        
        # Feature importance plots
        self._plot_feature_importance(model, diagnostics_path)
        
        # Learning curves
        self._plot_learning_curves(model, diagnostics_path)
        
        # Confusion matrix
        self._plot_confusion_matrix(y_test, y_pred, class_names, diagnostics_path)
        
        # ROC curves
        if y_pred_proba is not None:
            self._plot_roc_curves(y_test, y_pred_proba, class_names, diagnostics_path)
            self._plot_precision_recall_curves(y_test, y_pred_proba, class_names, diagnostics_path)
            self._plot_calibration(y_test, y_pred_proba, class_names, diagnostics_path)
        
        # SHAP analysis (use a sample of training data)
        try:
            # Use the test set for SHAP analysis
            self._generate_shap_plots(model, X_test, diagnostics_path)
        except Exception as e:
            logger.warning(f"SHAP analysis failed: {e}")
        
        print(f"Diagnostics saved to: {diagnostics_path}")

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
        
        # Save hyperparameters and configuration to diagnostics folder
        class_weight_setting = getattr(model, 'class_weight_setting', None)
        self._save_model_metadata(name, model, meta, class_weight_setting)
        
        self.last_saved_model_path = path
        return path

    def _save_model_metadata(self, model_name: str, model, meta: dict, class_weight_setting=None):
        """Save hyperparameters and configuration files."""
        try:
            diagnostics_path = self.run_dir / "model_diagnostics" / model_name
            diagnostics_path.mkdir(parents=True, exist_ok=True)
            
            # Get model hyperparameters
            hyperparameters = model.get_params()
            
            # Training configuration
            training_config = {
                "split_method": self.cfg.split_method,
                "test_fraction": self.cfg.test_fraction,
                "val_fraction": self.cfg.val_fraction,
                "random_state": self.cfg.random_state,
                "early_stopping_rounds": self.cfg.early_stopping_rounds,
                "class_weighting": class_weight_setting or self.cfg.class_weighting,
                "cv_folds": self.cfg.cv_folds,
                "class_order": list(self.cfg.class_order),
                "cache_dir": str(self.cfg.cache_dir) if self.cfg.cache_dir else None,
            }
            
            # Add feature engineering config if available
            if self.feature_manager is not None:
                training_config["feature_engineering"] = self.feature_manager.get_config()
            
            # Save hyperparameters as JSON
            with open(diagnostics_path / "hyperparameters.json", "w") as f:
                json.dump(hyperparameters, f, indent=2, default=str)
            
            # Save training configuration as JSON
            with open(diagnostics_path / "training_config.json", "w") as f:
                json.dump(training_config, f, indent=2, default=str)
            
            # Save human-readable summary
            summary_lines = [
                f"Model: {model_name}",
                f"Description: {meta.get('description', 'N/A')}",
                f"Saved: {meta['saved_utc']}",
                "",
                "=== XGBoost Hyperparameters ===",
            ]
            
            # Add key hyperparameters
            key_params = ['n_estimators', 'max_depth', 'learning_rate', 'subsample', 
                         'colsample_bytree', 'random_state', 'objective']
            for param in key_params:
                if param in hyperparameters:
                    summary_lines.append(f"{param}: {hyperparameters[param]}")
            
            summary_lines.extend([
                "",
                "=== Training Configuration ===",
                f"Split method: {training_config['split_method']}",
                f"Test fraction: {training_config['test_fraction']}",
                f"Validation fraction: {training_config['val_fraction']}",
                f"CV folds: {training_config['cv_folds']}",
                f"Class weighting: {training_config['class_weighting']}",
                f"Early stopping rounds: {training_config['early_stopping_rounds']}",
                "",
                "=== Feature Engineering ===",
            ])
            
            if self.feature_manager is not None:
                summary_lines.append(f"Feature extractors: {len(self.feature_manager.feature_extractors)}")
                for extractor in self.feature_manager.feature_extractors:
                    summary_lines.append(f"  - {extractor.__class__.__name__}")
                summary_lines.append(f"Total features: {len(meta.get('feature_names', []))}")
            else:
                summary_lines.append("No feature engineering applied")
            
            with open(diagnostics_path / "model_summary.txt", "w") as f:
                f.write("\n".join(summary_lines))
            
            print(f"Model metadata saved to: {diagnostics_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save model metadata: {e}")

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
