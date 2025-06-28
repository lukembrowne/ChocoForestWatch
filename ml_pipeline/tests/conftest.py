"""
Shared pytest fixtures for ml_pipeline tests.

This file contains pytest fixtures - these are reusable test data and setup functions
that can be shared across multiple test files. Think of fixtures as "test ingredients"
that you can inject into your tests to provide consistent, reliable test data.
"""
import pytest
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from unittest.mock import Mock, MagicMock
from shapely.geometry import Polygon
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
import tempfile
import json


@pytest.fixture
def sample_project_id():
    """Sample project ID for testing."""
    return 123


@pytest.fixture 
def sample_year():
    """Sample year for testing."""
    return "2022"


@pytest.fixture
def sample_collection():
    """Sample STAC collection name."""
    return "test-collection"


@pytest.fixture
def sample_base_url():
    """Sample TiTiler base URL."""
    return "http://localhost:8083"


@pytest.fixture
def sample_run_id():
    """Sample run ID."""
    return "test_run_2024_01_01"


@pytest.fixture
def mock_engine():
    """Mock SQLAlchemy engine."""
    return Mock(spec=Engine)


@pytest.fixture
def sample_polygon():
    """Create a sample polygon for testing."""
    return Polygon([
        (-80.0, -1.0),
        (-79.9, -1.0), 
        (-79.9, -0.9),
        (-80.0, -0.9),
        (-80.0, -1.0)
    ])


@pytest.fixture
def sample_training_polygons():
    """Create sample training polygons GeoDataFrame."""
    polygons = [
        Polygon([(-80.0, -1.0), (-79.9, -1.0), (-79.9, -0.9), (-80.0, -0.9), (-80.0, -1.0)]),
        Polygon([(-79.8, -1.0), (-79.7, -1.0), (-79.7, -0.9), (-79.8, -0.9), (-79.8, -1.0)]),
        Polygon([(-79.6, -1.0), (-79.5, -1.0), (-79.5, -0.9), (-79.6, -0.9), (-79.6, -1.0)])
    ]
    
    gdf = gpd.GeoDataFrame({
        'id': ['1', '2', '3'],
        'classLabel': ['Forest', 'Non-Forest', 'Forest'],
        'geometry': polygons
    })
    return gdf


@pytest.fixture
def sample_pixel_data():
    """Create sample pixel data for testing."""
    # Simulate raster pixels: 1=Forest, 0=Non-Forest, 255=Missing
    return np.array([
        [1, 1, 0, 0],
        [1, 0, 0, 255],
        [0, 0, 1, 1],
        [255, 1, 1, 0]
    ], dtype=np.uint8)


@pytest.fixture
def mock_titiler_extractor():
    """Mock TitilerExtractor for testing."""
    mock = Mock()
    mock.get_all_cog_urls.return_value = ["http://example.com/cog1.tif", "http://example.com/cog2.tif"]
    return mock


@pytest.fixture
def sample_held_out_features():
    """Sample held-out feature IDs."""
    return pd.DataFrame({
        'feature_id': ['1', '3']  # Only include features 1 and 3 for testing
    })


@pytest.fixture
def temp_test_features_dir(sample_held_out_features):
    """Create temporary directory with test feature CSV files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create CSV for each month
        for month in range(1, 13):
            month_str = f"2022-{month:02d}"
            csv_path = temp_path / f"test_features_{month_str}.csv"
            sample_held_out_features.to_csv(csv_path, index=False)
        
        yield temp_path


@pytest.fixture
def benchmark_tester_params(sample_base_url, sample_collection, sample_year, sample_project_id):
    """Standard parameters for BenchmarkTester initialization."""
    return {
        'base_url': sample_base_url,
        'collection': sample_collection, 
        'year': sample_year,
        'project_id': sample_project_id,
        'band_indexes': [1],
        'verbose': False
    }


# =====================================
# Predictor Test Fixtures
# =====================================

class MockModel:
    """Mock ML model that can be pickled for testing."""
    def __init__(self):
        self.consecutive_to_global = {0: 0, 1: 1}  # Map consecutive to global class labels
        self.predict_calls = []  # Track predict calls for testing
    
    def predict(self, X):
        # Track calls for testing
        self.predict_calls.append(len(X))
        # Simple mock prediction: alternate between 0 and 1 based on input length
        return np.array([i % 2 for i in range(len(X))])


@pytest.fixture
def mock_trained_model():
    """Mock trained machine learning model that can be pickled."""
    return MockModel()


@pytest.fixture
def sample_model_bundle(mock_trained_model):
    """Sample model bundle that would be saved as pickle file."""
    return {
        'model': mock_trained_model,
        'meta': {
            'feature_names': ['red', 'green', 'blue', 'nir'],
            'class_names': ['Non-Forest', 'Forest'],
            'training_date': '2022-01-01',
            'model_type': 'RandomForestClassifier'
        }
    }


@pytest.fixture
def temp_model_file(sample_model_bundle):
    """Create temporary model pickle file for testing."""
    import pickle
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pkl', delete=False) as f:
        pickle.dump(sample_model_bundle, f)
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def predictor_config():
    """Sample PredictorConfig for testing."""
    from ml_pipeline.predictor import PredictorConfig
    return PredictorConfig(
        blocksize=512,
        compress="lzw",
        dtype="uint8", 
        nodata=255,
        predictor=2
    )


@pytest.fixture
def mock_extractor_for_predictor():
    """Mock extractor for Predictor testing."""
    mock = Mock()
    mock.get_cog_urls.return_value = [
        "http://example.com/tile1.tif",
        "http://example.com/tile2.tif"
    ]
    mock.get_all_cog_urls.return_value = [
        "http://example.com/tile1.tif", 
        "http://example.com/tile2.tif",
        "http://example.com/tile3.tif"
    ]
    return mock


@pytest.fixture
def sample_aoi_geojson():
    """Sample Area of Interest GeoJSON for testing."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [-80.0, -1.0],
            [-79.0, -1.0], 
            [-79.0, 0.0],
            [-80.0, 0.0],
            [-80.0, -1.0]
        ]]
    }


@pytest.fixture
def mock_rasterio_dataset():
    """Mock rasterio dataset for testing."""
    mock_ds = Mock()
    mock_ds.profile = {
        'driver': 'GTiff',
        'dtype': 'uint16',
        'nodata': 0,
        'width': 100,
        'height': 100,
        'count': 4,
        'crs': 'EPSG:3857'
    }
    mock_ds.nodata = 0
    mock_ds.block_windows.return_value = [
        ((0, 0), Mock(col_off=0, row_off=0, width=50, height=50)),
        ((0, 1), Mock(col_off=50, row_off=0, width=50, height=50))
    ]
    # Mock 4-band raster data (RGBN)
    mock_ds.read.return_value = np.random.randint(0, 1000, (4, 50, 50), dtype=np.uint16)
    return mock_ds


@pytest.fixture
def temp_prediction_dir():
    """Create temporary directory for prediction outputs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def predictor_init_params(temp_model_file, mock_extractor_for_predictor, predictor_config):
    """Standard parameters for ModelPredictor initialization."""
    return {
        'model_path': temp_model_file,
        'extractor': mock_extractor_for_predictor,
        'upload_to_s3': False,
        's3_path': 'test/predictions',
        'cfg': predictor_config
    }


@pytest.fixture
def mock_gdal():
    """Mock GDAL operations for sieve filter testing."""
    mock_gdal = Mock()
    mock_dataset = Mock()
    mock_band = Mock()
    
    # Mock the gdalconst module
    mock_gdalconst = Mock()
    mock_gdalconst.GA_Update = 1
    mock_gdal.gdalconst = mock_gdalconst
    
    mock_gdal.Open.return_value = mock_dataset
    mock_gdal.UseExceptions = Mock()
    mock_gdal.SieveFilter = Mock()
    mock_dataset.GetRasterBand.return_value = mock_band
    mock_band.GetNoDataValue.return_value = 255
    mock_band.SetNoDataValue = Mock()
    mock_band.FlushCache = Mock()
    
    return mock_gdal


@pytest.fixture
def sample_cog_metadata():
    """Sample COG metadata for testing."""
    return {
        'url': 'http://example.com/sample.tif',
        'tile_id': 'sample',
        'bounds': [-80.0, -1.0, -79.0, 0.0],
        'epsg': 3857
    }