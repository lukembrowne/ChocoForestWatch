"""
Unit tests for ModelPredictor and PredictorConfig classes.

These tests focus on testing individual methods in isolation using mocks
to replace external dependencies like file systems, rasterio, GDAL, and S3.
"""
import pytest
import numpy as np
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open

# Import the classes we're testing
from ml_pipeline.predictor import ModelPredictor, PredictorConfig


class TestPredictorConfig:
    """
    Test the PredictorConfig dataclass.
    
    Testing dataclasses is important to ensure default values are correct
    and that the configuration behaves as expected.
    """
    
    def test_default_config_values(self):
        """Test that PredictorConfig has correct default values."""
        config = PredictorConfig()
        
        assert config.blocksize == 1024
        assert config.compress == "lzw"
        assert config.dtype == "uint8"
        assert config.nodata == 255
        assert config.predictor == 2

    def test_custom_config_values(self):
        """Test that PredictorConfig accepts custom values."""
        config = PredictorConfig(
            blocksize=512,
            compress="jpeg",
            dtype="uint16",
            nodata=0,
            predictor=1
        )
        
        assert config.blocksize == 512
        assert config.compress == "jpeg"
        assert config.dtype == "uint16"
        assert config.nodata == 0
        assert config.predictor == 1

    def test_config_is_dataclass(self):
        """Test that PredictorConfig behaves like a dataclass."""
        config1 = PredictorConfig(blocksize=256)
        config2 = PredictorConfig(blocksize=256)
        config3 = PredictorConfig(blocksize=512)
        
        # Same values should be equal
        assert config1 == config2
        # Different values should not be equal
        assert config1 != config3


class TestModelPredictorInit:
    """
    Test ModelPredictor initialization.
    
    The __init__ method loads a model from pickle, so we need to mock
    the file system and pickle loading.
    """
    
    def test_init_with_valid_model_file(self, predictor_init_params):
        """Test that ModelPredictor initializes correctly with valid model file."""
        # Act: Create predictor
        predictor = ModelPredictor(**predictor_init_params)
        
        # Assert: Verify attributes are set correctly
        assert predictor.model_path == predictor_init_params['model_path']
        assert predictor.extractor == predictor_init_params['extractor']
        assert predictor.cfg == predictor_init_params['cfg']
        assert predictor.upload_to_s3 == False
        assert predictor.s3_path == 'test/predictions'
        assert predictor.model is not None
        assert predictor.meta is not None

    def test_init_converts_string_path_to_path_object(self, predictor_init_params):
        """Test that string model paths are converted to Path objects."""
        # Arrange: Convert Path to string
        params = predictor_init_params.copy()
        params['model_path'] = str(params['model_path'])
        
        # Act
        predictor = ModelPredictor(**params)
        
        # Assert: Should convert to Path object
        assert isinstance(predictor.model_path, Path)

    def test_init_with_s3_upload_enabled(self, predictor_init_params):
        """Test initialization with S3 upload enabled."""
        params = predictor_init_params.copy()
        params['upload_to_s3'] = True
        params['s3_path'] = 'production/predictions'
        
        predictor = ModelPredictor(**params)
        
        assert predictor.upload_to_s3 == True
        assert predictor.s3_path == 'production/predictions'

    def test_init_loads_model_bundle_correctly(self, predictor_init_params, sample_model_bundle):
        """Test that model bundle is loaded and unpacked correctly."""
        predictor = ModelPredictor(**predictor_init_params)
        
        # Should unpack the model and metadata
        assert type(predictor.model).__name__ == 'MockModel'
        assert predictor.meta == sample_model_bundle['meta']
        assert hasattr(predictor.model, 'predict')
        assert hasattr(predictor.model, 'consecutive_to_global')

    def test_init_with_missing_model_file(self, predictor_init_params):
        """Test that initialization fails gracefully with missing model file."""
        params = predictor_init_params.copy()
        params['model_path'] = Path('/nonexistent/model.pkl')
        
        with pytest.raises(FileNotFoundError):
            ModelPredictor(**params)

    def test_init_with_invalid_pickle_file(self, predictor_init_params):
        """Test that initialization fails gracefully with invalid pickle file."""
        # Create a temporary file with invalid pickle data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pkl', delete=False) as f:
            f.write("not a pickle file")
            invalid_path = Path(f.name)
        
        params = predictor_init_params.copy()
        params['model_path'] = invalid_path
        
        try:
            with pytest.raises(Exception):  # Could be various pickle-related exceptions
                ModelPredictor(**params)
        finally:
            invalid_path.unlink()  # Cleanup


class TestModelPredictorPredictCollection:
    """
    Test the predict_collection method.
    
    This method processes all COGs in a collection, with options for
    parallel processing and local/remote storage.
    """
    
    @pytest.fixture
    def mock_predictor(self, predictor_init_params):
        """Create a ModelPredictor with mocked dependencies for testing."""
        return ModelPredictor(**predictor_init_params)

    def test_predict_collection_with_save_local_true(self, mock_predictor, temp_prediction_dir):
        """Test predict_collection with local saving enabled."""
        with patch.object(mock_predictor, '_predict_single_cog') as mock_predict_single, \
             patch('ml_pipeline.predictor.Parallel') as mock_parallel:
            
            # Mock parallel processing to return list of paths
            mock_parallel.return_value.return_value = [
                temp_prediction_dir / "tile1.tiff",
                temp_prediction_dir / "tile2.tiff",
                temp_prediction_dir / "tile3.tiff"
            ]
            
            result = mock_predictor.predict_collection(
                basemap_date="2022-01",
                collection="test-collection",
                pred_dir=temp_prediction_dir,
                save_local=True
            )
            
            assert len(result) == 3
            # Directory should still exist
            assert temp_prediction_dir.exists()

    def test_predict_collection_with_save_local_false(self, mock_predictor, temp_prediction_dir):
        """Test predict_collection with local saving disabled."""
        with patch.object(mock_predictor, '_predict_single_cog') as mock_predict_single, \
             patch('ml_pipeline.predictor.Parallel') as mock_parallel, \
             patch('ml_pipeline.predictor.shutil.rmtree') as mock_rmtree:
            
            mock_parallel.return_value.return_value = [
                temp_prediction_dir / "tile1.tiff",
                temp_prediction_dir / "tile2.tiff"
            ]
            
            result = mock_predictor.predict_collection(
                basemap_date="2022-01",
                collection="test-collection", 
                pred_dir=temp_prediction_dir,
                save_local=False
            )
            
            assert len(result) == 2
            # Should clean up directory
            mock_rmtree.assert_called_once_with(temp_prediction_dir)

    def test_predict_collection_creates_prediction_directory(self, mock_predictor):
        """Test that predict_collection creates prediction directory if it doesn't exist."""
        nonexistent_dir = Path("/tmp/nonexistent_pred_dir")
        
        with patch.object(mock_predictor, '_predict_single_cog') as mock_predict_single, \
             patch('ml_pipeline.predictor.Parallel') as mock_parallel, \
             patch.object(Path, 'mkdir') as mock_mkdir:
            
            mock_parallel.return_value.return_value = []
            
            mock_predictor.predict_collection(
                basemap_date="2022-01",
                collection="test-collection",
                pred_dir=nonexistent_dir
            )
            
            # Should create directory with parents
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_predict_collection_converts_string_path(self, mock_predictor):
        """Test that predict_collection converts string paths to Path objects."""
        with patch.object(mock_predictor, '_predict_single_cog') as mock_predict_single, \
             patch('ml_pipeline.predictor.Parallel') as mock_parallel, \
             patch.object(Path, 'mkdir') as mock_mkdir:
            
            mock_parallel.return_value.return_value = []
            
            # Pass string path instead of Path object
            mock_predictor.predict_collection(
                basemap_date="2022-01",
                collection="test-collection",
                pred_dir="/tmp/string_path"
            )
            
            # Should still work (mkdir should be called on Path object)
            mock_mkdir.assert_called_once()


class TestModelPredictorPrivateMethods:
    """
    Test private methods of ModelPredictor.
    
    These methods handle the core prediction logic, file I/O, and GDAL operations.
    """
    
    @pytest.fixture
    def mock_predictor(self, predictor_init_params):
        """Create a ModelPredictor with mocked dependencies for testing."""
        return ModelPredictor(**predictor_init_params)

    def test_predict_single_cog_success(self, mock_predictor, temp_prediction_dir, mock_rasterio_dataset):
        """Test successful prediction of a single COG."""
        cog_url = "http://example.com/test.tif"
        basemap_date = "2022-01"
        
        with patch('ml_pipeline.predictor.rasterio.open') as mock_rasterio_open, \
             patch.object(mock_predictor, '_sieve_inplace') as mock_sieve, \
             patch.object(mock_predictor, '_upload_to_s3') as mock_upload:
            
            # Setup mocks
            mock_rasterio_open.return_value.__enter__.return_value = mock_rasterio_dataset
            mock_dst = Mock()
            mock_rasterio_open.return_value.__enter__.return_value = mock_dst
            mock_dst.write = Mock()
            
            # Mock the source dataset for reading
            mock_src = mock_rasterio_dataset
            mock_rasterio_open.side_effect = [
                Mock(__enter__=Mock(return_value=mock_src), __exit__=Mock()),
                Mock(__enter__=Mock(return_value=mock_dst), __exit__=Mock())
            ]
            
            result = mock_predictor._predict_single_cog(
                cog_url=cog_url,
                basemap_date=basemap_date,
                pred_dir=temp_prediction_dir,
                save_local=True
            )
            
            # Should return path to prediction file
            assert isinstance(result, Path)
            assert result.name.endswith('.tiff')
            # Should call sieve filter
            mock_sieve.assert_called_once()

    def test_predict_single_cog_with_error(self, mock_predictor, temp_prediction_dir):
        """Test _predict_single_cog handles errors gracefully."""
        cog_url = "http://example.com/broken.tif"
        
        with patch('ml_pipeline.predictor.rasterio.open') as mock_rasterio_open:
            # Make rasterio.open raise an exception
            mock_rasterio_open.side_effect = Exception("Failed to open raster")
            
            result = mock_predictor._predict_single_cog(
                cog_url=cog_url,
                basemap_date="2022-01",
                pred_dir=temp_prediction_dir
            )
            
            # Should return None on error
            assert result is None

    def test_predict_single_cog_save_local_false(self, mock_predictor, temp_prediction_dir, mock_rasterio_dataset):
        """Test _predict_single_cog with save_local=False."""
        with patch('ml_pipeline.predictor.rasterio.open') as mock_rasterio_open, \
             patch.object(mock_predictor, '_sieve_inplace') as mock_sieve, \
             patch.object(Path, 'unlink') as mock_unlink:
            
            # Setup mocks
            mock_src = mock_rasterio_dataset
            mock_dst = Mock()
            mock_rasterio_open.side_effect = [
                Mock(__enter__=Mock(return_value=mock_src), __exit__=Mock()),
                Mock(__enter__=Mock(return_value=mock_dst), __exit__=Mock())
            ]
            
            result = mock_predictor._predict_single_cog(
                cog_url="http://example.com/test.tif",
                basemap_date="2022-01",
                pred_dir=temp_prediction_dir,
                save_local=False
            )
            
            # Should delete local file and return None
            mock_unlink.assert_called_once()
            assert result is None

    def test_sieve_inplace_success(self, mock_predictor, temp_prediction_dir, mock_gdal):
        """Test _sieve_inplace method with successful GDAL operations."""
        test_file = temp_prediction_dir / "test.tiff"
        test_file.touch()  # Create empty file
        
        with patch('ml_pipeline.predictor.gdal', mock_gdal):
            mock_predictor._sieve_inplace(test_file, min_pixels=10)
            
            # Should call GDAL functions
            mock_gdal.UseExceptions.assert_called_once()
            mock_gdal.Open.assert_called_once_with(str(test_file), 1)
            mock_gdal.SieveFilter.assert_called_once()

    def test_sieve_inplace_with_gdal_error(self, mock_predictor, temp_prediction_dir):
        """Test _sieve_inplace handles GDAL errors gracefully."""
        test_file = temp_prediction_dir / "test.tiff"
        test_file.touch()
        
        with patch('ml_pipeline.predictor.gdal') as mock_gdal:
            # Make GDAL.Open return None (failure)
            mock_gdal.Open.return_value = None
            
            with pytest.raises(RuntimeError, match="GDAL failed to open"):
                mock_predictor._sieve_inplace(test_file, min_pixels=10)

    def test_upload_to_s3_when_enabled(self, mock_predictor, temp_prediction_dir):
        """Test _upload_to_s3 when S3 upload is enabled."""
        mock_predictor.upload_to_s3 = True
        test_file = temp_prediction_dir / "test.tiff"
        test_file.touch()
        
        with patch('ml_pipeline.predictor.upload_file') as mock_upload:
            mock_predictor._upload_to_s3(test_file, "2022-01")
            
            # Should call upload_file with correct parameters
            mock_upload.assert_called_once()
            call_args = mock_upload.call_args
            assert call_args[0][0] == test_file  # local_path
            assert "test/predictions/2022/01/test.tiff" in call_args[0][1]  # remote_key

    def test_upload_to_s3_when_disabled(self, mock_predictor, temp_prediction_dir):
        """Test _upload_to_s3 when S3 upload is disabled."""
        mock_predictor.upload_to_s3 = False
        test_file = temp_prediction_dir / "test.tiff"
        
        with patch('ml_pipeline.predictor.upload_file') as mock_upload:
            mock_predictor._upload_to_s3(test_file, "2022-01")
            
            # Should not call upload_file
            mock_upload.assert_not_called()

    def test_upload_to_s3_constructs_correct_path(self, mock_predictor, temp_prediction_dir):
        """Test that _upload_to_s3 constructs the correct S3 path."""
        mock_predictor.upload_to_s3 = True
        mock_predictor.s3_path = "predictions/v2"
        test_file = temp_prediction_dir / "tile_123.tiff"
        test_file.touch()
        
        with patch('ml_pipeline.predictor.upload_file') as mock_upload:
            mock_predictor._upload_to_s3(test_file, "2023-12")
            
            expected_remote_key = "predictions/v2/2023/12/tile_123.tiff"
            mock_upload.assert_called_once_with(test_file, expected_remote_key)


class TestModelPredictorEdgeCases:
    """
    Test edge cases and error conditions for ModelPredictor.
    """
    
    @pytest.fixture
    def mock_predictor(self, predictor_init_params):
        """Create a ModelPredictor with mocked dependencies for testing."""
        return ModelPredictor(**predictor_init_params)

    def test_model_prediction_with_all_nodata_pixels(self, mock_predictor, temp_prediction_dir):
        """Test prediction when all pixels are nodata."""
        with patch('ml_pipeline.predictor.rasterio.open') as mock_rasterio_open:
            # Mock dataset with all nodata values
            mock_src = Mock()
            mock_src.profile = {'count': 4, 'dtype': 'uint16', 'nodata': 0}
            mock_src.nodata = 0
            mock_src.block_windows.return_value = [((0, 0), Mock())]
            mock_src.read.return_value = np.zeros((4, 50, 50), dtype=np.uint16)  # All nodata
            
            mock_dst = Mock()
            mock_rasterio_open.side_effect = [
                Mock(__enter__=Mock(return_value=mock_src), __exit__=Mock()),
                Mock(__enter__=Mock(return_value=mock_dst), __exit__=Mock())
            ]
            
            with patch.object(mock_predictor, '_sieve_inplace'):
                result = mock_predictor._predict_single_cog(
                    cog_url="http://example.com/nodata.tif",
                    basemap_date="2022-01",
                    pred_dir=temp_prediction_dir
                )
            
            # Should still complete successfully
            assert isinstance(result, Path)

    def test_model_prediction_with_mixed_valid_nodata(self, mock_predictor, temp_prediction_dir):
        """Test prediction with mixed valid and nodata pixels."""
        with patch('ml_pipeline.predictor.rasterio.open') as mock_rasterio_open:
            # Mock dataset with mixed data
            mock_src = Mock()
            mock_src.profile = {'count': 4, 'dtype': 'uint16', 'nodata': 0}
            mock_src.nodata = 0
            mock_src.block_windows.return_value = [((0, 0), Mock())]
            
            # Create mixed data: some valid, some nodata
            mixed_data = np.random.randint(1, 1000, (4, 50, 50), dtype=np.uint16)
            mixed_data[:, :25, :] = 0  # Half nodata
            mock_src.read.return_value = mixed_data
            
            mock_dst = Mock()
            mock_rasterio_open.side_effect = [
                Mock(__enter__=Mock(return_value=mock_src), __exit__=Mock()),
                Mock(__enter__=Mock(return_value=mock_dst), __exit__=Mock())
            ]
            
            with patch.object(mock_predictor, '_sieve_inplace'):
                result = mock_predictor._predict_single_cog(
                    cog_url="http://example.com/mixed.tif",
                    basemap_date="2022-01", 
                    pred_dir=temp_prediction_dir
                )
            
            assert isinstance(result, Path)
            # Should call model.predict on valid pixels only
            assert len(mock_predictor.model.predict_calls) > 0


# How to run these specific tests:
#
# Run all predictor unit tests:
# docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh unit -k predictor"
#
# Run specific test class:
# docker compose exec backend bash -c "cd /app/ml_pipeline && python -m pytest tests/unit/test_predictor_unit.py::TestModelPredictorInit -v"
#
# Run specific test:
# docker compose exec backend bash -c "cd /app/ml_pipeline && python -m pytest tests/unit/test_predictor_unit.py::TestModelPredictorInit::test_init_with_valid_model_file -v"