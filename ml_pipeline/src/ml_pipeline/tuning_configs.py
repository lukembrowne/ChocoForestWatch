"""
ml_pipeline.tuning_configs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configuration and parameter ranges for hyperparameter tuning of XGBoost models
in forest classification tasks.

This module provides:
- Optimized parameter ranges for land cover classification
- Simple parameter sampling utilities
- Easy configuration for different numbers of trials
"""

from typing import Dict, Any, Union
import numpy as np


class TuningConfig:
    """Configuration for hyperparameter tuning experiments."""
    
    # Optimized parameter ranges for forest classification
    # Based on the previous "balanced" preset which worked well
    PARAMETER_RANGES = {
        # Core tree structure parameters
        'n_estimators': {'type': 'int', 'low': 100, 'high': 2000},
        'max_depth': {'type': 'int', 'low': 2, 'high': 12},
        'learning_rate': {'type': 'log_uniform', 'low': 0.02, 'high': 0.25},
        
        # Tree shape parameters
        'min_child_weight': {'type': 'int', 'low': 1, 'high': 10},
        'gamma': {'type': 'log_uniform', 'low': 0.001, 'high': 10.0},
        'max_delta_step': {'type': 'int', 'low': 0, 'high': 10},
        
        # Class imbalance handling
        'class_weight': {'type': 'choice', 'choices': [None, 'balanced']},
        
        # Sampling parameters 
        'subsample': {'type': 'uniform', 'low': 0.4, 'high': 1.0},
        'colsample_bytree': {'type': 'uniform', 'low': 0.4, 'high': 1.0},
        
        # Regularization parameters
        'reg_alpha': {'type': 'log_uniform', 'low': 0.001, 'high': 10.0},
        'reg_lambda': {'type': 'log_uniform', 'low': 0.1, 'high': 50.0},
    }
    
    @classmethod
    def get_parameter_ranges(cls) -> Dict[str, Dict[str, Any]]:
        """Get the standard parameter ranges for forest classification.
        
        Returns
        -------
        Dict[str, Dict[str, Any]]
            Dictionary mapping parameter names to their range configurations.
        """
        return cls.PARAMETER_RANGES.copy()
    
    @classmethod
    def sample_parameter(cls, param_config: Dict[str, Any], random_state: np.random.RandomState = None) -> Union[int, float, str]:
        """Sample a single parameter value according to its configuration.
        
        Parameters
        ----------
        param_config : Dict[str, Any]
            Parameter configuration with type and range information.
        random_state : np.random.RandomState, optional
            Random state for reproducible sampling.
            
        Returns
        -------
        Union[int, float, str]
            Sampled parameter value.
        """
        if random_state is None:
            random_state = np.random.RandomState()
        
        param_type = param_config['type']
        
        if param_type == 'int':
            return random_state.randint(param_config['low'], param_config['high'] + 1)
        
        elif param_type == 'uniform':
            return random_state.uniform(param_config['low'], param_config['high'])
        
        elif param_type == 'log_uniform':
            log_low = np.log(param_config['low'])
            log_high = np.log(param_config['high'])
            log_val = random_state.uniform(log_low, log_high)
            return np.exp(log_val)
        
        elif param_type == 'choice':
            return random_state.choice(param_config['choices'])
        
        else:
            raise ValueError(f"Unknown parameter type: {param_type}")
    
    @classmethod
    def generate_parameter_set(cls, parameter_ranges: Dict[str, Dict[str, Any]], 
                              random_state: np.random.RandomState = None) -> Dict[str, Any]:
        """Generate a complete set of parameters by sampling from ranges.
        
        Parameters
        ----------
        parameter_ranges : Dict[str, Dict[str, Any]]
            Dictionary mapping parameter names to their range configurations.
        random_state : np.random.RandomState, optional
            Random state for reproducible sampling.
            
        Returns
        -------
        Dict[str, Any]
            Complete parameter set ready for XGBoost.
        """
        if random_state is None:
            random_state = np.random.RandomState()
        
        params = {}
        for param_name, param_config in parameter_ranges.items():
            params[param_name] = cls.sample_parameter(param_config, random_state)
        
        return params
    
    @classmethod
    def create_config(cls, n_trials: int = 25) -> Dict[str, Any]:
        """Create a tuning configuration with specified number of trials.
        
        Parameters
        ----------
        n_trials : int, default=25
            Number of trials to run.
            
        Returns
        -------
        Dict[str, Any]
            Configuration dictionary with parameters and trial count.
        """
        return {
            'n_trials': n_trials,
            'parameters': cls.get_parameter_ranges(),
            'description': f'Hyperparameter tuning with {n_trials} trials'
        }


# Utility functions for parameter validation and suggestions

def validate_parameter_ranges(parameter_ranges: Dict[str, Dict[str, Any]]) -> bool:
    """Validate parameter range configurations.
    
    Parameters
    ----------
    parameter_ranges : Dict[str, Dict[str, Any]]
        Parameter ranges to validate.
        
    Returns
    -------
    bool
        True if all ranges are valid.
        
    Raises
    ------
    ValueError
        If any parameter range is invalid.
    """
    valid_types = {'int', 'uniform', 'log_uniform', 'choice'}
    
    for param_name, param_config in parameter_ranges.items():
        if 'type' not in param_config:
            raise ValueError(f"Parameter '{param_name}' missing 'type' field")
        
        param_type = param_config['type']
        if param_type not in valid_types:
            raise ValueError(f"Parameter '{param_name}' has invalid type '{param_type}'. Valid: {valid_types}")
        
        if param_type in ['int', 'uniform', 'log_uniform']:
            if 'low' not in param_config or 'high' not in param_config:
                raise ValueError(f"Parameter '{param_name}' missing 'low' or 'high' field")
            if param_config['low'] >= param_config['high']:
                raise ValueError(f"Parameter '{param_name}' low >= high")
        
        elif param_type == 'choice':
            if 'choices' not in param_config:
                raise ValueError(f"Parameter '{param_name}' missing 'choices' field")
            if len(param_config['choices']) == 0:
                raise ValueError(f"Parameter '{param_name}' has empty choices")
    
    return True


def get_trials_recommendation(n_samples: int) -> int:
    """Get recommended number of trials based on dataset size.
    
    Parameters
    ----------
    n_samples : int
        Number of training samples.
        
    Returns
    -------
    int
        Recommended number of trials.
    """
    if n_samples < 1000:
        return 15  # Small dataset: fewer trials
    elif n_samples > 100000:
        return 50  # Large dataset: more trials for better optimization
    else:
        return 25  # Medium dataset: balanced approach