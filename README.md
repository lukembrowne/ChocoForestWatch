# Choco Forest Watch

**Forest monitoring for the Chocó forests of western Ecuador, a global biodiversity hotspot**

🌐 **[View Live Application →](https://chocoforestwatch.fcat-ecuador.org)**

## What is ChocoForestWatch?

ChocoForestWatch is an advanced forest monitoring system that monitors deforestation and forest cover changes across the Chocó bioregion of western Ecuador. Using high-resolution satellite imagery and machine learning, we provide researchers, conservationists, and policymakers with the tools needed to protect one of the world's most biodiverse and threatened regions.

## Key Features

🗺️ **Interactive Mapping Interface** - Explore forest cover changes with an intuitive web-based mapping platform

🛰️ **Satellite Image Analysis** - Monthly NICFI satellite imagery processed with advanced machine learning algorithms

🤖 **ML-Powered Detection** - XGBoost models trained on expert-annotated data to identify deforestation patterns


## Documentation

### Workflows
- **[Data Processing Workflow](docs/workflows/data-processing.md)** - Complete guide for processing NICFI satellite imagery and STAC integration
- **[ML Pipeline Workflow](docs/workflows/ml-pipeline.md)** - End-to-end machine learning pipeline including feature engineering and model training
- **[Versioning System](docs/workflows/versioning-system.md)** - Application and dataset versioning guidelines and implementation
- **[GFW Deforestation Alerts](docs/workflows/gfw-deforestation-alerts.md)** - Integration with Global Forest Watch deforestation monitoring
- **[Western Ecuador Stats Caching](docs/workflows/western-ecuador-stats-caching.md)** - Performance optimization for regional statistics

### Model Training & Algorithms
- **[Forest Flag Algorithms](docs/model-training/forest-flag-algorithms.md)** - Comprehensive comparison of temporal algorithms for forest classification
- **[Model Fitting Process](docs/model-training/model-fitting-process.md)** - Hyperparameter tuning, cross-validation, and model optimization techniques

### Setup & Configuration
- **[Analytics Setup](docs/setup/umami-analytics.md)** - Umami analytics integration for usage tracking

## Technology Stack

**Frontend**: Quasar (Vue.js) with OpenLayers mapping  
**Backend**: Django REST API with PostGIS for geospatial data  
**Database**: PostgreSQL with PostGIS and PGSTAC extensions  
**ML Pipeline**: Python with XGBoost   
**Docker-based development** and deployment workflow
**TiTiler** dynamic tile server for satellite imagery visualization 
**Data Storage**: STAC-compliant object storage for satellite imagery

## Contributing

We welcome contributions from researchers, developers, and conservationists! 

- **Report Issues**: Found a bug or have a feature request? [Open an issue](https://github.com/your-org/ChocoForestWatch/issues)
- **Documentation**: Help improve our guides and documentation

## License

This project is licensed under the MIT License. See `LICENSE` for details.
