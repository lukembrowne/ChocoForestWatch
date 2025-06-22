from __future__ import annotations

from pathlib import Path
from typing import List, Dict
import logging

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report

from ml_pipeline.extractor import TitilerExtractor
from ml_pipeline.polygon_loader import load_training_polygons
from ml_pipeline.benchmark_metrics_io import (
    save_metrics_csv,
    show_accuracy_table,
    plot_accuracy,
)
from ml_pipeline.db_utils import get_db_connection
from ml_pipeline.raster_utils import pixels_to_labels, extract_pixels_with_missing

# Suppress boto3 logging
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('s3transfer').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

class BenchmarkTester:
    """Run inference against a (raster) benchmark dataset and capture metrics.
    """

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    def __init__(
        self,
        base_url: str,
        collection: str,
        year: str,
        project_id: int,
        *,
        band_indexes: List[int] | None = None,
        engine=None,
        run_id: str | None = None,
        test_features_dir: str | Path | None = None,
    ) -> None:
        """Parameters
        ----------
        base_url
            Root of the TiTiler service (e.g. ``http://localhost:8083``).
        collection
            STAC collection ID of the **benchmark raster** you want to evaluate
            (e.g. ``nicfi-pred-composite-2022`` or Hansen tree-cover, etc.).
        year
            Four-digit year to evaluate (e.g. ``"2022"``).
        project_id
            Training-polygon project ID – we re-use the same polygons for testing.
        band_indexes
            1-based band indexes to read from each COG (defaults to ``[1]``).
        engine
            Optional SQLAlchemy engine. If ``None`` we'll open one with
            :pyfunc:`ml_pipeline.db_utils.get_db_connection`.
        run_id
            If supplied, will look for held-out validation CSVs below
            ``runs/<run_id>/feature_ids_testing``.
        test_features_dir
            Override for the directory containing the held-out CSVs. Takes
            precedence over *run_id*.
        """
        self.base_url = base_url.rstrip("/")
        self.collection = collection
        self.year = str(year)
        self.project_id = project_id
        self.band_indexes = band_indexes or [1]
        self.engine = engine or get_db_connection()
        self.run_id = run_id

        # Where are the held-out feature-ID CSVs?
        if test_features_dir is not None:
            self.test_features_dir = Path(test_features_dir)
        elif run_id is not None:
            # Look for runs directory in ml_pipeline folder (go up from current location)
            ml_pipeline_dir = Path(__file__).parent.parent.parent  # Go up from src/ml_pipeline to ml_pipeline
            self.test_features_dir = ml_pipeline_dir / "runs" / run_id / "feature_ids_testing"
        else:
            self.test_features_dir = None

        self.extractor = TitilerExtractor(
            base_url=self.base_url, collection=self.collection, band_indexes=self.band_indexes
        )

        # Quick fail-fast – does the collection exist?
        _cogs = self.extractor.get_all_cog_urls(collection)
        if len(_cogs) == 0:
            raise ValueError(f"No COGs found for collection '{collection}'. Is the STAC loaded?")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, save: bool = True) -> pd.DataFrame:
        """Run the benchmark and return a metrics DataFrame.

        Set *save* to ``False`` if you do **not** want the CSV + quick-look tables.
        """
        metrics_rows: List[Dict] = []
        y_true_all, y_pred_all = [], []
        missing_total = 0              # missing pixels across all months
        total_pixels_all = 0           # valid + missing pixels across all months
        total_polygons_considered = 0

        # One pass over every month that has polygons
        months_sorted = [f"{m:02d}" for m in range(1, 13)]
        for month_str in months_sorted:
            month = f"{self.year}-{month_str}"
            print("-" * 100)
            print(f"Processing {month}")

            # ------------------------------------------------------------------
            # Load training polygons for this month & filter by the held-out set
            # ------------------------------------------------------------------
            try:
                gdf_month = load_training_polygons(
                    self.engine,
                    project_id=self.project_id,
                    basemap_date=month,
                )
            except Exception as e:
                raise RuntimeError(
                    f"❌  Failed to load polygons for {month}: {e}. "
                    "This likely means the training-polygon table is incomplete "
                    "or the SQL query needs updating."
                ) from e

            # Only keep Forest / Non-Forest labels
            gdf_month = gdf_month[gdf_month["classLabel"].isin(["Forest", "Non-Forest"])]

            if gdf_month.empty:
                raise ValueError(
                    f"❌  No Forest / Non-Forest polygons found for {month}. "
                    "This contradicts the expectation that each month has polygons."
                )

            # Filter to held-out feature IDs (if provided)
            if self.test_features_dir is not None:
                csv_path = self.test_features_dir / f"test_features_{month}.csv"
                if csv_path.exists():
                    feature_df = pd.read_csv(csv_path)
                    held_out_ids = set(feature_df["feature_id"].astype(str))
                    gdf_month = gdf_month[gdf_month["id"].isin(held_out_ids)]
                    print(f"Held-out polygons: {len(gdf_month)}")
                else:
                    raise FileNotFoundError(
                        f"❌  Expected held-out CSV not found for {month}: {csv_path}"
                    )

            if gdf_month.empty:
                raise ValueError(
                    f"❌  All polygons were filtered out for {month} after applying the held-out IDs."
                )

            # ------------------------------------------------------------------
            # Extract pixels & classify for each polygon
            # ------------------------------------------------------------------
            predictions = []
            total_missing_px = 0
            
            for idx, row in gdf_month.iterrows():
                try:
                    pixels, missing_px, _ = extract_pixels_with_missing(self.extractor, row.geometry, self.band_indexes)
                    total_missing_px += missing_px
                    
                    if pixels.size > 0:
                        y_pred = pixels_to_labels(self.collection, pixels.squeeze())
                        # Take majority vote if multiple pixels
                        if len(y_pred) > 1:
                            unique, counts = np.unique(y_pred, return_counts=True)
                            predicted_label = unique[np.argmax(counts)]
                        else:
                            predicted_label = y_pred[0]
                        
                        predictions.append({
                            "id": str(row["id"]),  # Ensure string type
                            "predicted_label": predicted_label
                        })
                except Exception as e:
                    print(f"  ⚠️  Failed to extract pixels for polygon {row['id']}: {e}")
                    continue
            
            if not predictions:
                raise RuntimeError(
                    f"❌  No valid predictions extracted for {month}. Check if the raster has coverage "
                    "or if all pixels are nodata."
                )

            pred_df = pd.DataFrame(predictions)
            
            # Convert gdf_month id to string for consistent merge
            gdf_month["id"] = gdf_month["id"].astype(str)
            
            # Merge predictions into GeoDataFrame
            gdf_month = gdf_month.merge(pred_df, on="id", how="left")
            
            missing_px = total_missing_px

            # Pixel-based missing-data metric
            valid_px = len(predictions)  # Number of successful predictions
            missing_px_pct = missing_px / (missing_px + valid_px) if (missing_px + valid_px) else 0.0
            print(
                f"Pixel-level missing data: {missing_px} missing vs {valid_px} valid "
                f"({missing_px_pct:.2%})"
            )

            # Track global counts
            missing_total += missing_px
            total_pixels_all += (missing_px + valid_px)
            total_polygons_considered += len(gdf_month)

            # ------------------------------------------------------------------
            # Calculate metrics – drop polygons without predictions
            # ------------------------------------------------------------------
            gdf_valid = gdf_month[gdf_month["predicted_label"].notna()]
            if gdf_valid.empty:
                raise RuntimeError(
                    f"❌  Predictions failed for every polygon in {month}."
                )

            y_true = gdf_valid["classLabel"]
            y_pred_valid = gdf_valid["predicted_label"]

            acc = accuracy_score(y_true, y_pred_valid)
            report = classification_report(
                y_true,
                y_pred_valid,
                labels=["Forest", "Non-Forest"],
                output_dict=True,
                zero_division=0,
            )

            metrics_rows.append(
                {
                    "run_id": self.run_id,
                    "collection": self.collection,
                    "month": month,
                    "n_polygons": len(gdf_month),
                    "n_pixels": len(y_pred),
                    "accuracy": acc,
                    "f1_forest": report["Forest"]["f1-score"],
                    "f1_nonforest": report["Non-Forest"]["f1-score"],
                    "precision_forest": report["Forest"]["precision"],
                    "precision_nonforest": report["Non-Forest"]["precision"],
                    "recall_forest": report["Forest"]["recall"],
                    "recall_nonforest": report["Non-Forest"]["recall"],
                    "missing_pct": missing_px_pct,
                }
            )

            y_true_all.extend(y_true)
            y_pred_all.extend(y_pred_valid)

        # ------------------------------------------------------------------
        # Overall metrics – across every month
        # ------------------------------------------------------------------
        if not y_true_all:
            raise RuntimeError("No predictions were generated across any month – nothing to benchmark.")

        overall_acc = accuracy_score(y_true_all, y_pred_all)
        overall_report = classification_report(
            y_true_all,
            y_pred_all,
            labels=["Forest", "Non-Forest"],
            output_dict=True,
            zero_division=0,
        )
        metrics_rows.append(
            {
                "run_id": self.run_id,
                "collection": self.collection,
                "month": "overall",
                "n_polygons": total_polygons_considered,
                "n_pixels": len(y_pred_all),
                "accuracy": overall_acc,
                "f1_forest": overall_report["Forest"]["f1-score"],
                "f1_nonforest": overall_report["Non-Forest"]["f1-score"],
                "precision_forest": overall_report["Forest"]["precision"],
                "precision_nonforest": overall_report["Non-Forest"]["precision"],
                "recall_forest": overall_report["Forest"]["recall"],
                "recall_nonforest": overall_report["Non-Forest"]["recall"],
                "missing_pct": missing_total / total_pixels_all if total_pixels_all else np.nan,
            }
        )

        metrics_df = pd.DataFrame(metrics_rows)

        # ------------------------------------------------------------------
        # Save + quick-look
        # ------------------------------------------------------------------
        if save:
            if self.run_id is None:
                raise ValueError("run_id must be provided to save benchmark metrics inside the run folder.")
            save_metrics_csv(metrics_df, benchmark_name=self.collection, run_id=self.run_id)
            show_accuracy_table(metrics_df)
            plot_accuracy(metrics_df)

        return metrics_df
