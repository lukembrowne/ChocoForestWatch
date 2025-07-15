"""
ml_pipeline.tuning_reporter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analysis and visualization tools for hyperparameter tuning results.

This module provides:
- Results comparison and ranking by F1-macro performance
- Parameter importance analysis using F1-macro correlation
- Performance visualization focused on F1-macro metrics
- HTML report generation with F1-macro as primary metric
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import seaborn as sns
from scipy.stats import pearsonr, spearmanr

from .hyperparameter_tuner import ExperimentResult

logger = logging.getLogger(__name__)


class TuningReporter:
    """Analysis and reporting for hyperparameter tuning results using F1-macro as primary metric."""
    
    def __init__(self, tuning_dir: Path):
        """
        Initialize reporter with tuning results directory.
        
        Parameters
        ----------
        tuning_dir : Path
            Directory containing tuning results.
        """
        self.tuning_dir = Path(tuning_dir)
        self.results: List[ExperimentResult] = []
        self.summary_df: Optional[pd.DataFrame] = None
        
        # Load results
        self._load_results()
        
        if not self.results:
            raise ValueError(f"No tuning results found in {tuning_dir}")
        
        logger.info(f"Loaded {len(self.results)} experiment results")
    
    def _load_results(self):
        """Load experiment results from JSON files."""
        for result_file in self.tuning_dir.glob("experiment_*.json"):
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                result = ExperimentResult.from_dict(data)
                self.results.append(result)
            except Exception as e:
                logger.warning(f"Failed to load {result_file}: {e}")
        
        # Sort by performance
        self.results.sort(key=lambda x: x.score, reverse=True)
        
        # Create summary dataframe
        self._create_summary_dataframe()
    
    def _create_summary_dataframe(self):
        """Create summary dataframe from results."""
        data = []
        for result in self.results:
            row = {
                'experiment_id': result.experiment_id,
                'cv_f1_macro_mean': result.cv_f1_macro_mean,
                'cv_f1_macro_std': result.cv_f1_macro_std,
                'test_f1_macro': result.test_f1_macro,
                'cv_accuracy_mean': result.cv_accuracy_mean,
                'cv_accuracy_std': result.cv_accuracy_std,
                'test_accuracy': result.test_accuracy,
                'test_f1_mean': np.mean(result.test_f1_scores),
                'test_f1_std': np.std(result.test_f1_scores),
                'training_time_seconds': result.training_time_seconds,
                'timestamp': result.timestamp
            }
            
            # Add parameters with 'param_' prefix
            for param_name, param_value in result.parameters.items():
                row[f'param_{param_name}'] = param_value
            
            data.append(row)
        
        self.summary_df = pd.DataFrame(data)
    
    def get_top_results(self, n: int = 10) -> List[ExperimentResult]:
        """Get top N results by CV F1-macro."""
        return self.results[:n]
    
    def analyze_parameter_importance(self) -> Dict[str, float]:
        """
        Analyze parameter importance using correlation with F1-macro performance.
        
        Returns
        -------
        Dict[str, float]
            Parameter importance scores (absolute correlation with F1-macro).
        """
        if self.summary_df is None:
            return {}
        
        param_cols = [col for col in self.summary_df.columns if col.startswith('param_')]
        target = 'cv_f1_macro_mean'
        
        importance = {}
        for param_col in param_cols:
            param_name = param_col.replace('param_', '')
            
            # Handle different parameter types
            param_values = self.summary_df[param_col]
            
            # Skip if parameter is constant
            if param_values.nunique() <= 1:
                importance[param_name] = 0.0
                continue
            
            # For numeric parameters, use Pearson correlation
            if pd.api.types.is_numeric_dtype(param_values):
                corr, p_value = pearsonr(param_values, self.summary_df[target])
                importance[param_name] = abs(corr) if not np.isnan(corr) else 0.0
            else:
                # For categorical parameters, use rank correlation after encoding
                try:
                    encoded = pd.Categorical(param_values).codes
                    corr, p_value = spearmanr(encoded, self.summary_df[target])
                    importance[param_name] = abs(corr) if not np.isnan(corr) else 0.0
                except:
                    importance[param_name] = 0.0
        
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    
    def plot_parameter_importance(self, save_path: Path = None) -> Path:
        """
        Plot parameter importance analysis.
        
        Parameters
        ----------
        save_path : Path, optional
            Where to save the plot. If None, saves to tuning directory.
            
        Returns
        -------
        Path
            Path where plot was saved.
        """
        importance = self.analyze_parameter_importance()
        
        if not importance:
            logger.warning("No parameter importance data to plot")
            return None
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        params = list(importance.keys())
        scores = list(importance.values())
        
        bars = ax.barh(params, scores)
        ax.set_xlabel('Absolute Correlation with CV F1-macro')
        ax.set_title('Parameter Importance Analysis')
        ax.grid(True, alpha=0.3)
        
        # Color bars by importance
        max_score = max(scores) if scores else 1
        for bar, score in zip(bars, scores):
            bar.set_color(plt.cm.viridis(score / max_score))
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = self.tuning_dir / "parameter_importance.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def plot_performance_distribution(self, save_path: Path = None) -> Path:
        """
        Plot distribution of performance scores.
        
        Parameters
        ----------
        save_path : Path, optional
            Where to save the plot.
            
        Returns
        -------
        Path
            Path where plot was saved.
        """
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # CV F1-macro distribution
        cv_f1_scores = [r.cv_f1_macro_mean for r in self.results]
        axes[0].hist(cv_f1_scores, bins=20, alpha=0.7, edgecolor='black')
        axes[0].axvline(np.mean(cv_f1_scores), color='red', linestyle='--', label=f'Mean: {np.mean(cv_f1_scores):.4f}')
        axes[0].set_xlabel('CV F1-macro')
        axes[0].set_ylabel('Count')
        axes[0].set_title('Cross-Validation F1-macro Distribution')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Test F1-macro vs CV F1-macro
        test_f1_scores = [r.test_f1_macro for r in self.results]
        axes[1].scatter(cv_f1_scores, test_f1_scores, alpha=0.6)
        axes[1].plot([min(cv_f1_scores), max(cv_f1_scores)], [min(cv_f1_scores), max(cv_f1_scores)], 'r--', alpha=0.8)
        axes[1].set_xlabel('CV F1-macro')
        axes[1].set_ylabel('Test F1-macro')
        axes[1].set_title('Test vs CV F1-macro')
        axes[1].grid(True, alpha=0.3)
        
        # Add correlation coefficient
        corr, _ = pearsonr(cv_f1_scores, test_f1_scores)
        axes[1].text(0.05, 0.95, f'r = {corr:.3f}', transform=axes[1].transAxes, 
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = self.tuning_dir / "performance_distribution.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def plot_parameter_vs_performance(self, parameter_name: str, save_path: Path = None) -> Path:
        """
        Plot relationship between a parameter and performance.
        
        Parameters
        ----------
        parameter_name : str
            Name of the parameter to analyze.
        save_path : Path, optional
            Where to save the plot.
            
        Returns
        -------
        Path
            Path where plot was saved.
        """
        if self.summary_df is None:
            return None
        
        param_col = f'param_{parameter_name}'
        if param_col not in self.summary_df.columns:
            logger.warning(f"Parameter '{parameter_name}' not found in results")
            return None
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x_values = self.summary_df[param_col]
        y_values = self.summary_df['cv_f1_macro_mean']
        y_errors = self.summary_df['cv_f1_macro_std']
        
        if pd.api.types.is_numeric_dtype(x_values):
            # Scatter plot for numeric parameters
            ax.scatter(x_values, y_values, alpha=0.6)
            ax.errorbar(x_values, y_values, yerr=y_errors, fmt='none', alpha=0.3)
            
            # Add trend line
            if len(set(x_values)) > 1:
                z = np.polyfit(x_values, y_values, 1)
                p = np.poly1d(z)
                ax.plot(sorted(x_values), p(sorted(x_values)), "r--", alpha=0.8)
        else:
            # Box plot for categorical parameters
            unique_values = sorted(x_values.unique())
            data_by_value = [y_values[x_values == val] for val in unique_values]
            ax.boxplot(data_by_value, labels=unique_values)
        
        ax.set_xlabel(parameter_name)
        ax.set_ylabel('CV F1-macro')
        ax.set_title(f'Parameter Effect: {parameter_name}')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = self.tuning_dir / f"param_effect_{parameter_name}.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def plot_training_time_analysis(self, save_path: Path = None) -> Path:
        """
        Plot training time vs performance analysis.
        
        Parameters
        ----------
        save_path : Path, optional
            Where to save the plot.
            
        Returns
        -------
        Path
            Path where plot was saved.
        """
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        times = [r.training_time_seconds for r in self.results]
        scores = [r.cv_f1_macro_mean for r in self.results]
        
        # Training time distribution
        axes[0].hist(times, bins=20, alpha=0.7, edgecolor='black')
        axes[0].axvline(np.mean(times), color='red', linestyle='--', label=f'Mean: {np.mean(times):.1f}s')
        axes[0].set_xlabel('Training Time (seconds)')
        axes[0].set_ylabel('Count')
        axes[0].set_title('Training Time Distribution')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Performance vs time trade-off
        axes[1].scatter(times, scores, alpha=0.6)
        axes[1].set_xlabel('Training Time (seconds)')
        axes[1].set_ylabel('CV F1-macro')
        axes[1].set_title('Performance vs Training Time Trade-off')
        axes[1].grid(True, alpha=0.3)
        
        # Highlight Pareto frontier
        pareto_indices = self._find_pareto_frontier(times, scores)
        pareto_times = [times[i] for i in pareto_indices]
        pareto_scores = [scores[i] for i in pareto_indices]
        axes[1].scatter(pareto_times, pareto_scores, color='red', s=100, alpha=0.8, label='Pareto Optimal')
        axes[1].legend()
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = self.tuning_dir / "training_time_analysis.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def _find_pareto_frontier(self, costs: List[float], benefits: List[float]) -> List[int]:
        """Find Pareto optimal points (minimize cost, maximize benefit)."""
        points = list(zip(costs, benefits, range(len(costs))))
        points.sort()  # Sort by cost
        
        pareto_indices = []
        max_benefit = float('-inf')
        
        for cost, benefit, idx in points:
            if benefit > max_benefit:
                max_benefit = benefit
                pareto_indices.append(idx)
        
        return pareto_indices
    
    def generate_html_report(self, save_path: Path = None) -> Path:
        """
        Generate comprehensive HTML report.
        
        Parameters
        ----------
        save_path : Path, optional
            Where to save the report.
            
        Returns
        -------
        Path
            Path where report was saved.
        """
        if save_path is None:
            save_path = self.tuning_dir / "tuning_report.html"
        
        # Generate all plots
        plot_paths = {}
        plot_paths['importance'] = self.plot_parameter_importance()
        plot_paths['distribution'] = self.plot_performance_distribution()
        plot_paths['time_analysis'] = self.plot_training_time_analysis()
        
        # Generate parameter effect plots for top parameters
        importance = self.analyze_parameter_importance()
        top_params = list(importance.keys())[:5]  # Top 5 most important
        
        param_plots = {}
        for param in top_params:
            param_plots[param] = self.plot_parameter_vs_performance(param)
        
        # Get summary statistics
        best_result = self.results[0] if self.results else None
        stats = self._calculate_summary_stats()
        
        # Create HTML content
        html_content = self._create_html_content(
            best_result=best_result,
            stats=stats,
            plot_paths=plot_paths,
            param_plots=param_plots,
            importance=importance
        )
        
        # Write HTML file
        with open(save_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {save_path}")
        return save_path
    
    def _calculate_summary_stats(self) -> Dict[str, Any]:
        """Calculate summary statistics."""
        f1_scores = [r.cv_f1_macro_mean for r in self.results]
        times = [r.training_time_seconds for r in self.results]
        
        return {
            'n_experiments': len(self.results),
            'best_score': max(f1_scores) if f1_scores else 0,
            'worst_score': min(f1_scores) if f1_scores else 0,
            'mean_score': np.mean(f1_scores) if f1_scores else 0,
            'std_score': np.std(f1_scores) if f1_scores else 0,
            'mean_time': np.mean(times) if times else 0,
            'total_time': sum(times) if times else 0
        }
    
    def _create_html_content(self, 
                           best_result: ExperimentResult,
                           stats: Dict[str, Any],
                           plot_paths: Dict[str, Path],
                           param_plots: Dict[str, Path],
                           importance: Dict[str, float]) -> str:
        """Create HTML report content."""
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Hyperparameter Tuning Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 30px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .plot {{ text-align: center; margin: 20px 0; }}
        .plot img {{ max-width: 100%; height: auto; border: 1px solid #ddd; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .best {{ background-color: #d4edda; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Hyperparameter Tuning Report</h1>
        <p>Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="section">
        <h2>Summary Statistics</h2>
        <div class="metric"><strong>Experiments:</strong> {stats['n_experiments']}</div>
        <div class="metric"><strong>Best CV F1-macro:</strong> {stats['best_score']:.4f}</div>
        <div class="metric"><strong>Mean CV F1-macro:</strong> {stats['mean_score']:.4f} ± {stats['std_score']:.4f}</div>
        <div class="metric"><strong>Total Training Time:</strong> {stats['total_time']/3600:.1f} hours</div>
    </div>
        """
        
        # Best result section
        if best_result:
            html += f"""
    <div class="section">
        <h2>Best Result</h2>
        <p><strong>Experiment:</strong> {best_result.experiment_id}</p>
        <p><strong>CV F1-macro:</strong> {best_result.cv_f1_macro_mean:.4f} ± {best_result.cv_f1_macro_std:.4f}</p>
        <p><strong>Test F1-macro:</strong> {best_result.test_f1_macro:.4f}</p>
        <p><strong>Test Accuracy:</strong> {best_result.test_accuracy:.4f}</p>
        <p><strong>Training Time:</strong> {best_result.training_time_seconds:.1f} seconds</p>
        
        <h3>Best Parameters</h3>
        <table>
            <tr><th>Parameter</th><th>Value</th></tr>
            """
            
            for param, value in best_result.parameters.items():
                if param != 'random_state':  # Skip random_state for clarity
                    html += f"<tr><td>{param}</td><td>{value}</td></tr>"
            
            html += "</table></div>"
        
        # Parameter importance section
        html += """
    <div class="section">
        <h2>Parameter Importance Analysis</h2>
        """
        
        if importance:
            html += """
        <table>
            <tr><th>Parameter</th><th>Importance Score</th></tr>
            """
            for param, score in list(importance.items())[:10]:  # Top 10
                html += f"<tr><td>{param}</td><td>{score:.4f}</td></tr>"
            html += "</table>"
        
        # Add plots
        for plot_name, plot_path in plot_paths.items():
            if plot_path and plot_path.exists():
                rel_path = plot_path.name  # Just filename for relative path
                html += f"""
        <div class="plot">
            <h3>{plot_name.replace('_', ' ').title()}</h3>
            <img src="{rel_path}" alt="{plot_name}">
        </div>
                """
        
        html += "</div>"
        
        # Parameter effect plots
        if param_plots:
            html += """
    <div class="section">
        <h2>Parameter Effects</h2>
            """
            for param, plot_path in param_plots.items():
                if plot_path and plot_path.exists():
                    rel_path = plot_path.name
                    html += f"""
        <div class="plot">
            <h3>Effect of {param}</h3>
            <img src="{rel_path}" alt="Effect of {param}">
        </div>
                    """
            html += "</div>"
        
        # Top results table
        html += """
    <div class="section">
        <h2>Top 10 Results</h2>
        <table>
            <tr>
                <th>Rank</th>
                <th>Experiment</th>
                <th>CV F1-macro</th>
                <th>Test F1-macro</th>
                <th>Test Accuracy</th>
                <th>Training Time (s)</th>
            </tr>
        """
        
        for i, result in enumerate(self.results[:10]):
            css_class = "best" if i == 0 else ""
            html += f"""
            <tr class="{css_class}">
                <td>{i+1}</td>
                <td>{result.experiment_id}</td>
                <td>{result.cv_f1_macro_mean:.4f} ± {result.cv_f1_macro_std:.4f}</td>
                <td>{result.test_f1_macro:.4f}</td>
                <td>{result.test_accuracy:.4f}</td>
                <td>{result.training_time_seconds:.1f}</td>
            </tr>
            """
        
        html += """
        </table>
    </div>
</body>
</html>
        """
        
        return html


def generate_tuning_report(tuning_dir: Path) -> Path:
    """
    Convenience function to generate a tuning report.
    
    Parameters
    ----------
    tuning_dir : Path
        Directory containing tuning results.
        
    Returns
    -------
    Path
        Path to generated HTML report.
    """
    reporter = TuningReporter(tuning_dir)
    return reporter.generate_html_report()