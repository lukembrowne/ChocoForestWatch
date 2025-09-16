# Changelog

All notable changes to ChocoForestWatch will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2025-09-10
 - Fixed bug with GFW deforestation alert clicking behavior
 - Improve documentation and add MIT license
 - Better UI for adding Planet imagery in sidepanel
 - Added 2023 + 2024 Planet imagery to imagery viewer
 - Added ability to download imagery
 - Added enhanced analytics

## [0.1.1] - 2025-07-14

### Added
- Advanced feature engineering system with NDVI and NDWI spectral indices support
- Step-based pipeline execution for modular workflow control (training, composites, cfw-processing, benchmarks)
- Boundary clipping support for ChocoForestWatch datasets in ML pipeline
- Hyperparameter tuning framework with comprehensive optimization presets
- Dataset service for managing external forest cover datasets
- Dynamic dataset configuration with JSON-based management
- Hyperparameter tuning for xgboost model

### Changed
- Expanded training polygon set to across western Ecuador
- Improved composite generation to use local files when available

### Fixed
- Resolved projection handling issues in spatial operations with automatic CRS detection and reprojection


## [0.1.0] - 2025-06-01

### Added
- Version tracking system for datasets and models
- Changelog maintenance for better release management
- Multi-year GFW Integrated Deforestation Alerts with raster-based click-to-query functionality
- Enhanced prediction pipeline with standalone processing and database integration
- Umami analytics integration with Docker setup and dashboard access
- CompositeGenerator support for local composite file merging and conditional S3 uploads
- Responsive MapLegend component improvements for smaller screens
- Integrated AnalysisPanel in SidebarPanel with enhanced search functionality
- Spatial filtering improvements in ML pipeline extractor

### Changed
- Updated Docker and deployment configurations for enhanced analytics integration
- Refactored dataset selection components and removed BenchmarkSelector
- Improved Umami analytics configuration to use environment variables

### Fixed
- Resolved test failures in ML pipeline integration tests
- Fixed responsive layout issues in MapLegend component

### Security
- Restricted access to analytics dashboard with proper authentication

## Release Notes

This project follows semantic versioning:
- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality in a backward compatible manner  
- **PATCH** version for backward compatible bug fixes

### Dataset Versioning
Each annual forest cover dataset is versioned using the format `YYYY.MM.patch` where:
- `YYYY` represents the target year for predictions
- `MM` represents the model version for that year
- `patch` represents minor updates or corrections

Dataset versions are tracked in STAC collections and displayed in the frontend interface for reproducibility and reference.