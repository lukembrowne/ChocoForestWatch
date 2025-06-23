# ─── benchmark_metrics_io.py ────────────────────────────────────────────────
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# ---------- I/O helpers ----------------------------------------------------
def save_metrics_csv(
    metrics_df: pd.DataFrame,
    benchmark_name: str,
    *,
    run_id: str,
    runs_root: Path | str = None,
) -> Path:
    """Save one benchmark run CSV inside this run's folder.

    The file layout is now:
        <ml_pipeline_root>/runs/<run_id>/benchmark_results/<benchmark_name>.csv

    Parameters
    ----------
    metrics_df
        DataFrame returned from ``BenchmarkTester.run``.
    benchmark_name
        Typically the STAC collection ID (e.g. ``nicfi-pred-composite-2022``).
    run_id
        Identifier for the current pipeline run (matches ``RunManager``).
    runs_root
        Root directory that contains all runs. If None, automatically resolves 
        to <ml_pipeline_root>/runs for consistency.
    """
    if runs_root is None:
        # Automatically resolve to ml_pipeline root runs folder
        # Go up from src/ml_pipeline to ml_pipeline root
        ml_pipeline_root = Path(__file__).parent.parent.parent
        runs_root = ml_pipeline_root / "runs"
    
    out_dir = Path(runs_root) / run_id / "benchmark_results"
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_benchmark = benchmark_name.replace("/", "-")
    out_file = out_dir / f"{safe_benchmark}.csv"

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
            f"No metrics CSVs found for benchmark {benchmark_name}"
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


# ---------- Summary Visualization Functions --------------------------------
def create_benchmark_summary_charts(
    run_id: str,
    runs_root: Path | str = None,
    save_charts: bool = True,
    show_charts: bool = False
) -> None:
    """
    Create individual summary charts comparing all benchmark results for a run.
    
    Generates separate comparative visualizations:
    - Overall accuracy comparison across benchmarks
    - F1-scores by class (Forest/Non-Forest) 
    - Precision comparison by class
    - Recall comparison by class
    - Missing data percentage comparison
    
    Charts use a blue color scheme with 'Our Model' highlighted in dark green.
    
    Parameters
    ----------
    run_id : str
        The run identifier to create summaries for
    runs_root : Path | str, optional
        Root directory containing runs. If None, auto-resolves to ml_pipeline/runs
    save_charts : bool, default True
        Whether to save charts as PNG files in the benchmark_results folder
    show_charts : bool, default False
        Whether to display charts interactively (useful for Jupyter notebooks)
    """
    if runs_root is None:
        # Auto-resolve to ml_pipeline root runs folder
        ml_pipeline_root = Path(__file__).parent.parent.parent
        runs_root = ml_pipeline_root / "runs"
    
    benchmark_dir = Path(runs_root) / run_id / "benchmark_results"
    
    if not benchmark_dir.exists():
        print(f"❌ No benchmark results found for run {run_id} at {benchmark_dir}")
        return
    
    # Load all benchmark CSV files
    csv_files = list(benchmark_dir.glob("*.csv"))
    if not csv_files:
        print(f"❌ No CSV files found in {benchmark_dir}")
        return
    
    print(f"📊 Loading benchmark results from {len(csv_files)} files...")
    
    # Combine all benchmark results
    all_results = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        # Extract benchmark name from filename
        benchmark_name = csv_file.stem
        df['benchmark'] = benchmark_name
        all_results.append(df)
    
    combined_df = pd.concat(all_results, ignore_index=True)
    
    # Filter to overall results only for cross-benchmark comparison
    overall_df = combined_df[combined_df['month'] == 'overall'].copy()
    
    if overall_df.empty:
        print("❌ No 'overall' summary rows found in benchmark results")
        return
    
    # Clean up benchmark names for better display
    overall_df['benchmark_clean'] = overall_df['benchmark'].str.replace('nicfi-pred-', 'Our Model: ').str.replace('-composite-2022', '').str.replace('benchmarks-', '').str.replace('-', ' ').str.title()
    
    # Define color scheme: blue for benchmarks, dark green for our model
    def get_bar_colors(benchmark_names):
        """Return color list: dark green for 'Our Model', blue for others"""
        colors = []
        for name in benchmark_names:
            if 'Our Model' in name:
                colors.append('#2d5a2d')  # Dark green for our model
            else:
                colors.append('#4a90e2')  # Nice blue for benchmarks
        return colors
    
    # Set up plotting style
    plt.style.use('default')
    
    # List of charts to create
    charts = [
        {
            'data_col': 'accuracy',
            'title': 'Overall Accuracy Comparison',
            'xlabel': 'Accuracy',
            'filename': 'accuracy_comparison',
            'xlim': (0, 1),
            'format_func': lambda x: f'{x:.3f}'
        },
        {
            'data_col': 'f1_forest',
            'title': 'F1-Score Comparison - Forest Class',
            'xlabel': 'F1-Score (Forest)',
            'filename': 'f1_forest_comparison',
            'xlim': (0, 1),
            'format_func': lambda x: f'{x:.3f}'
        },
        {
            'data_col': 'f1_nonforest',
            'title': 'F1-Score Comparison - Non-Forest Class',
            'xlabel': 'F1-Score (Non-Forest)',
            'filename': 'f1_nonforest_comparison',
            'xlim': (0, 1),
            'format_func': lambda x: f'{x:.3f}'
        },
        {
            'data_col': 'precision_forest',
            'title': 'Precision Comparison - Forest Class',
            'xlabel': 'Precision (Forest)',
            'filename': 'precision_forest_comparison',
            'xlim': (0, 1),
            'format_func': lambda x: f'{x:.3f}'
        },
        {
            'data_col': 'recall_forest',
            'title': 'Recall Comparison - Forest Class',
            'xlabel': 'Recall (Forest)',
            'filename': 'recall_forest_comparison',
            'xlim': (0, 1),
            'format_func': lambda x: f'{x:.3f}'
        },
        {
            'data_col': 'missing_pct',
            'title': 'Missing Data Comparison',
            'xlabel': 'Missing Data (%)',
            'filename': 'missing_data_comparison',
            'xlim': None,
            'format_func': lambda x: f'{x*100:.1f}%',
            'multiply_by_100': True
        }
    ]
    
    # Generate each chart individually
    for chart_config in charts:
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Sort data for this chart
        chart_data = overall_df.sort_values(chart_config['data_col'], ascending=True).copy()
        
        # Get values (multiply by 100 for percentage if needed)
        values = chart_data[chart_config['data_col']]
        if chart_config.get('multiply_by_100', False):
            plot_values = values * 100
        else:
            plot_values = values
        
        # Get colors for bars
        colors = get_bar_colors(chart_data['benchmark_clean'])
        
        # Create horizontal bar chart
        bars = ax.barh(chart_data['benchmark_clean'], plot_values, color=colors)
        
        # Customize chart
        ax.set_xlabel(chart_config['xlabel'], fontsize=12, fontweight='bold')
        ax.set_title(chart_config['title'], fontsize=14, fontweight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        
        # Set x-axis limits if specified
        if chart_config['xlim']:
            if chart_config.get('multiply_by_100', False):
                ax.set_xlim(chart_config['xlim'][0] * 100, chart_config['xlim'][1] * 100)
            else:
                ax.set_xlim(chart_config['xlim'])
        
        # Add value labels on bars
        for bar, val in zip(bars, values):
            label_text = chart_config['format_func'](val)
            # Position label slightly to the right of bar end
            label_x = bar.get_width() + (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.01
            ax.text(label_x, bar.get_y() + bar.get_height()/2, label_text, 
                   va='center', fontweight='bold', fontsize=10)
        
        # Make y-axis labels more readable
        ax.tick_params(axis='y', labelsize=10)
        ax.tick_params(axis='x', labelsize=10)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the chart if requested
        if save_charts:
            chart_path = benchmark_dir / f"{chart_config['filename']}_{run_id}.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"✅ Chart saved: {chart_path}")
        
        # Show the chart if requested
        if show_charts:
            plt.show()
        else:
            plt.close()
    
    print(f"📊 Generated {len(charts)} individual benchmark comparison charts")
    
    # Create a summary table and save as CSV
    summary_table = overall_df[['benchmark_clean', 'accuracy', 'f1_forest', 'f1_nonforest', 
                               'precision_forest', 'precision_nonforest', 'recall_forest', 
                               'recall_nonforest', 'missing_pct', 'n_pixels']].copy()
    
    summary_table = summary_table.sort_values('accuracy', ascending=False)
    summary_table.columns = ['Benchmark', 'Accuracy', 'F1_Forest', 'F1_NonForest', 
                            'Precision_Forest', 'Precision_NonForest', 'Recall_Forest', 
                            'Recall_NonForest', 'Missing_%', 'Total_Pixels']
    
    # Round numeric columns for readability
    numeric_cols = ['Accuracy', 'F1_Forest', 'F1_NonForest', 'Precision_Forest', 
                   'Precision_NonForest', 'Recall_Forest', 'Recall_NonForest', 'Missing_%']
    summary_table[numeric_cols] = summary_table[numeric_cols].round(4)
    summary_table['Missing_%'] = (summary_table['Missing_%'] * 100).round(2)
    
    # Save summary table
    summary_path = benchmark_dir / f"benchmark_summary_table_{run_id}.csv"
    summary_table.to_csv(summary_path, index=False)
    print(f"✅ Summary table saved: {summary_path}")
    
    # Print summary to console
    print(f"\n📋 Benchmark Summary for Run: {run_id}")
    print("=" * 60)
    print(summary_table.to_string(index=False))
    print(f"\n🎯 Best performing benchmark (by accuracy): {summary_table.iloc[0]['Benchmark']}")
    print(f"   Accuracy: {summary_table.iloc[0]['Accuracy']:.4f}")


def load_run_benchmark_data(
    run_id: str,
    runs_root: Path | str = None
) -> pd.DataFrame:
    """
    Load and combine all benchmark CSV files for a specific run.
    
    Parameters
    ----------
    run_id : str
        The run identifier to load data for
    runs_root : Path | str, optional
        Root directory containing runs. If None, auto-resolves to ml_pipeline/runs
        
    Returns
    -------
    pd.DataFrame
        Combined benchmark results with benchmark name added as a column
    """
    if runs_root is None:
        ml_pipeline_root = Path(__file__).parent.parent.parent
        runs_root = ml_pipeline_root / "runs"
    
    benchmark_dir = Path(runs_root) / run_id / "benchmark_results"
    
    if not benchmark_dir.exists():
        raise FileNotFoundError(f"No benchmark results found for run {run_id}")
    
    csv_files = list(benchmark_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {benchmark_dir}")
    
    all_results = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        benchmark_name = csv_file.stem
        df['benchmark'] = benchmark_name
        all_results.append(df)
    
    return pd.concat(all_results, ignore_index=True)