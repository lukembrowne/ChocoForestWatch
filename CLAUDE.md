# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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