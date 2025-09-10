# ML Pipeline Workflow

The ML pipeline supports flexible execution with multiple entry points depending on your needs. The system includes advanced feature engineering capabilities for enhanced model performance.

## Feature Engineering

The pipeline supports comprehensive derived spectral features alongside the base NICFI bands (Blue, Green, Red, NIR):

### Vegetation Indices
- NDVI (Normalized Difference Vegetation Index): `(NIR - Red) / (NIR + Red)` – Measures vegetation health and density.
- EVI (Enhanced Vegetation Index): `2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)` – Superior to NDVI for dense vegetation, reduces atmospheric effects.
- SAVI (Soil-Adjusted Vegetation Index): `(NIR - Red) / (NIR + Red + L) * (1 + L)` – Reduces soil background effects in sparse vegetation.

### Water Detection
- Blue–NIR ratio: For comprehensive water body identification.

### Surface Characteristics
- Brightness/Texture: Overall reflectance intensity and spectral variability for distinguishing surface types.
- Shadow Detection: Indices for identifying topographic, cloud, and building shadows.

### Base Bands Only
- Use raw Blue, Green, Red, NIR bands without derived features for baseline performance.

## Forest Flag Algorithm Selection

The pipeline supports multiple algorithms for generating forest/non-forest classifications from monthly predictions during composite generation. Each algorithm handles temporal patterns differently:

### Available Algorithms

| Algorithm | Description | Best For | Data Requirements |
|---|---|---|---|
| `majority_vote` | Uses most frequent class across all months | Stable areas, baseline performance | 2+ valid months |
| `temporal_trend` | Analyzes temporal patterns and filters noise | Deforestation detection (recommended) | 3+ valid months |
| `change_point` | Statistical detection of significant transitions | Clear land cover changes | 4+ valid months |
| `latest_valid` | Uses most recent valid observation | Recent changes, monitoring | 1+ valid month |
| `weighted_temporal` | Weights recent observations higher | Balanced recent/historical approach | 2+ valid months |

### Algorithm Performance Characteristics

- Temporal Trend: Best for detecting late-season deforestation while filtering noise. Correctly identifies patterns like `[Forest, Forest, Forest, Non-Forest]` → Non-Forest.
- Change Point: Good for statistically significant transitions, includes confidence scoring.
- Majority Vote: Original algorithm; may miss temporal patterns but provides consistent baseline.
- Latest Valid: Very sensitive to recent changes but prone to noise.
- Weighted Temporal: Moderate approach balancing recent vs. historical data.

### Usage Examples

```bash
# Use temporal trend algorithm (recommended for deforestation detection)
--forest-algorithm temporal_trend

# Use change point detection for statistical transitions
--forest-algorithm change_point

# Use majority vote (default, backward compatible)
--forest-algorithm majority_vote
```

For detailed algorithm descriptions, implementation details, and performance comparisons, see the Forest Flag Algorithms reference: `docs/model-training/forest-flag-algorithms.md`.

## Complete Training and Prediction Pipeline

For a full end-to-end model training and evaluation workflow:

```bash
# Navigate to ML pipeline directory
cd ml_pipeline/notebooks

# Full pipeline with all features and enhanced deforestation detection
poetry run python run_train_predict_pipeline.py \
  --step all \
  --start_month 1 --end_month 12 \
  --year 2022 \
  --project_id 7 \
  --run_id "all_features_2025_07_15" \
  --db-host "remote" \
  --features ndvi ndwi evi savi brightness water_detection shadow \
  --boundary-geojson shapefiles/Ecuador-DEM-900m-contour.geojson \
  --tune-trials 100 \
  --forest-algorithm temporal_trend

# Full pipeline without features (base bands only - legacy behavior)
poetry run python run_train_predict_pipeline.py \
  --step all \
  --start_month 1 --end_month 12 \
  --year 2022 \
  --project_id 7 \
  --run_id "test_base_bands_2025_07_12" \
  --db-host "remote" \
  --boundary-geojson shapefiles/Ecuador-DEM-900m-contour.geojson
```

This will:
1. Train separate XGBoost models for each month using training polygons and specified features.
2. Generate predictions as Cloud Optimized GeoTIFFs (COGs) using the same features.
3. Create annual forest/non-forest composites.
4. Evaluate accuracy against benchmark datasets.

## Individual Pipeline Steps

Run specific pipeline steps independently based on your needs:

### Training & Prediction Only
```bash
# Train models with NDVI and generate monthly predictions
poetry run python run_train_predict_pipeline.py \
  --step training \
  --start_month 1 --end_month 1 \
  --year 2022 \
  --project_id 7 \
  --run_id "test_ndvi_2025_07_12" \
  --db-host "remote" \
  --features ndvi

# Train models with base bands only (no features)
poetry run python run_train_predict_pipeline.py \
  --step training \
  --start_month 1 --end_month 1 \
  --year 2022 \
  --project_id 7 \
  --run_id "test_base_2025_07_12" \
  --db-host "remote"
```

### Composites Only
```bash
# Generate annual composites with temporal trend algorithm (recommended)
poetry run python run_train_predict_pipeline.py \
  --step composites \
  --year 2022 \
  --project_id 7 \
  --run_id "test_ndvi_2025_07_12" \
  --db-host "remote" \
  --forest-algorithm temporal_trend

# Generate composites with change point detection
poetry run python run_train_predict_pipeline.py \
  --step composites \
  --year 2022 \
  --project_id 7 \
  --run_id "test_ndvi_2025_07_12" \
  --db-host "remote" \
  --forest-algorithm change_point

# Generate composites with majority vote (default)
poetry run python run_train_predict_pipeline.py \
  --step composites \
  --year 2022 \
  --project_id 7 \
  --run_id "test_ndvi_2025_07_12" \
  --db-host "remote"
```

### CFW Dataset Processing Only
```bash
# Process ChocoForestWatch dataset for unified structure
poetry run python run_train_predict_pipeline.py \
  --step cfw-processing \
  --year 2022 \
  --project_id 7 \
  --run_id "test_ndvi_2025_07_12" \
  --db-host "remote"

# Process with boundary clipping (recommended for consistency with other datasets)
poetry run python run_train_predict_pipeline.py \
  --step cfw-processing \
  --year 2022 \
  --project_id 7 \
  --run_id "test_ndvi_2025_07_12" \
  --db-host "remote" \
  --boundary-geojson shapefiles/Ecuador-DEM-900m-contour.geojson
```

### Benchmarks Only
```bash
# Run evaluation against all benchmark datasets
poetry run python run_train_predict_pipeline.py \
  --step benchmarks \
  --year 2022 \
  --project_id 7 \
  --run_id "test_ndvi_2025_07_12" \
  --db-host "remote"
```

## Single Month Training with Features

For testing or single month runs:

```bash
# Single month with NDVI features
python train_and_predict_by_month.py \
  --year 2022 \
  --month 06 \
  --run_dir runs/test_ndvi_june \
  --project_id 7 \
  --db-host remote \
  --features ndvi

# Single month with multiple features
python train_and_predict_by_month.py \
  --year 2022 \
  --month 06 \
  --run_dir runs/test_features_june \
  --project_id 7 \
  --db-host remote \
  --features ndvi ndwi

# Single month with base bands only
python train_and_predict_by_month.py \
  --year 2022 \
  --month 06 \
  --run_dir runs/test_base_june \
  --project_id 7 \
  --db-host remote
```

## Hyperparameter Tuning

For a complete guide to tuning (presets, parameters, outputs, and usage), see: `docs/model-training/model-fitting-process.md#hyperparameter-tuning`.

## Pipeline Step Dependencies

- `training`: Requires `--start_month` and `--end_month`; optional `--features` for spectral indices.
- `tuning`: Requires `--year` and `--project_id`; optional `--tune-month` (defaults to month 1).
- `composites`: Requires predictions from training; optional `--forest-algorithm`.
- `cfw-processing`: Requires existing composites from the composites step.
- `benchmarks`: Can run independently with any existing STAC collections.
- `all`: Runs all steps (training → composites → cfw-processing → benchmarks).

## Feature Engineering Options

### Individual Features
| Feature | Description | Use Case | Added Features |
|---|---|---|---:|
| `ndvi` | Normalized Difference Vegetation Index | Enhanced vegetation detection | +1 |
| `ndwi` | Normalized Difference Water Index | Basic water body detection | +1 |
| `evi` | Enhanced Vegetation Index | Dense vegetation, atmospheric correction | +1 |
| `savi` | Soil-Adjusted Vegetation Index | Sparse vegetation, soil backgrounds | +1 |
| `brightness` | Brightness and texture analysis | Surface type discrimination | +3 |
| `water_detection` | Advanced water detection suite | Comprehensive water body mapping | +3 |
| `shadow` | Shadow detection indices | Improved classification accuracy | +2 |

### Example Feature Combinations
| Option | Description | Total Features | Use Case |
|---|---|---:|---|
| No `--features` | Base bands only | 4 | Baseline performance |
| `ndvi` | Base bands + NDVI | 5 | Simple improvement |
| `ndvi ndwi` | Base bands + NDVI + NDWI | 6 | Balanced vegetation/water |
| `ndvi ndwi evi savi brightness water_detection shadow` | Full feature suite | 16+ | Maximum performance |

## Process Forest Cover Rasters

The `ml_pipeline/notebooks/process_forest_cover_rasters.py` script re-processes forest cover benchmark datasets with optimization and standardization:

```bash
# Navigate to ml_pipeline/notebooks directory
cd ml_pipeline/notebooks

# Process all datasets with boundary masking
poetry run python process_forest_cover_rasters.py --boundary-geojson shapefiles/Ecuador-DEM-900m-contour.geojson

# Process a specific dataset
poetry run python process_forest_cover_rasters.py --dataset hansen-tree-cover-2022

# Dry run to see what would be processed
poetry run python process_forest_cover_rasters.py --dry-run --verbose

# Process from custom input directory
poetry run python process_forest_cover_rasters.py --input-dir ./my_rasters --dataset mapbiomas-2022
```

Available datasets: `hansen-tree-cover-2022`, `mapbiomas-2022`, `esa-landcover-2020`, `jrc-forestcover-2020`, `palsar-2020`, `wri-treecover-2020`.

Note: ChocoForestWatch datasets (`cfw-{run_id}`) are processed dynamically via the main pipeline and are no longer hardcoded in the configuration.
