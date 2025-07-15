"""
ml_pipeline.hyperparameter_tuner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hyperparameter tuning framework for XGBoost models in forest classification.

This module provides:
- Random search over parameter spaces
- Integration with existing ModelTrainer and diagnostics
- Experiment tracking and comparison
- Automatic best model selection
"""

from __future__ import annotations
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict

from .trainer import ModelTrainer, TrainerConfig
from .tuning_configs import TuningConfig, validate_parameter_ranges
from .run_manager import RunManager

logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    """Results from a single hyperparameter experiment."""
    experiment_id: str
    parameters: Dict[str, Any]
    cv_f1_macro_mean: float
    cv_f1_macro_std: float
    cv_accuracy_mean: float
    cv_accuracy_std: float
    test_f1_macro: float
    test_accuracy: float
    test_f1_scores: List[float]
    test_precision: List[float]
    test_recall: List[float]
    training_time_seconds: float
    model_path: Path
    diagnostics_path: Path
    timestamp: str
    
    @property
    def score(self) -> float:
        """Primary score for ranking experiments (F1-macro)."""
        return self.cv_f1_macro_mean
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['model_path'] = str(result['model_path'])
        result['diagnostics_path'] = str(result['diagnostics_path'])
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentResult':
        """Create from dictionary."""
        data['model_path'] = Path(data['model_path'])
        data['diagnostics_path'] = Path(data['diagnostics_path'])
        return cls(**data)


class HyperparameterTuner:
    """Hyperparameter tuning system for XGBoost forest classification models."""
    
    def __init__(self, 
                 trainer: ModelTrainer,
                 run_manager: RunManager,
                 n_trials: int = 25,
                 random_state: int = 42):
        """
        Initialize hyperparameter tuner.
        
        Parameters
        ----------
        trainer : ModelTrainer
            Configured trainer instance with data already prepared.
        run_manager : RunManager
            Run manager for organizing results.
        n_trials : int, default=25
            Number of trials to run for hyperparameter optimization.
        random_state : int, default=42
            Random state for reproducible experiments.
        """
        self.trainer = trainer
        self.run_manager = run_manager
        self.random_state = np.random.RandomState(random_state)
        self.n_trials = n_trials
        
        # Load tuning configuration
        self.config = TuningConfig.create_config(n_trials)
        
        # Validate configuration
        validate_parameter_ranges(self.config['parameters'])
        
        # Setup tuning directory
        self.tuning_dir = run_manager.run_path / "hyperparameter_tuning"
        self.tuning_dir.mkdir(exist_ok=True)
        
        # Results tracking
        self.results: List[ExperimentResult] = []
        self.best_result: Optional[ExperimentResult] = None
        
        logger.info(f"Initialized tuner with {n_trials} trials")
        logger.info(f"Tuning parameters: {list(self.config['parameters'].keys())}")
    
    def generate_experiment_parameters(self) -> Dict[str, Any]:
        """Generate a random set of parameters for one experiment."""
        params = TuningConfig.generate_parameter_set(
            self.config['parameters'], 
            self.random_state
        )
        
        # Always include random_state for reproducibility
        params['random_state'] = self.trainer.cfg.random_state
        
        return params
    
    def run_single_experiment(self, 
                             experiment_id: str,
                             parameters: Dict[str, Any],
                             npz_path: Path) -> ExperimentResult:
        """
        Run a single hyperparameter experiment.
        
        Parameters
        ----------
        experiment_id : str
            Unique identifier for this experiment.
        parameters : Dict[str, Any]
            Parameter set to test.
        npz_path : Path
            Path to prepared training data.
            
        Returns
        -------
        ExperimentResult
            Results from the experiment.
        """
        logger.info(f"Running experiment {experiment_id}")
        logger.debug(f"Parameters: {parameters}")
        
        start_time = time.time()
        
        # Run training with these parameters
        model_path, metrics = self.trainer.fit_prepared_data(
            npz_path=npz_path,
            model_name=f"tune_{experiment_id}",
            model_description=f"Hyperparameter tuning experiment {experiment_id}",
            model_params=parameters
        )
        
        training_time = time.time() - start_time
        
        # Extract metrics
        cv_f1_macro_scores = metrics.get('cv_f1_macro', [])
        cv_f1_macro_mean = float(np.mean(cv_f1_macro_scores)) if cv_f1_macro_scores else 0.0
        cv_f1_macro_std = float(np.std(cv_f1_macro_scores)) if cv_f1_macro_scores else 0.0
        
        cv_accuracy_scores = metrics.get('cv_accuracy', [])
        cv_accuracy_mean = float(np.mean(cv_accuracy_scores)) if cv_accuracy_scores else 0.0
        cv_accuracy_std = float(np.std(cv_accuracy_scores)) if cv_accuracy_scores else 0.0
        
        # Create result object
        result = ExperimentResult(
            experiment_id=experiment_id,
            parameters=parameters,
            cv_f1_macro_mean=cv_f1_macro_mean,
            cv_f1_macro_std=cv_f1_macro_std,
            cv_accuracy_mean=cv_accuracy_mean,
            cv_accuracy_std=cv_accuracy_std,
            test_f1_macro=float(metrics['f1_macro']),
            test_accuracy=float(metrics['accuracy']),
            test_f1_scores=metrics['f1'],
            test_precision=metrics['precision'],
            test_recall=metrics['recall'],
            training_time_seconds=training_time,
            model_path=model_path,
            diagnostics_path=self.run_manager.run_path / "model_diagnostics" / f"tune_{experiment_id}",
            timestamp=datetime.now().isoformat()
        )
        
        # Save experiment result
        self._save_experiment_result(result)
        
        logger.info(f"Experiment {experiment_id} completed: CV F1-macro={cv_f1_macro_mean:.4f}±{cv_f1_macro_std:.4f}, Test F1-macro={result.test_f1_macro:.4f}, Test Acc={result.test_accuracy:.4f}")
        
        return result
    
    def run_tuning(self, npz_path: Path, n_trials: int = None) -> ExperimentResult:
        """
        Run complete hyperparameter tuning.
        
        Parameters
        ----------
        npz_path : Path
            Path to prepared training data.
        n_trials : int, optional
            Number of trials to run. If None, uses instance default.
            
        Returns
        -------
        ExperimentResult
            Best result from all experiments.
        """
        if n_trials is None:
            n_trials = self.n_trials
        
        logger.info(f"Starting hyperparameter tuning with {n_trials} trials")
        logger.info(f"Results will be saved to: {self.tuning_dir}")
        
        # Save tuning configuration
        self._save_tuning_config(n_trials)
        
        # Run experiments
        for i in range(n_trials):
            experiment_id = f"{i+1:03d}"
            
            try:
                # Generate parameters for this experiment
                parameters = self.generate_experiment_parameters()
                
                # Run experiment
                result = self.run_single_experiment(
                    experiment_id=experiment_id,
                    parameters=parameters,
                    npz_path=npz_path
                )
                
                # Track result
                self.results.append(result)
                
                # Update best result
                if self.best_result is None or result.score > self.best_result.score:
                    self.best_result = result
                    logger.info(f"🏆 New best result: {result.score:.4f} (experiment {experiment_id})")
                
            except Exception as e:
                logger.error(f"Experiment {experiment_id} failed: {str(e)}")
                continue
        
        # Save final results
        self._save_final_results()
        
        if self.best_result is not None:
            logger.info(f"✅ Tuning completed! Best CV F1-macro: {self.best_result.score:.4f}")
            logger.info(f"Best parameters: {self.best_result.parameters}")
            return self.best_result
        else:
            raise RuntimeError("No experiments completed successfully")
    
    def _save_experiment_result(self, result: ExperimentResult):
        """Save individual experiment result."""
        result_file = self.tuning_dir / f"experiment_{result.experiment_id}.json"
        with open(result_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
    
    def _save_tuning_config(self, n_trials: int):
        """Save the tuning configuration used."""
        config_data = {
            'n_trials': n_trials,
            'parameter_ranges': self.config['parameters'],
            'description': self.config.get('description', f'Hyperparameter tuning with {n_trials} trials'),
            'random_state': self.trainer.cfg.random_state,
            'timestamp': datetime.now().isoformat()
        }
        
        config_file = self.tuning_dir / "tuning_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def _save_final_results(self):
        """Save summary of all results."""
        if not self.results:
            return
        
        # Create summary dataframe
        summary_data = []
        for result in self.results:
            row = {
                'experiment_id': result.experiment_id,
                'cv_f1_macro_mean': result.cv_f1_macro_mean,
                'cv_f1_macro_std': result.cv_f1_macro_std,
                'cv_accuracy_mean': result.cv_accuracy_mean,
                'cv_accuracy_std': result.cv_accuracy_std,
                'test_f1_macro': result.test_f1_macro,
                'test_accuracy': result.test_accuracy,
                'test_f1_mean': np.mean(result.test_f1_scores),
                'training_time_seconds': result.training_time_seconds,
                **{f'param_{k}': v for k, v in result.parameters.items()}
            }
            summary_data.append(row)
        
        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.sort_values('cv_f1_macro_mean', ascending=False)
        
        # Save summary
        summary_file = self.tuning_dir / "results_summary.csv"
        summary_df.to_csv(summary_file, index=False)
        
        # Save best model recommendation
        if self.best_result:
            recommendation = {
                'best_experiment': self.best_result.experiment_id,
                'best_cv_f1_macro': self.best_result.cv_f1_macro_mean,
                'best_cv_accuracy': self.best_result.cv_accuracy_mean,
                'best_test_f1_macro': self.best_result.test_f1_macro,
                'best_test_accuracy': self.best_result.test_accuracy,
                'best_parameters': self.best_result.parameters,
                'model_path': str(self.best_result.model_path),
                'diagnostics_path': str(self.best_result.diagnostics_path),
                'ranking_top_5': [
                    {
                        'experiment_id': r.experiment_id,
                        'cv_f1_macro': r.cv_f1_macro_mean,
                        'cv_accuracy': r.cv_accuracy_mean,
                        'test_f1_macro': r.test_f1_macro,
                        'test_accuracy': r.test_accuracy,
                        'parameters': r.parameters
                    }
                    for r in sorted(self.results, key=lambda x: x.score, reverse=True)[:5]
                ]
            }
            
            rec_file = self.tuning_dir / "best_model_recommendation.json"
            with open(rec_file, 'w') as f:
                json.dump(recommendation, f, indent=2)
        
        logger.info(f"Results summary saved to: {summary_file}")
    
    def load_previous_results(self) -> List[ExperimentResult]:
        """Load results from previous tuning runs in the same directory."""
        results = []
        
        for result_file in self.tuning_dir.glob("experiment_*.json"):
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                result = ExperimentResult.from_dict(data)
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to load result from {result_file}: {e}")
        
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    @classmethod
    def create_from_config_file(cls, 
                               trainer: ModelTrainer,
                               run_manager: RunManager,
                               config_file: Path,
                               random_state: int = 42) -> 'HyperparameterTuner':
        """Create tuner from a configuration file."""
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        return cls(
            trainer=trainer,
            run_manager=run_manager,
            custom_config=config,
            random_state=random_state
        )


# Utility functions for easy usage

def run_hyperparameter_tuning(
    trainer: ModelTrainer,
    run_manager: RunManager,
    npz_path: Path,
    n_trials: int = 25,
    random_state: int = 42
) -> ExperimentResult:
    """
    Convenience function to run hyperparameter tuning.
    
    Parameters
    ----------
    trainer : ModelTrainer
        Configured trainer instance.
    run_manager : RunManager
        Run manager for organizing results.
    npz_path : Path
        Path to prepared training data.
    n_trials : int, default=25
        Number of trials to run.
    random_state : int, default=42
        Random state for reproducibility.
        
    Returns
    -------
    ExperimentResult
        Best result from tuning.
    """
    tuner = HyperparameterTuner(
        trainer=trainer,
        run_manager=run_manager,
        n_trials=n_trials,
        random_state=random_state
    )
    
    return tuner.run_tuning(npz_path=npz_path, n_trials=n_trials)


def get_best_parameters_from_run(run_path: Path) -> Dict[str, Any]:
    """
    Extract best parameters from a completed tuning run.
    
    Parameters
    ----------
    run_path : Path
        Path to the run directory containing tuning results.
        
    Returns
    -------
    Dict[str, Any]
        Best parameter set found.
    """
    tuning_dir = run_path / "hyperparameter_tuning"
    rec_file = tuning_dir / "best_model_recommendation.json"
    
    if not rec_file.exists():
        raise FileNotFoundError(f"No tuning results found at {rec_file}")
    
    with open(rec_file, 'r') as f:
        recommendation = json.load(f)
    
    return recommendation['best_parameters']