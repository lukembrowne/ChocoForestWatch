"""
Integration tests for ModelPredictor class.

Integration tests test how multiple components work together and may use
real file systems, temporary files, and actual rasterio operations.
These tests are slower but catch issues that unit tests miss.
"""
import pytest
import numpy as np
import rasterio
from pathlib import Path
import tempfile
import pickle
from unittest.mock import Mock, patch

from ml_pipeline.predictor import ModelPredictor, PredictorConfig


@pytest.mark.integration
class TestModelPredictorWithRealFiles:
    """
    Integration tests that use real temporary files and rasterio operations.
    
    These tests verify that the Predictor can actually read/write raster files
    and handle real file system operations.
    """
    
    @pytest.fixture
    def real_model_file(self, mock_trained_model):
        """Create a real pickle file on disk for testing."""
        model_bundle = {
            'model': mock_trained_model,
            'meta': {
                'feature_names': ['red', 'green', 'blue', 'nir'],
                'class_names': ['Non-Forest', 'Forest'],
                'training_date': '2022-01-01'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pkl', delete=False) as f:
            pickle.dump(model_bundle, f)
            temp_path = Path(f.name)
        
        yield temp_path
        
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture 
    def real_test_raster(self):
        """Create a real test raster file using rasterio."""
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as f:
            temp_path = Path(f.name)
        
        # Create a small 4-band test raster
        profile = {
            'driver': 'GTiff',
            'dtype': 'uint16',
            'nodata': 0,
            'width': 100,
            'height': 100,
            'count': 4,
            'crs': 'EPSG:3857',
            'transform': rasterio.transform.from_bounds(-80, -1, -79, 0, 100, 100)
        }
        
        with rasterio.open(temp_path, 'w', **profile) as dst:
            # Write realistic 4-band data (RGBN)
            for band in range(1, 5):
                data = np.random.randint(0, 1000, (100, 100), dtype=np.uint16)
                # Add some nodata pixels
                data[:10, :10] = 0  # nodata region
                dst.write(data, band)
        
        yield temp_path
        
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_predictor_init_with_real_model_file(self, real_model_file, mock_extractor_for_predictor):
        """Test that ModelPredictor can load a real pickle file."""
        predictor = ModelPredictor(
            model_path=real_model_file,
            extractor=mock_extractor_for_predictor,
            upload_to_s3=False,
            s3_path='test/path'
        )
        
        assert predictor.model is not None
        assert predictor.meta is not None
        assert 'feature_names' in predictor.meta
        assert predictor.model_path == real_model_file

    def test_predict_single_cog_with_real_raster(self, real_model_file, real_test_raster, 
                                                 mock_extractor_for_predictor, temp_prediction_dir):
        """Test prediction on a real raster file."""
        predictor = ModelPredictor(
            model_path=real_model_file,
            extractor=mock_extractor_for_predictor,
            upload_to_s3=False,
            s3_path='test/path'
        )
        
        # Mock the COG URL to point to our real test raster
        cog_url = f"file://{real_test_raster}"
        
        # Store original rasterio.open before patching to avoid recursion
        original_rasterio_open = rasterio.open
        
        with patch.object(predictor, '_sieve_inplace') as mock_sieve, \
             patch('ml_pipeline.predictor.rasterio.open') as mock_rasterio_open:
            
            # Use real rasterio.open for reading, mock for writing
            def rasterio_open_side_effect(path, mode='r', **kwargs):
                if mode == 'r':
                    return original_rasterio_open(real_test_raster)
                else:
                    # Mock the write operation
                    mock_dst = Mock()
                    mock_dst.__enter__ = Mock(return_value=mock_dst)
                    mock_dst.__exit__ = Mock(return_value=None)
                    mock_dst.write = Mock()
                    return mock_dst
            
            mock_rasterio_open.side_effect = rasterio_open_side_effect
            
            result = predictor._predict_single_cog(
                cog_url=cog_url,
                basemap_date="2022-01",
                pred_dir=temp_prediction_dir,
                save_local=True
            )
            
            # Should complete successfully
            assert isinstance(result, Path)
            assert result.suffix == '.tiff'
            mock_sieve.assert_called_once()

    def test_predictor_config_integration(self, real_model_file, mock_extractor_for_predictor):
        """Test that PredictorConfig settings are properly used."""
        custom_config = PredictorConfig(
            blocksize=256,
            compress="jpeg",
            dtype="uint16",
            nodata=9999,
            predictor=1
        )
        
        predictor = ModelPredictor(
            model_path=real_model_file,
            extractor=mock_extractor_for_predictor,
            upload_to_s3=False,
            s3_path='test/path',
            cfg=custom_config
        )
        
        assert predictor.cfg.blocksize == 256
        assert predictor.cfg.compress == "jpeg"
        assert predictor.cfg.dtype == "uint16"
        assert predictor.cfg.nodata == 9999

    def test_directory_creation_integration(self, real_model_file, mock_extractor_for_predictor):
        """Test that prediction directory is actually created."""
        predictor = ModelPredictor(
            model_path=real_model_file,
            extractor=mock_extractor_for_predictor,
            upload_to_s3=False,
            s3_path='test/path'
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = Path(temp_dir) / "predictions" / "subdir"
            assert not nonexistent_dir.exists()
            
            with patch.object(predictor, '_predict_single_cog') as mock_predict:
                mock_predict.return_value = nonexistent_dir / "test.tiff"
                
                predictor.predict_collection(
                    basemap_date="2022-01",
                    collection="test-collection",
                    pred_dir=nonexistent_dir
                )
                
                # Directory should be created
                assert nonexistent_dir.exists()


@pytest.mark.integration
@pytest.mark.slow
class TestModelPredictorWorkflows:
    """
    Integration tests for complete prediction workflows.
    
    These tests exercise the full prediction pipeline but with controlled inputs.
    """
    
    @pytest.fixture
    def predictor_with_real_files(self, real_model_file, mock_extractor_for_predictor):
        """Create a predictor with real model file for workflow testing."""
        return ModelPredictor(
            model_path=real_model_file,
            extractor=mock_extractor_for_predictor,
            upload_to_s3=False,
            s3_path='test/workflows'
        )

    @pytest.fixture
    def real_model_file(self, mock_trained_model):
        """Create a real pickle file on disk for testing."""
        model_bundle = {
            'model': mock_trained_model,
            'meta': {
                'feature_names': ['red', 'green', 'blue', 'nir'],
                'class_names': ['Non-Forest', 'Forest'],
                'training_date': '2022-01-01'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pkl', delete=False) as f:
            pickle.dump(model_bundle, f)
            temp_path = Path(f.name)
        
        yield temp_path
        
        if temp_path.exists():
            temp_path.unlink()


    def test_predict_collection_workflow_with_parallelization(self, predictor_with_real_files, temp_prediction_dir):
        """Test predict_collection workflow including parallel processing."""
        # Test that parallel processing is set up correctly
        with patch('ml_pipeline.predictor.Parallel') as mock_parallel, \
             patch.object(predictor_with_real_files, '_predict_single_cog') as mock_predict_single:
            
            # Mock Parallel to return a mock object that we can call
            mock_parallel_instance = Mock()
            mock_parallel.return_value = mock_parallel_instance
            mock_parallel_instance.return_value = [
                temp_prediction_dir / f"tile_{i}.tiff" for i in range(3)
            ]
            
            result = predictor_with_real_files.predict_collection(
                basemap_date="2022-06",
                collection="test-collection",
                pred_dir=temp_prediction_dir,
                save_local=True
            )
            
            # Should set up parallel processing with correct parameters
            mock_parallel.assert_called_once_with(n_jobs=8, prefer="processes")
            assert len(result) == 3

    def test_s3_upload_integration_workflow(self, predictor_with_real_files, temp_prediction_dir):
        """Test workflow with S3 upload enabled."""
        # Enable S3 upload
        predictor_with_real_files.upload_to_s3 = True
        predictor_with_real_files.s3_path = "integration/test/predictions"
        
        with patch.object(predictor_with_real_files, '_upload_to_s3') as mock_upload, \
             patch('ml_pipeline.predictor.rasterio.open') as mock_rasterio_open, \
             patch.object(predictor_with_real_files, '_sieve_inplace') as mock_sieve:
            
            # Mock successful raster operations
            mock_src = Mock()
            mock_src.profile = {'count': 4, 'dtype': 'uint16', 'nodata': 0}
            mock_src.nodata = 0
            mock_src.block_windows.return_value = [((0, 0), Mock())]
            mock_src.read.return_value = np.random.randint(1, 1000, (4, 50, 50), dtype=np.uint16)
            
            mock_dst = Mock()
            mock_rasterio_open.side_effect = [
                Mock(__enter__=Mock(return_value=mock_src), __exit__=Mock()),
                Mock(__enter__=Mock(return_value=mock_dst), __exit__=Mock())
            ]
            
            result = predictor_with_real_files._predict_single_cog(
                cog_url="http://example.com/test.tif",
                basemap_date="2022-08",
                pred_dir=temp_prediction_dir,
                save_local=True
            )
            
            # Should call upload to S3
            mock_upload.assert_called_once_with(result, "2022-08")


@pytest.mark.integration
class TestModelPredictorErrorHandling:
    """
    Integration tests for error handling in realistic scenarios.
    """

    def test_disk_space_simulation(self, real_model_file, mock_extractor_for_predictor, temp_prediction_dir):
        """Test behavior when disk operations fail (simulating disk full)."""
        predictor = ModelPredictor(
            model_path=real_model_file,
            extractor=mock_extractor_for_predictor,
            upload_to_s3=False,
            s3_path='test/path'
        )
        
        with patch('ml_pipeline.predictor.rasterio.open') as mock_rasterio_open:
            # Simulate disk write failure
            mock_rasterio_open.side_effect = OSError("No space left on device")
            
            result = predictor._predict_single_cog(
                cog_url="http://example.com/test.tif",
                basemap_date="2022-01",
                pred_dir=temp_prediction_dir
            )
            
            # Should handle error gracefully and return None
            assert result is None

    def test_corrupted_raster_data_handling(self, real_model_file, mock_extractor_for_predictor, temp_prediction_dir):
        """Test handling of corrupted raster data."""
        predictor = ModelPredictor(
            model_path=real_model_file,
            extractor=mock_extractor_for_predictor,
            upload_to_s3=False,
            s3_path='test/path'
        )
        
        with patch('ml_pipeline.predictor.rasterio.open') as mock_rasterio_open:
            # Mock corrupted raster that fails during read
            mock_src = Mock()
            mock_src.profile = {'count': 4, 'dtype': 'uint16', 'nodata': 0}
            mock_src.block_windows.return_value = [((0, 0), Mock())]
            mock_src.read.side_effect = Exception("Corrupted raster data")
            
            # Mock the write operation for output file
            mock_dst = Mock()
            mock_dst.__enter__ = Mock(return_value=mock_dst)
            mock_dst.__exit__ = Mock(return_value=None)
            mock_dst.write = Mock()
            
            def rasterio_open_side_effect(path, mode='r', **kwargs):
                if mode == 'r':
                    # Return the context manager that yields the corrupted source
                    mock_cm = Mock()
                    mock_cm.__enter__ = Mock(return_value=mock_src)
                    mock_cm.__exit__ = Mock(return_value=None)
                    return mock_cm
                else:  # write mode
                    return mock_dst
            
            mock_rasterio_open.side_effect = rasterio_open_side_effect
            
            result = predictor._predict_single_cog(
                cog_url="http://example.com/corrupted.tif",
                basemap_date="2022-01",
                pred_dir=temp_prediction_dir
            )
            
            # Should handle corrupted data gracefully and still return a path
            # (individual window failures should not prevent file creation)
            assert isinstance(result, Path)
            assert result.suffix == '.tiff'


@pytest.fixture
def real_model_file(mock_trained_model):
    """Create a real pickle file on disk for testing (scoped to module)."""
    model_bundle = {
        'model': mock_trained_model,
        'meta': {
            'feature_names': ['red', 'green', 'blue', 'nir'],
            'class_names': ['Non-Forest', 'Forest'],
            'training_date': '2022-01-01'
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pkl', delete=False) as f:
        pickle.dump(model_bundle, f)
        temp_path = Path(f.name)
    
    yield temp_path
    
    if temp_path.exists():
        temp_path.unlink()


# How to run these integration tests:
#
# Run all predictor integration tests:
# docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh integration -k predictor"
#
# Run without slow tests:
# docker compose exec backend bash -c "cd /app/ml_pipeline && python -m pytest tests/integration/test_predictor_integration.py -m 'integration and not slow' -v"
#
# Run specific integration test:
# docker compose exec backend bash -c "cd /app/ml_pipeline && python -m pytest tests/integration/test_predictor_integration.py::TestModelPredictorWithRealFiles::test_predictor_init_with_real_model_file -v"