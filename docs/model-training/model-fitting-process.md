# Model Fitting Process
This document provides an overview of the model fitting process for forest classification in the ChocoForestWatch ML pipeline, including feature engineering, hyperparameter tuning, and the overall workflow for training models separately for each month.

## Overview

The model fitting process uses XGBoost classifiers trained on NICFI satellite imagery to classify forest, non-forest, and other land cover types. The pipeline includes feature engineering and hyperparameter optimization to improve high accuracy. The system trains separate models for each month and then builds an annual composite of forest / non-forest.

## Architecture

### Core Components

1. **Feature Engineering** (`ml_pipeline/feature_engineering.py`) - Extracts derived features from satellite bands
2. **XGBoost Training** (`ml_pipeline/trainer.py`) - Core model training with comprehensive evaluation
3. **Hyperparameter Tuning** (`ml_pipeline/hyperparameter_tuner.py`) - Optimizes model parameters through random search
4. **Monthly Workflow** (`ml_pipeline/notebooks/train_and_predict_by_month.py`) - Handles single-month training and prediction
5. **Pipeline Orchestration** (`ml_pipeline/notebooks/run_train_predict_pipeline.py`) - Coordinates multi-month processing

### Data Flow

```
Training Polygons (PostgreSQL/PostGIS)
    ↓
NICFI Imagery Extraction (via TiTiler)
    ↓
Feature Engineering (derived indices)
    ↓
Feature Vector (base bands + derived features)
    ↓
XGBoost Model Training (monthly)
    ↓
Cross-validation & Evaluation
    ↓
Model Persistence & Diagnostics
    ↓
Prediction Generation (COGs)
    ↓
STAC Integration & Composites
```

## Feature Engineering

The feature engineering system transforms raw satellite bands into a feature set that aims to improve classification accuracy. The system is modular and extensible, allowing for easy addition of new feature extractors.

### Base Architecture

- **FeatureExtractor** (Abstract Base Class) - Defines interface for all feature extractors
- **FeatureManager** - Coordinates multiple extractors and manages the feature pipeline
- **Validation** - Ensures input data quality and consistency

### Input Data Format

Raw satellite imagery uses NICFI band order: `[Blue, Green, Red, NIR]` (indices 0-3)

### Available Feature Extractors

#### 1. Vegetation Indices

**NDVI Extractor** (`NDVIExtractor`)
- **Formula**: `NDVI = (NIR - Red) / (NIR + Red)`
- **Range**: -1 to 1
- **Purpose**: Healthy vegetation detection
- **Interpretation**: 
  - Values near 1: Dense, healthy vegetation
  - Values near 0: Bare soil/rock
  - Negative values: Water bodies

**EVI Extractor** (`EviExtractor`)
- **Formula**: `EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)`
- **Advantages**: Superior to NDVI for dense vegetation, atmospheric correction
- **Purpose**: Enhanced vegetation monitoring in tropical forests
- **Benefits**: Reduces atmospheric effects, better canopy structure sensitivity

**SAVI Extractor** (`SaviExtractor`)
- **Formula**: `SAVI = (NIR - Red) / (NIR + Red + L) * (1 + L)`
- **Parameter**: L (soil brightness correction factor, default=0.5)
- **Purpose**: Soil-adjusted vegetation index for sparse vegetation
- **Use Cases**: Arid regions, early growth stage detection

#### 2. Water Detection

**NDWI Extractor** (`NDWIExtractor`)
- **Formula**: `NDWI = (Green - NIR) / (Green + NIR)`
- **Purpose**: Water body detection
- **Interpretation**:
  - Positive values: Water bodies
  - Negative values: Vegetation/dry surfaces

**Water Detection Extractor** (`WaterDetectionExtractor`)
- **Features**: Blue-NIR ratio with log normalization
- **Purpose**: Comprehensive water body identification
- **Advantages**: Distinguishes water from shadows and dark surfaces

#### 3. Spectral Analysis

**Spectral Ratio Extractor** (`SpectralRatioExtractor`)
- **Available Ratios**:
  - `red_nir`: Red/NIR ratio
  - `green_red`: Green/Red ratio
  - `blue_red`: Blue/Red ratio
  - `nir_green`: NIR/Green ratio
- **Purpose**: Land cover type discrimination
- **Customizable**: Select specific ratios based on requirements

**Brightness Temperature Extractor** (`BrightnessTempExtractor`)
- **Features**:
  - Overall brightness: Mean of all bands
  - NIR brightness: NIR band intensity
  - Spectral variance: Standard deviation across bands
- **Purpose**: Surface texture and material identification

#### 4. Shadow Detection

**Shadow Index Extractor** (`ShadowIndexExtractor`)
- **Features**:
  - Shadow brightness: Inverse total brightness
  - Shadow blue dominance: Blue-dominated spectral signature
- **Purpose**: Improve classification accuracy by identifying shadowed areas
- **Benefits**: Reduces misclassification of shadows as water

#### 5. Temporal Features

**Temporal Extractor** (`TemporalExtractor`)
- **Features**:
  - Monthly cycles: `sin(2π * month / 12)`, `cos(2π * month / 12)`
  - Yearly normalization: `(year - 2020) / 10`
  - Day of year: `sin(2π * day / 365)`
- **Purpose**: Capture seasonal patterns in forest changes
- **Input**: Date strings in YYYY-MM format
  

## XGBoost Model Training

The core training system is implemented in `ml_pipeline/trainer.py` and provides comprehensive model development capabilities.

### ModelTrainer Architecture

**Key Components**:
- **TrainerConfig**: Configuration dataclass for training parameters
- **ModelTrainer**: Main training class with decoupled data preparation and model fitting
- **Data Splitting**: Feature-based or pixel-based train/validation/test splits
- **Cross-validation**: Stratified K-fold with group-aware splitting
- **Model Evaluation**: Comprehensive metrics and diagnostics generation

### Training Configuration

```python
@dataclass
class TrainerConfig:
    # Data splitting
    split_method: str = "feature"        # "feature" or "pixel"
    test_fraction: float = 0.2           # Test set size
    val_fraction: float = 0.2            # Validation set size
    
    # Model parameters
    random_state: int = 42
    early_stopping_rounds: int = 20
    
    # Class handling
    class_weighting: str = None          # None or "balanced"
    cv_folds: int = 5                    # Cross-validation folds
    
    # Class order (fixed indices)
    class_order: tuple = (
        "Forest", "Non-Forest", "Cloud", 
        "Shadow", "Water", "Haze", "Sensor Error"
    )
    
    # Feature engineering
    feature_extractors: list = None      # Feature extractors to use
```

### Decoupled Training Workflow

The training process is split into two phases for efficiency:

1. **Data Preparation** (Heavy I/O, run once):
```python
# Extract pixels and cache as NPZ file
npz_path = trainer.prepare_training_data(
    training_sets=[{"gdf": polygons_gdf, "basemap_date": "2022-01"}],
    cache_name="pixels_2022_01.npz"
)
```

2. **Model Fitting** (Lightweight, repeatable):
```python
# Train model from cached data
model_path, metrics = trainer.fit_prepared_data(
    npz_path=npz_path,
    model_name="nicfi-2022-01",
    model_params={"n_estimators": 100, "max_depth": 6}
)
```

### Data Splitting Strategy

**Feature-based Splitting** (Recommended):
- Splits based on unique polygon features rather than individual pixels
- Prevents data leakage where pixels from the same polygon appear in train and test
- Uses stratified sampling to maintain class balance
- Particularly important for geospatial data

**Pixel-based Splitting**:
- Traditional random split of individual pixels
- May lead to optimistic performance estimates
- Faster but less robust for geospatial applications

### Cross-Validation

- **Method**: Stratified K-fold (default: 5 folds)
- **Group-aware**: Uses GroupKFold for feature-based splitting
- **Metrics**: Accuracy, precision, recall, F1-score per class
- **Purpose**: Robust performance estimation and overfitting detection

### Model Evaluation Metrics

**Primary Metrics**:
- Overall accuracy on held-out test set
- Cross-validation accuracy (mean ± std)
- Class-wise precision, recall, F1-score
- Confusion matrix

**Advanced Evaluation**:
- ROC curves (binary and multiclass)
- Precision-recall curves
- Calibration plots for probability assessment
- SHAP values for feature importance

### Comprehensive Diagnostics

The system automatically generates extensive diagnostics:

**Feature Importance Analysis**:
- Weight, gain, and cover importance plots
- SHAP summary and importance plots
- Feature importance scores as CSV with meaningful names

**Model Performance Plots**:
- Learning curves from training history
- Confusion matrix heatmaps
- ROC and precision-recall curves
- Calibration reliability diagrams

**Model Metadata**:
- Hyperparameters as JSON
- Training configuration details
- Human-readable model summary
- Feature engineering configuration

## Hyperparameter Tuning

The hyperparameter tuning system uses random search to optimize XGBoost parameters for forest classification accuracy. **Best Practice**: Run tuning once using representative data, then apply optimized parameters to all monthly models.

### When to Use Hyperparameter Tuning

**Run hyperparameter tuning when:**
- Starting a new modeling project or dataset
- Changing feature engineering significantly (adding/removing extractors)
- Model performance is unsatisfactory
- Exploring different parameter spaces for research
- Beginning a new prediction year with different data characteristics

**DO NOT tune separately for each month** - this is computationally wasteful and can lead to overfitting to temporal patterns rather than optimizing the underlying model structure.

**Recommended Workflow:**
1. **Tune once** using one representative month (typically month 1)
2. **Apply parameters** to all monthly training runs
3. **Re-tune only** when making significant changes to features or data

### Practical Workflow Guide

#### Step 1: Run Hyperparameter Tuning

Choose the appropriate number of trials based on your time budget and performance requirements:

```bash
# Quick tuning (15 trials, ~30 minutes) - for development/testing
python run_train_predict_pipeline.py \
  --step tuning \
  --year 2022 \
  --project_id 7 \
  --run_id "tune_quick_2025_01" \
  --db-host remote \
  --tune-trials 15 \
  --tune-month 1 \
  --features ndvi ndwi

# Standard tuning (25 trials, ~1 hour) - RECOMMENDED for production  
python run_train_predict_pipeline.py \
  --step tuning \
  --year 2022 \
  --project_id 7 \
  --run_id "tune_standard_2025_01" \
  --db-host remote \
  --tune-trials 25 \
  --tune-month 1 \
  --features ndvi ndwi evi

# Thorough tuning (50+ trials, ~2-3 hours) - for maximum performance
python run_train_predict_pipeline.py \
  --step tuning \
  --year 2022 \
  --project_id 7 \
  --run_id "tune_thorough_2025_01" \
  --db-host remote \
  --tune-trials 50 \
  --tune-month 1 \
  --features ndvi ndwi evi savi
```

#### Step 2: Extract Best Parameters

After tuning completes, find the optimized parameters in:

```bash
# Primary location (easy to use)
ml_pipeline/runs/{run_id}/best_hyperparameters.json

# Detailed results with top 5 experiments
ml_pipeline/runs/{run_id}/hyperparameter_tuning/best_model_recommendation.json

# Full analysis report
ml_pipeline/runs/{run_id}/hyperparameter_tuning/tuning_analysis_report.html
```

Example best parameters output:
```json
{
  "n_estimators": 342,
  "max_depth": 7,
  "learning_rate": 0.0876,
  "subsample": 0.85,
  "colsample_bytree": 0.91,
  "reg_alpha": 0.234,
  "reg_lambda": 1.45,
  "random_state": 42
}
```

**Core Structure Parameters:**
- `n_estimators` (100-1000): Number of boosting rounds
  - *Higher*: Better fit, slower training, risk of overfitting
  - *Lower*: Faster training, risk of underfitting
  - *Sweet spot*: Usually 200-500 for forest classification

- `max_depth` (3-10): Maximum tree depth
  - *Higher*: More complex patterns, risk of overfitting
  - *Lower*: Simpler patterns, more generalization
  - *Sweet spot*: Usually 6-8 for satellite imagery

- `learning_rate` (0.01-0.3): Step size shrinkage
  - *Higher*: Faster learning, risk of overshooting
  - *Lower*: More conservative, often better performance
  - *Sweet spot*: Usually 0.05-0.15

**Sampling Parameters:**
- `subsample` (0.6-1.0): Fraction of samples per tree
  - *Purpose*: Prevents overfitting, adds randomness
  - *Recommendation*: 0.8-0.9 for most cases

- `colsample_bytree` (0.6-1.0): Fraction of features per tree
  - *Purpose*: Feature regularization, speed improvement
  - *Recommendation*: 0.8-1.0 for satellite data (limited features)

**Regularization Parameters:**
- `reg_alpha` (0-10): L1 regularization (feature selection)
- `reg_lambda` (0-10): L2 regularization (weight smoothing)
- `gamma` (0-10): Minimum loss reduction for splits
  - *Higher values*: More conservative splitting, less overfitting

**Tree Shape Parameters:**
- `min_child_weight` (1-10): Minimum sum of instance weight in child
  - *Higher values*: More conservative, prevents overfitting
  - *Lower values*: More aggressive splitting, may overfit
  - *Sweet spot*: Usually 1-5 for forest classification

- `max_delta_step` (0-10): Maximum delta step for weight estimation
  - *Higher values*: More conservative updates, helps with imbalanced classes
  - *0*: No constraint (default)
  - *Recommendation*: Try 1-3 for imbalanced datasets

**Class Imbalance Handling:**
- `class_weight` (None/'balanced'): Whether to use balanced class weighting
  - *None*: No weighting (default)
  - *'balanced'*: Automatically weight inversely proportional to class frequencies
  - *Benefits*: Improves performance on minority classes

### Advanced Usage and Troubleshooting

**Parameter Ranges Used:**
The system uses these optimized ranges for all tuning:
- `n_estimators`: 100-2000 (integer)
- `max_depth`: 2-12 (integer)  
- `learning_rate`: 0.02-0.25 (log-uniform)
- `subsample`: 0.4-1.0 (uniform)
- `colsample_bytree`: 0.4-1.0 (uniform)
- `reg_alpha`: 0.001-10.0 (log-uniform)
- `reg_lambda`: 0.1-50.0 (log-uniform)

**Tree Shape Parameters:**
- `min_child_weight`: 1-10 (integer) - Minimum sum of instance weight in child
- `gamma`: 0.001-10.0 (log-uniform) - Minimum loss reduction for splits
- `max_delta_step`: 0-10 (integer) - Maximum delta step for weight estimation

**Class Imbalance Handling:**
- `class_weight`: None or 'balanced' (choice) - Whether to use balanced class weighting

**Loading Previous Results:**
```python
from ml_pipeline.hyperparameter_tuner import get_best_parameters_from_run

# Get best parameters from previous tuning run
best_params = get_best_parameters_from_run(
    run_path=Path("ml_pipeline/runs/tune_thorough_2025_01")
)
```

**Performance Monitoring:**
- **Cross-validation F1-macro**: Primary metric for parameter selection (handles class imbalance better than accuracy)
- **Test F1-macro**: Validate generalization performance on all classes
- **Test accuracy**: Overall classification performance
- **CV-Test gap**: Large gaps indicate overfitting
- **Training time**: Consider operational constraints

**Common Issues and Solutions:**

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Overfitting | CV >> Test F1-macro | Increase regularization (`reg_alpha`, `reg_lambda`, `gamma`) |
| Underfitting | Low CV and Test F1-macro | Increase complexity (`max_depth`, `n_estimators`) |
| Class imbalance | Low F1-macro despite high accuracy | Use `class_weight: 'balanced'` |
| Slow training | Long experiment times | Reduce `n_estimators`, increase `learning_rate` |
| Parameter boundaries | Best params at edges | Expand parameter ranges |
| Inconsistent results | High variance in CV | Increase regularization, reduce `learning_rate` |
| Poor minority class performance | Low per-class F1 scores | Enable balanced class weighting, tune `min_child_weight` |


## Monthly Training Workflow

The system trains separate models for each month to capture seasonal variations in forest patterns. This approach is implemented through `train_and_predict_by_month.py`.

### Single-Month Pipeline

**Key Steps**:
1. **Training Data Loading**: Load polygons for specific month/year from database
2. **Data Extraction**: Extract pixels from NICFI imagery via TiTiler
3. **Feature Engineering**: Apply configured feature extractors
4. **Model Training**: Train XGBoost with monthly-specific data
5. **Prediction Generation**: Generate forest cover predictions as COGs
6. **STAC Integration**: Add predictions to spatiotemporal catalog

### Command-Line Interface

```bash
python train_and_predict_by_month.py \
  --year 2022 \
  --month 01 \
  --run_dir runs/test_run \
  --project_id 7 \
  --db-host remote \
  --features ndvi ndwi evi
```

### Feature Configuration

**Available Features**:
- `ndvi`: Normalized Difference Vegetation Index
- `ndwi`: Normalized Difference Water Index  
- `evi`: Enhanced Vegetation Index
- `savi`: Soil-Adjusted Vegetation Index
- `brightness`: Brightness and texture features
- `water_detection`: Water detection indices
- `shadow`: Shadow detection features

### Data Caching Strategy

**Efficient Caching**:
- **NPZ Files**: Compressed numpy arrays for pixel data
- **Feature-specific Caching**: Different cache files for different feature combinations
- **Automatic Cache Management**: SHA-1 hash-based naming for consistency
- **Overwrite Control**: Optional cache refresh for updated training data

## Multi-Month Pipeline Orchestration

The `run_train_predict_pipeline.py` script orchestrates training across multiple months and handles downstream processing.

### Pipeline Steps

1. **Training Step** (`--step training`):
   - Processes specified month range sequentially
   - Runs `train_and_predict_by_month.py` for each month
   - Collects success/failure statistics
   - Provides retry commands for failed months

2. **Hyperparameter Tuning Step** (`--step tuning`):
   - Optimizes parameters using single month of data
   - Generates comprehensive tuning analysis
   - Saves best parameters for later use

3. **Composites Step** (`--step composites`):
   - Generates annual forest cover composites
   - Merges monthly predictions into unified COGs
   - Handles parallel processing for efficiency

4. **CFW Processing Step** (`--step cfw-processing`):
   - Processes composites into ChocoForestWatch datasets
   - Creates STAC collections for frontend integration
   - Manages dataset versioning and metadata

5. **Benchmarks Step** (`--step benchmarks`):
   - Evaluates against external forest datasets
   - Generates comparative performance metrics
   - Creates summary visualizations

### Usage Examples

**Full Pipeline**:
```bash
python run_train_predict_pipeline.py \
  --step all \
  --start_month 1 --end_month 12 \
  --year 2022 \
  --project_id 7 \
  --run_id "production_2025_01" \
  --db-host remote \
  --features ndvi ndwi evi
```

**Hyperparameter Tuning**:
```bash
python run_train_predict_pipeline.py \
  --step tuning \
  --year 2022 \
  --project_id 7 \
  --run_id "tune_test_2025_01" \
  --db-host remote \
  --tune-preset thorough \
  --tune-trials 100 \
  --features ndvi ndwi
```

### Database Configuration

**Local Development** (`--db-host local`):
- Connects to localhost PostgreSQL/PostGIS
- Suitable for development and testing
- Reduced spatial filtering for speed

**Production** (`--db-host remote`):
- Connects to production database
- Full spatial filtering for Western Ecuador
- Used for operational model training

### Result Organization

```
runs/
└── {run_id}/
    ├── {year}_{month}/           # Monthly results
    │   ├── saved_models/         # Trained models
    │   ├── data_cache/           # Cached training data
    │   ├── model_diagnostics/    # Evaluation plots
    │   └── prediction_cogs/      # Generated predictions
    ├── composites/               # Annual composites
    ├── hyperparameter_tuning/    # Tuning results
    └── benchmark_results/        # Evaluation metrics
```

