# Choco Forest Watch

A full-stack application for deforestation monitoring, built with Quasar (Vue.js) frontend and a robust backend system.

## Project Overview

Choco Forest Watch is a comprehensive forest monitoring system that helps track and manage forest resources. The application consists of:

- Frontend: Quasar (Vue.js) application
- Backend: Django API
- Database: PostgreSQL with PostGIS
- Redis: For caching and background tasks
- Infrastructure: Docker containers deployed on DigitalOcean

## Development Setup

### Prerequisites

- Node.js (v16 or higher)
- Yarn or npm
- Docker and Docker Compose
- Git

### Local Deployment with Docker

1. Clone the repository:
   ```bash
   git clone git@github.com:lukembrowne/ChocoForestWatch.git
   cd ChocoForestWatch
   ```

2. Create a `.env.prod` file in the root directory with the following variables:
   ```bash
   # Database
   POSTGRES_DB=chocoforest
   POSTGRES_USER=your_user
   POSTGRES_PASSWORD=your_password

   # Frontend
   VITE_API_URL=http://localhost:8000
   VUE_APP_PLANET_API_KEY=your_planet_api_key
   VITE_SENTRY_DSN=your_sentry_dsn

   # Add other environment variables as needed
   ```

3. Create required directories for data persistence:
   ```bash
   mkdir -p data/{planet_quads,predictions,models} media logs
   ```

4. Start the application using Docker Compose:
   ```bash
   docker compose -f docker-compose.prod.yml up --build
   ```

   This will start:
   - PostgreSQL database with PostGIS extension (port 5432)
   - Redis server (port 6379)
   - Django backend (port 8000)
   - Quasar frontend (port 9000)

5. Access the application:
   - Frontend: http://localhost:9000
   - Backend API: http://localhost:8000
   - Analytics Dashboard: https://analytics.chocoforestwatch.fcat-ecuador.org (production only)

### Development Workflow

1. **Create a GitHub Issue**
   - Go to the GitHub repository issues section
   - Create a new issue describing the feature or bug fix
   - Use appropriate labels (e.g., `enhancement`, `bug`, `documentation`)
   - Assign the issue to yourself or team member

2. **Branch Creation**
   - Create a new branch from `dev` using the issue number:
     ```bash
     git checkout dev
     git pull origin dev
     git checkout -b issue-123/feature-description
     ```
   - The branch name should reference the issue number for traceability
   - Branch naming conventions:
     - `issue-123/feature-name` for new features
     - `issue-123/bugfix-name` for bug fixes
     - `issue-123/hotfix-name` for urgent production fixes

3. **Development**
   - Update documentation as needed
   - Commit your changes with conventional commits:
     ```bash
     git commit -m "feat: add new feature (#123)"
     # or
     git commit -m "fix: resolve issue with X (#123)"
     ```
   - Reference the issue number in commit messages

4. **Pull Request**
   - Push your branch to GitHub:
     ```bash
     git push origin issue-123/feature-description
     ```
   - Create a Pull Request (PR) from your branch to `dev`
   - Link the PR to the related issue using GitHub's linking syntax
   - Fill in the PR template with:
     - Description of changes
     - Testing performed
     - Screenshots (if applicable)
     - Any additional notes

5. **Code Review**
   - Request review from team members
   - Address review comments
   - Ensure all CI checks pass
   - Update the PR as needed

6. **Merge and Release**
   - Once approved, squash and merge your PR into `dev`
   - When ready for release:
     - Create a PR from `dev` to `main`
     - After review and approval, merge to `main`
     - Tag the release with version number
     - The merge to `main` will trigger the deployment workflow

### Branch Strategy

- `main`: Production-ready code
  - Should never receive direct commits
  - Only receives changes through merges from `dev`
  - Protected branch with required reviews
- `dev`: Development branch for integrating features
  - Main integration branch for all features
  - Protected branch with required reviews
  - Should be kept up to date with `main` through regular merges
- `issue-*/*`: Feature/fix branches for specific issues
- `release/*`: Release preparation branches (if needed)
- `hotfix/*`: Urgent production fixes
  - Branch from `main`
  - Must be merged back to both `main` and `dev`

### Branch Synchronization

1. **Regular Dev-Main Sync**
   ```bash
   # Keep dev up to date with main
   git checkout dev
   git pull origin dev
   git merge main
   git push origin dev
   ```

2. **Hotfix ProcessProcess**
   ```bash
   # Create hotfix branch from main
   git checkout main
   git pull origin main
   git checkout -b hotfix/urgent-fix

   # After fixing, merge to both main and dev
   git checkout main
   git merge hotfix/urgent-fix
   git push origin main

   git checkout dev
   git merge hotfix/urgent-fix
   git push origin dev
   ```

3. **Release Process**
   ```bash
   # Create release branch from dev
   git checkout dev
   git pull origin dev
   git checkout -b release/v1.0.0

   # After testing, merge to main and back to dev
   git checkout main
   git merge release/v1.0.0
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin main --tags

   git checkout dev
   git merge release/v1.0.0
   git push origin dev
   ```

### Important Notes

1. Never make direct commits to `main` or `dev`
2. Always create feature branches from `dev`
3. Keep `dev` synchronized with `main` regularly
4. Use hotfix branches for urgent production fixes
5. Tag all releases in `main`
6. Ensure CI passes before merging to any protected branch

### Deployment Process

The application is automatically deployed when changes are pushed to the `main` branch. The deployment process:

1. GitHub Actions workflow is triggered on push to `main`
2. The workflow:
   - Connects to the DigitalOcean droplet
   - Pulls the latest code
   - Builds Docker images using `docker-compose.prod.yml`
   - Restarts containers with new images
   - Maintains data persistence through Docker volumes

## Project Structure

```
ChocoForestWatch/
├── frontend/           # Quasar frontend application
├── backend/           # Django backend
├── .github/           # GitHub Actions workflows
├── data/             # Persistent data storage
│   ├── planet_quads/ # Planet imagery data
│   ├── predictions/  # Model predictions
│   └── models/       # ML models
├── media/            # User-uploaded media
├── logs/             # Application logs
└── docker-compose.prod.yml # Production Docker configuration
```

## Data Processing Workflows

### NICFI Imagery Processing (one time)

The system includes automated workflows for processing NICFI (Norway's International Climate and Forests Initiative) satellite imagery:

1. **Data Transfer**
   - Use `migrate_nicfi_data.sh` to transfer NICFI imagery from Google Drive to DigitalOcean Spaces
   - This script handles the  transfer of large imagery datasets

2. **STAC Integration**
   - Process transferred imagery using `build_nicfi_STAC.py`
   - Builds SpatioTemporal Asset Catalog (STAC) metadata
   - Inserts STAC records into PGSTAC database
   - Enables seamless integration with TiTiler for dynamic tile serving
   - Provides standardized access to imagery through STAC API endpoints


## ML Pipeline Workflows

The ML pipeline supports flexible execution with multiple entry points depending on your needs. The system now includes **advanced feature engineering capabilities** for enhanced model performance.

### Feature Engineering

The pipeline supports comprehensive derived spectral features alongside the base NICFI bands (Blue, Green, Red, NIR):

#### Vegetation Indices
- **NDVI (Normalized Difference Vegetation Index)**: `(NIR - Red) / (NIR + Red)` - Measures vegetation health and density
- **EVI (Enhanced Vegetation Index)**: `2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)` - Superior to NDVI for dense vegetation, reduces atmospheric effects
- **SAVI (Soil-Adjusted Vegetation Index)**: `(NIR - Red) / (NIR + Red + L) * (1 + L)` - Reduces soil background effects in sparse vegetation

#### Water Detection
- **Blue-NIR ratio**: For comprehensive water body identification

#### Surface Characteristics
- **Brightness/Texture**: Overall reflectance intensity and spectral variability for distinguishing surface types
- **Shadow Detection**: Indices for identifying topographic, cloud, and building shadows

#### Base Bands Only
- Use raw Blue, Green, Red, NIR bands without derived features for baseline performance

### Complete Training and Prediction Pipeline

For a full end-to-end model training and evaluation workflow:

```bash
# Navigate to ML pipeline directory
cd ml_pipeline/notebooks

# Full pipeline with all features and boundary clipping
poetry run python run_train_predict_pipeline.py \
  --step all \
  --start_month 1 --end_month 12 \
  --year 2022 \
  --project_id 7 \
  --run_id "all_features_2025_07_15" \
  --db-host "remote" \
  --features ndvi ndwi evi savi brightness water_detection shadow \
  --boundary-geojson shapefiles/Ecuador-DEM-900m-contour.geojson \
  --tune-trials 100

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
1. Train separate XGBoost models for each month using training polygons and specified features
2. Generate predictions as Cloud Optimized GeoTIFFs (COGs) using the same features
3. Create annual forest/non-forest composites
4. Evaluate accuracy against benchmark datasets

### Individual Pipeline Steps

Run specific pipeline steps independently based on your needs:

#### Training & Prediction Only
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

#### Composites Only
```bash
# Generate annual composites from existing monthly predictions
poetry run python run_train_predict_pipeline.py \
  --step composites \
  --year 2022 \
  --project_id 7 \
  --run_id "test_ndvi_2025_07_12" \
  --db-host "remote"
```

#### CFW Dataset Processing Only
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

#### Benchmarks Only
```bash
# Run evaluation against all benchmark datasets
poetry run python run_train_predict_pipeline.py \
  --step benchmarks \
  --year 2022 \
  --project_id 7 \
  --run_id "test_ndvi_2025_07_12" \
  --db-host "remote"
```

### Single Month Training with Features

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

### Hyperparameter Tuning

The ML pipeline includes a comprehensive hyperparameter tuning framework to optimize XGBoost model parameters for your specific datasets and use cases.

#### Quick Start
```bash
# Fast tuning (10 trials, ~20 minutes)
poetry run python run_train_predict_pipeline.py \
  --step tuning \
  --year 2022 \
  --project_id 7 \
  --run_id "tune_fast_2025_07_13" \
  --db-host "remote" \
  --tune-preset fast

# Balanced tuning (25 trials, ~1 hour)
poetry run python run_train_predict_pipeline.py \
  --step tuning \
  --year 2022 \
  --project_id 7 \
  --run_id "tune_balanced_2025_07_13" \
  --db-host "remote" \
  --tune-preset balanced \
  --features ndvi

# Thorough tuning (50 trials, ~3 hours)
poetry run python run_train_predict_pipeline.py \
  --step tuning \
  --year 2022 \
  --project_id 7 \
  --run_id "tune_thorough_2025_07_13" \
  --db-host "remote" \
  --tune-preset thorough \
  --features ndvi ndwi
```

#### Tuning Presets

| Preset | Trials | Duration | Use Case |
|--------|--------|----------|----------|
| `fast` | 10 | ~20 min | Quick optimization, testing |
| `balanced` | 25 | ~1 hour | Standard optimization |
| `thorough` | 50 | ~3 hours | Comprehensive search |
| `regularization_focus` | 20 | ~45 min | Addressing overfitting |
| `depth_learning_focus` | 20 | ~45 min | Addressing underfitting |

#### Tuning Options

- **`--tune-preset`**: Choose from predefined configurations
- **`--tune-trials`**: Override the number of trials (e.g., `--tune-trials 15`)
- **`--tune-month`**: Specify month for tuning data (defaults to month 1)
- **`--tune-random-state`**: Set random seed for reproducibility

#### Parameters Optimized

The tuning framework automatically optimizes these XGBoost parameters:
- **`n_estimators`**: Number of boosting rounds (100-1000)
- **`max_depth`**: Tree depth (3-10)
- **`learning_rate`**: Step size (0.01-0.3)
- **`subsample`**: Fraction of samples per tree (0.6-1.0)
- **`colsample_bytree`**: Fraction of features per tree (0.6-1.0)
- **`reg_alpha`**: L1 regularization (0.01-10.0)
- **`reg_lambda`**: L2 regularization (0.1-10.0)
- **`min_child_weight`**: Minimum weight in leaf (1-10)

#### Outputs

The tuning process generates comprehensive results:

```
runs/{run_id}/
├── hyperparameter_tuning/
│   ├── experiment_001.json         # Individual experiment results
│   ├── tuning_report.html          # Comprehensive analysis report
│   ├── parameter_importance.png    # Which parameters matter most
│   ├── performance_distribution.png # Results visualization
│   └── best_model_recommendation.json
├── model_diagnostics/
│   ├── tune_001/                   # Full diagnostics per experiment
│   │   ├── feature_importance.png  # With meaningful band names
│   │   ├── learning_curves.png     # Training/validation curves
│   │   ├── confusion_matrix.png    # Performance visualization
│   │   └── ...
└── best_hyperparameters.json       # Easy-to-use best parameters
```

#### Using Tuning Results

After tuning completes, you'll get:
1. **Best parameters printed to console** for immediate use
2. **HTML report** with parameter importance analysis
3. **JSON file** with best parameters for programmatic use
4. **Full diagnostics** for each experiment including meaningful feature names

Example best parameters output:
```json
{
  "n_estimators": 342,
  "max_depth": 7,
  "learning_rate": 0.087,
  "subsample": 0.89,
  "colsample_bytree": 0.82,
  "reg_alpha": 1.23,
  "reg_lambda": 2.45
}
```

#### Integration with Training

Use the best parameters in subsequent training runs by modifying your training scripts or manually applying the recommended parameters.

### Pipeline Step Dependencies

- **training**: Requires `--start_month` and `--end_month` parameters; optional `--features` for spectral indices
- **tuning**: Requires `--year` and `--project_id`; optional `--tune-month` (defaults to month 1)
- **composites**: Requires existing monthly predictions from training step
- **cfw-processing**: Requires existing composites from composites step
- **benchmarks**: Can run independently with any existing STAC collections
- **all**: Runs all steps in sequence (training → composites → cfw-processing → benchmarks)

### Feature Engineering Options

#### Individual Features
| Feature | Description | Use Case | Added Features |
|---------|-------------|----------|----------------|
| `ndvi` | Normalized Difference Vegetation Index | Enhanced vegetation detection | +1 |
| `ndwi` | Normalized Difference Water Index | Basic water body detection | +1 |
| `evi` | Enhanced Vegetation Index | Dense vegetation, atmospheric correction | +1 |
| `savi` | Soil-Adjusted Vegetation Index | Sparse vegetation, soil backgrounds | +1 |
| `brightness` | Brightness and texture analysis | Surface type discrimination | +3 |
| `water_detection` | Advanced water detection suite | Comprehensive water body mapping | +3 |
| `shadow` | Shadow detection indices | Improved classification accuracy | +2 |

#### Example Feature Combinations
| Option | Description | Total Features | Use Case |
|--------|-------------|----------------|----------|
| No `--features` | Base bands only | 4 | Baseline performance |
| `--features ndvi` | Basic vegetation enhancement | 5 | Forest monitoring |
| `--features ndvi evi savi` | Comprehensive vegetation analysis | 7 | Advanced forest classification |
| `--features ndvi water_detection` | Forest and water mapping | 8 | Multi-land cover classification |
| `--features evi shadow` | Forest, urban, shadow detection | 9 | Complex landscape analysis |
| `--features ndvi evi water_detection` | Maximum discrimination | 11 | Comprehensive land use mapping |

### Available Forest Cover Datasets

The pipeline includes several reference forest cover datasets for comparison, all organized under a unified dataset structure:

#### External Reference Datasets
- **`datasets-hansen-tree-cover-2022`** - Hansen Global Forest Change (University of Maryland)
- **`datasets-mapbiomas-2022`** - MapBiomas Ecuador (local ecosystem mapping)
- **`datasets-esa-landcover-2020`** - ESA WorldCover (European Space Agency)
- **`datasets-jrc-forestcover-2020`** - JRC Global Forest Cover (European Commission)
- **`datasets-palsar-2020`** - ALOS PALSAR Forest/Non-Forest Map (JAXA)
- **`datasets-wri-treecover-2020`** - WRI Tropical Tree Cover (World Resources Institute)

#### ChocoForestWatch Datasets
- **`datasets-cfw-{run_id}-{year}`** - ChocoForestWatch model predictions (automatically created for each pipeline run)
- Examples: 
  - `datasets-cfw-test_ndvi_2025_07_12-2022` (NDVI-enhanced model)
  - `datasets-cfw-test_base_2025_07_12-2022` (base bands only)
  - `datasets-cfw-test_multi_features_2025_07_12-2022` (NDVI + NDWI)

### Training Data Preparation

Before running the pipeline, establish training data:

1. **Create Project**: Use the web interface to create a new project
2. **Draw Training Polygons**: Use the training module to digitize forest/non-forest areas
3. **Stratified Sampling**: The system uses stratified random sampling across Planet quads
4. **Target**: Aim for ~50 features per class per month for optimal model performance

### Pipeline Outputs

The ML pipeline generates several types of outputs organized in the `runs/` directory:

```
runs/
└── {run_id}/
    ├── {year}_{month}/           # Monthly results
    │   ├── saved_models/         # Trained Random Forest models (.pkl files)
    │   ├── data_cache/          # Cached training data
    │   └── prediction_cogs/     # Monthly prediction rasters (COGs)
    ├── composites/              # Annual composites
    │   └── {quad}_forest_cover.tif
    ├── benchmark_results/       # Accuracy metrics
    │   ├── benchmarks-hansen-tree-cover-2022.csv
    │   ├── benchmarks-mapbiomas-2022.csv
    │   └── ...
    └── feature_ids_testing/     # Held-out validation data
        ├── test_features_2022-01.csv
        └── ...
```

**Key Output Files:**
- **Models**: Monthly XGBoost models saved as pickle files with embedded feature engineering pipelines
- **Predictions**: Cloud Optimized GeoTIFFs uploaded to DigitalOcean Spaces
- **Composites**: Annual forest/non-forest maps merged from monthly predictions
- **Benchmarks**: CSV files with accuracy metrics (accuracy, F1, precision, recall)
- **STAC Collections**: Metadata entries for integration with TiTiler tile server
- **Feature Metadata**: Model files include feature engineering configuration for consistent prediction

**Feature Engineering Benefits:**
- **Consistent Features**: Training and prediction use identical feature engineering pipelines
- **Model Portability**: Feature engineering is saved with models for reproducible predictions
- **Performance Gains**: NDVI and NDWI can improve forest/non-forest classification accuracy
- **Cache Separation**: Models with different features use separate cache files to prevent conflicts

### Process Forest Cover Rasters

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

Available datasets: `hansen-tree-cover-2022`, `mapbiomas-2022`, `esa-landcover-2020`, `jrc-forestcover-2020`, `palsar-2020`, `wri-treecover-2020`

**Note**: ChocoForestWatch datasets (`cfw-{run_id}`) are processed dynamically via the main pipeline and are no longer hardcoded in the configuration.

## Western Ecuador Statistics Caching

The application includes an optimized caching system for western Ecuador summary statistics across different forest cover datasets. **As of 2025, all datasets are pre-processed and clipped to western Ecuador**, enabling much faster calculation through simplified pixel counting without geometric boundary clipping.

### Key Features

- **Simplified Calculation**: Uses direct pixel counting (1=forest, 0=non-forest, 255=missing) instead of complex geometric operations
- **Auto-Loading**: Frontend automatically displays cached regional statistics when users visit the homepage
- **Instant Access**: Pre-cached statistics load immediately without waiting for calculations
- **Memory Efficient**: Avoids memory issues with large datasets that occurred in the previous boundary-based approach

### Pre-calculation Scripts

To ensure instant loading, pre-calculate statistics for all datasets:

#### Using Django Management Command (Recommended)

```bash
# Pre-calculate all statistics using optimized simplified mode
docker compose exec backend python manage.py precalculate_western_ecuador_stats --db-host local

# Force recalculation even if cached
docker compose exec backend python manage.py precalculate_western_ecuador_stats --force --db-host local

# Calculate for specific collection only
docker compose exec backend python manage.py precalculate_western_ecuador_stats --collection datasets-hansen-tree-cover-2022 --db-host local

# Clear all cached stats before calculating
docker compose exec backend python manage.py precalculate_western_ecuador_stats --clear --db-host local

# Test with first collection only (recommended for troubleshooting)
docker compose exec backend python manage.py precalculate_western_ecuador_stats --test-first --db-host local

# Combine options for fresh calculation
docker compose exec backend python manage.py precalculate_western_ecuador_stats --clear --force --db-host local
```

#### Using Standalone Script

```bash
# Pre-calculate all statistics (from project root)
python scripts/precalculate_stats.py

# Force recalculation even if cached
python scripts/precalculate_stats.py --force

# Calculate for specific collection only
python scripts/precalculate_stats.py --collection datasets-hansen-tree-cover-2022

# Show help
python scripts/precalculate_stats.py --help
```

### Performance Improvements

The new simplified calculation method provides:

- **Much faster execution** - typically 10-50x faster than boundary-based clipping
- **Reduced memory usage** - no need to load large boundary geometries or perform spatial operations
- **Higher reliability** - eliminates projection and geometric processing errors
- **Easier maintenance** - simpler, more straightforward codebase

### Available Forest Cover Collections

The available datasets are now managed dynamically through the database system. Current collections include:

- `datasets-hansen-tree-cover-2022` - Hansen Global Forest Change
- `datasets-mapbiomas-2022` - MapBiomas Ecuador  
- `datasets-esa-landcover-2020` - ESA WorldCover
- `datasets-jrc-forestcover-2020` - JRC Forest Cover
- `datasets-palsar-2020` - ALOS PALSAR Forest Map
- `datasets-wri-treecover-2020` - WRI Tropical Tree Cover
- `datasets-cfw-{run_id}-{year}` - ChocoForestWatch datasets (e.g., `datasets-cfw-test_ndvi_2025_07_12-2022` for NDVI-enhanced models)

For the complete list of available datasets, use the Django admin interface at `/admin/core/dataset/` or query the API at `/api/datasets/`.

### Caching Details

- **Storage**: File-based cache in `backend/djangocfw/cache/`
- **Persistence**: Statistics survive server restarts  
- **Timeout**: Never expires (cached indefinitely)
- **Automatic Loading**: Frontend automatically displays cached regional stats when datasets are selected
- **Fallback**: If cache is empty, statistics are calculated on-demand and then cached

### Troubleshooting

If the pre-calculation seems to hang or fail:

1. **Test with one collection first**:
   ```bash
   docker compose exec backend python manage.py precalculate_western_ecuador_stats --test-first --db-host local
   ```

2. **Monitor detailed logs** while running:
   ```bash
   docker compose logs -f backend
   ```

3. **Verify environment variables**:
   - `TITILER_URL` should be set (usually `http://tiler-uvicorn:8083`)

4. **Common issues**:
   - TiTiler service not running
   - Network timeouts (though calculations are now much faster)
   - Invalid collection IDs in STAC database
   - Collection statistics endpoint not available (falls back to default values)

5. **Performance expectations**:
   - Simplified mode: typically 10-30 seconds per collection
   - Standard mode (fallback): 1-2 minutes per collection
   - Much faster than previous boundary-based approach

### Environment Requirements

Ensure these environment variables are set:

- `TITILER_URL` - URL of the TiTiler service (e.g., `http://tiler-uvicorn:8083`)

Note: `BOUNDARY_GEOJSON_PATH` is no longer required for the simplified calculation mode since all datasets are pre-processed.

### Recommended Workflow

1. After deployment or major updates, run the pre-calculation script to warm the cache
2. Users will then see instant western Ecuador statistics when they select different forest cover datasets
3. Users can still draw custom areas to override the default regional statistics
   
## Analytics Dashboard

The application includes integrated web analytics powered by Umami, providing insights into user behavior and site performance.

### Accessing Analytics

**Production Environment:**
- **URL:** https://analytics.chocoforestwatch.fcat-ecuador.org
- **Setup:** Self-hosted Umami instance running on subdomain
- **Authentication:** Secure login required (contact admin for access)

### Implementation Details

The analytics system is deployed using:
- **Umami:** Privacy-focused, open-source web analytics
- **Database:** Dedicated PostgreSQL instance for analytics data
- **Infrastructure:** Docker container with SSL certificate via Let's Encrypt
- **Network:** Nginx reverse proxy on dedicated subdomain

### Features

- Real-time visitor tracking
- Page view analytics
- Referrer statistics
- Geographic visitor distribution
- Privacy-compliant (no cookies, GDPR friendly)
- Custom event tracking capabilities

For detailed setup instructions, see the [Umami Analytics Setup Guide](docs/setup/umami-analytics.md).

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Setup Guides](docs/setup/)** - Installation and configuration instructions
  - [Umami Analytics Setup](docs/setup/umami-analytics.md) - Complete analytics integration guide
- **[Architecture Documentation](docs/architecture/)** - Technical design and system overview
- **[Development Workflows](docs/workflows/)** - Testing, CI/CD, and troubleshooting
- **[User Guides](docs/user-guides/)** - End-user documentation

See the [Documentation Index](docs/README.md) for a complete overview.

## Contributing

1. Follow the development workflow outlined above
2. Ensure all tests pass before submitting PRs
3. Follow the existing code style and conventions
4. Update documentation as needed
5. Create issues for any bugs or feature requests

## License

....

## Support

....