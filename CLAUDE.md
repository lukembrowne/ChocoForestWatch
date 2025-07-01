# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Standard Workflow 
1. First think through the problem, read the codebase for relevant files, and write a plan to projectplan.md 
2. The plan should have a list of todo items that you can check off as you complete them 
3. Before you begin working, check in with me and I will verify the plan 
4. Then, begin working on the todo items, marking them as complete as you go 
5. Please every step of the way just give me a high level explanation of what changes you made 
6. Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity 
7. Finally, add a review section to the projectplan.md file with a summary of the changes you made and any other relevant information

## Development Commands

### Docker Development
```bash
docker compose up --build  # Start all services for development
docker compose -f docker-compose.prod.yml up --build  # Production build
```

**IMPORTANT**: This application is developed and deployed entirely within Docker containers. All development, testing, and debugging must be done through the containerized environment using `docker compose`.

### Working with Services
- **Frontend development**: Use `docker compose exec frontend [command]` instead of running commands directly
- **Backend operations**: Use `docker compose exec backend [command]` for Django management
- **Database access**: Use `docker compose exec db psql [options]` for database operations
- **ML Pipeline**: Use `docker compose exec backend python manage.py shell` or access notebooks through mounted volumes

### Testing New Features
When testing new features or changes:
1. Use `docker compose up --build` to rebuild and start services
2. Access services through their exposed ports (typically localhost:9000 for frontend)
3. Execute commands within containers, not on the host system
4. Example: Instead of `npm run dev`, the frontend service runs Quasar dev server automatically within the container

### Common Docker Commands
```bash
docker compose exec frontend sh          # Access frontend container shell
docker compose exec backend python manage.py migrate    # Run Django migrations
docker compose logs frontend            # View frontend service logs
docker compose restart frontend         # Restart specific service

# Pre-calculate western Ecuador statistics for all datasets
docker compose exec backend python manage.py precalculate_western_ecuador_stats

# Force recalculation of cached statistics
docker compose exec backend python manage.py precalculate_western_ecuador_stats --force
```

## Development Memories
- No need to test functionality using `docker compose up --build` because it uses too many tokens with the logging
- NEVER add "Generated with Claude Code" or "Co-Authored-By: Claude" attribution in commit messages or PR descriptions

## Versioning and Changelog Guidelines

### Application Versioning
- **Semantic Versioning**: Use MAJOR.MINOR.PATCH format (e.g., 0.1.0)
- **Version Synchronization**: All components (frontend, backend, ML pipeline) maintain the same version
- **Version Files**: 
  - Frontend: `package.json`
  - Backend: `djangocfw/version.py`
  - ML Pipeline: `pyproject.toml`

### Dataset Versioning
- **Format**: YYYY.MM.patch (e.g., 2024.01.0)
  - `YYYY`: Target year for predictions
  - `MM`: Model version for that year  
  - `patch`: Minor updates or corrections
- **Tracking**: Version information stored in STAC collections, COG metadata, and Django models
- **Display**: Version numbers shown in frontend dataset selectors and layer information

### Changelog Maintenance
- **Format**: Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) standard
- **Location**: `/CHANGELOG.md` in project root
- **Sections**: Added, Changed, Fixed, Deprecated, Removed, Security
- **Updates**: Add entries for major changes as they are implemented
- **Release Process**: Update changelog before creating releases

### Version Tracking Implementation
- **STAC Collections**: Include `version`, `created_at`, and `processing:software` metadata
- **COG Files**: Add version information to GeoTIFF tags (`TIFFTAG_SOFTWARE`, `TIFFTAG_DATETIME`)
- **Database Models**: TrainedModel and Prediction models include version tracking fields
- **Frontend Display**: Version information shown in dataset selectors and about modal
- **API Endpoint**: `/api/version/` provides application version information
- **Spatial Operations**: All spatial operations must handle mixed coordinate reference systems (CRS) automatically. The pipeline should detect raster and boundary CRS, reproject geometries as needed, and provide clear logging for debugging projection issues. Never assume consistent projections across datasets.
- Always use this approach to internal documentation moving forward: carefully document code, provide clear guidance, and maintain a comprehensive yet concise documentation strategy
- **Frontend Plugins/Packages**: When adding new plugins or packages to the frontend:
  1. Use `docker compose exec frontend npm install [package-name]` to install within the container
  2. Verify the package is added to `frontend/package.json`
  3. Rebuild the frontend container with `docker compose up --build frontend`
  4. If the package requires global configuration (e.g., Vue plugin), update `frontend/src/boot/` with appropriate initialization
  5. Always test the package integration thoroughly within the Docker environment
  6. For Quasar-specific plugins, use `quasar ext add [plugin-name]` when applicable
  7. Ensure all new packages are compatible with the current Vue 3 and Quasar setup

## Architecture Overview

### Multi-Service Application
- **Frontend**: Quasar (Vue.js) SPA with mapping interface using OpenLayers
- **Backend**: Django REST API with PostGIS for geospatial data
- **Database**: PostgreSQL with PostGIS and PGSTAC extensions
- **ML Pipeline**: Separate Poetry-managed Python package for model training/prediction
- **TiTiler**: STAC-based dynamic tile server for satellite imagery

### Data Flow Architecture
1. **Training Data Creation**: Users draw polygons in the frontend interface
2. **Model Training**: ML pipeline extracts features from NICFI imagery and trains monthly models
3. **Prediction Generation**: Models generate forest/deforestation predictions as COGs
4. **STAC Integration**: Predictions stored in PGSTAC for efficient tile serving
5. **Visualization**: TiTiler serves dynamic tiles to frontend mapping interface

### Key Integrations
- **PGSTAC**: Manages spatiotemporal asset catalogs for satellite imagery
- **DigitalOcean Spaces**: S3-compatible storage for imagery and predictions
- **NICFI**: Monthly satellite imagery from Norway's forest initiative

## Project Structure

### Core Components
- `frontend/src/stores/`: Pinia stores (mapStore.js, projectStore.js)
- `frontend/src/components/`: Vue components organized by feature
- `backend/djangocfw/core/`: Django models, views, serializers
- `ml_pipeline/src/ml_pipeline/`: Core ML pipeline modules
- `ml_pipeline/notebooks/`: Jupyter notebooks for ML workflows

### Data Management
- Training polygons stored in Django models with PostGIS geometry
- NICFI imagery managed through STAC collections
- Predictions output as Cloud Optimized GeoTIFFs (COGs)
- Benchmark datasets for model evaluation

### Development Workflow
- Main development branch: `dev`
- Production branch: `main`
- Feature branches: `issue-123/feature-description`
- Deployment triggered on push to `main`

## Key ML Pipeline Workflows

### Training Process
1. Create project and draw training polygons using web interface
2. Use stratified random sampling across Planet quads (~50 features per class per month)
3. Run `run_train_predict_pipeline.py` to train separate models for each month
4. Models saved as pickle files, predictions uploaded as COGs to cloud storage

### Benchmark Testing
- Compare model predictions against established forest cover datasets
- Run `test_benchmarks*.py` to evaluate accuracy metrics
- Results stored in benchmark_results/ directories

### Composite Generation
- Create annual forest/non-forest composites from monthly predictions
- Use `create_composite*.py` scripts for temporal aggregation

## Environment Configuration

### Required Environment Variables
- Database: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- Storage: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (DigitalOcean Spaces)
- Frontend: `VITE_API_URL`, `VITE_SENTRY_DSN`

### Docker Services
- `db`: PGSTAC-enabled PostgreSQL database
- `backend`: Django API server
- `frontend`: Quasar development server
- `tiler`: TiTiler STAC tile server
- `nginx`: Reverse proxy for production

## Technology Stack Details

### Frontend Technologies
- Quasar Framework (Vue 3 based)
- OpenLayers for interactive mapping
- Pinia for state management
- Chart.js for data visualization
- Vue I18n for internationalization (English/Spanish)

### Backend Technologies  
- Django REST Framework
- PostGIS for geospatial operations
- Celery for background tasks (configured but not actively used)
- STAC (SpatioTemporal Asset Catalog) standards

### ML Technologies
- scikit-learn for model training (Random Forest primary algorithm)
- XGBoost for additional model options
- Rasterio for geospatial raster processing
- GDAL for coordinate transformations and projections
- **Projection Handling**: All spatial operations automatically detect and handle different coordinate reference systems (CRS) through reprojection

## Internationalization Requirements

### Frontend Component Translation Policy
**CRITICAL**: ALL frontend components MUST be fully translated into both English and Spanish.

#### Requirements:
1. **Text Content**: All user-facing text must use i18n translation keys
2. **Translation Files**: Add translations to both `frontend/src/locales/en.json` and `frontend/src/locales/es.json`
3. **Component Setup**: Import and use `useI18n` in Vue components
4. **Implementation Pattern**:
   ```vue
   <script setup>
   import { useI18n } from 'vue-i18n'
   const { t } = useI18n()
   </script>
   
   <template>
     <div>{{ t('your.translation.key') }}</div>
   </template>
   ```

#### Translation Key Organization:
- Use nested keys for logical grouping (e.g., `sidebar.search.title`)
- Keep keys descriptive and hierarchical
- Maintain consistency across components

#### Testing:
- Verify translations work in both languages
- Test language switching functionality
- Ensure no hardcoded text remains

This ensures the platform is accessible to both English and Spanish-speaking users in the target region.