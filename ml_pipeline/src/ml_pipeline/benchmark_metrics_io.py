# ─── benchmark_metrics_io.py ────────────────────────────────────────────────
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt   # Only needed if you want the quick plot

# ---------- I/O helpers ----------------------------------------------------
def save_metrics_csv(
    metrics_df: pd.DataFrame,
    benchmark_name: str,
    out_root: Path | str = "benchmark_results",
) -> Path:
    """
    Save *one* benchmark run to:
        benchmark_results/<benchmark_name>/metrics_YYYYMMDD_HHMMSS.csv
    """
    out_dir = Path(out_root) / benchmark_name
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"metrics_{stamp}.csv"
    metrics_df.to_csv(out_file, index=False)
    print(f"✅  Metrics written ➜ {out_file}")
    return out_file


def load_all_metrics(
    benchmark_name: str,
    out_root: Path | str = "benchmark_results",
) -> pd.DataFrame:
    """
    Read every metrics_*.csv for the benchmark and return one long DataFrame.
    """
    csv_files = sorted((Path(out_root) / benchmark_name).glob("metrics_*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No metrics CSVs found for benchmark “{benchmark_name}” in {out_root}"
        )
    return pd.concat(map(pd.read_csv, csv_files), ignore_index=True)


# ---------- Quick-look display --------------------------------------------
def show_accuracy_table(all_metrics: pd.DataFrame) -> None:
    """Pretty, one-line accuracy summary by month (ignoring the 'overall' row)."""
    tbl = (
        all_metrics.query("month != 'overall'")
        .pivot_table(index="month", values="accuracy", aggfunc=["mean", "std"])
        .round(3)
    )
    print("\nPer-month accuracy (mean ± SD across runs)\n")
    print(tbl.to_markdown())


def plot_accuracy(all_metrics: pd.DataFrame, title: str = "") -> None:
    """Bar plot of accuracy per month (optional, but handy)."""
    df = all_metrics.query("month != 'overall'")
    df.plot(kind="bar", x="month", y="accuracy", legend=False)
    plt.ylabel("Accuracy")
    plt.title(title or "Benchmark accuracy per month")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()