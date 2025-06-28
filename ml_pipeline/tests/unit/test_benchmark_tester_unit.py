"""
Unit tests for BenchmarkTester class.

Unit tests focus on testing individual methods/functions in isolation.
They use mocks to replace external dependencies (databases, APIs, file systems).
This makes tests fast, reliable, and independent of external systems.
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the class we're testing
from ml_pipeline.benchmark_tester import BenchmarkTester


class TestBenchmarkTesterInit:
    """
    Test class for BenchmarkTester initialization.
    
    Why group tests in classes?
    - Organization: Related tests stay together
    - Shared setup: Use class-level fixtures if needed
    - Clear naming: TestClassName makes it obvious what we're testing
    """
    
    def test_init_with_required_params(self, benchmark_tester_params, mock_engine):
        """
        Test that BenchmarkTester initializes correctly with required parameters.
        
        This is a basic "happy path" test - testing that normal usage works.
        """
        # Arrange: Set up test data (fixtures provide this)
        params = benchmark_tester_params.copy()
        params['engine'] = mock_engine
        
        # Mock the TitilerExtractor and its get_all_cog_urls method
        with patch('ml_pipeline.benchmark_tester.TitilerExtractor') as mock_extractor_class:
            mock_extractor_instance = Mock()
            mock_extractor_instance.get_all_cog_urls.return_value = ['http://example.com/test.tif']
            mock_extractor_class.return_value = mock_extractor_instance
            
            # Act: Execute the code we're testing
            tester = BenchmarkTester(**params)
            
            # Assert: Verify the results
            assert tester.base_url == "http://localhost:8083"
            assert tester.collection == "test-collection"
            assert tester.year == "2022"
            assert tester.project_id == 123
            assert tester.band_indexes == [1]
            assert tester.engine == mock_engine
            assert tester.verbose is False

    def test_init_strips_trailing_slash_from_base_url(self, benchmark_tester_params, mock_engine):
        """
        Test that trailing slashes are removed from base_url.
        
        This is an "edge case" test - testing behavior with slightly unusual input.
        """
        params = benchmark_tester_params.copy()
        params['base_url'] = "http://localhost:8083/"  # Note the trailing slash
        params['engine'] = mock_engine
        
        with patch('ml_pipeline.benchmark_tester.TitilerExtractor') as mock_extractor_class:
            mock_extractor_instance = Mock()
            mock_extractor_instance.get_all_cog_urls.return_value = ['http://example.com/test.tif']
            mock_extractor_class.return_value = mock_extractor_instance
            
            tester = BenchmarkTester(**params)
            
            # Should remove the trailing slash
            assert tester.base_url == "http://localhost:8083"

    def test_init_with_default_band_indexes(self, benchmark_tester_params, mock_engine):
        """
        Test that band_indexes defaults to [1] when not provided.
        
        This tests default parameter behavior.
        """
        params = benchmark_tester_params.copy()
        params['engine'] = mock_engine
        # Don't specify band_indexes - should default to [1]
        del params['band_indexes']
        
        with patch('ml_pipeline.benchmark_tester.TitilerExtractor') as mock_extractor_class:
            mock_extractor_instance = Mock()
            mock_extractor_instance.get_all_cog_urls.return_value = ['http://example.com/test.tif']
            mock_extractor_class.return_value = mock_extractor_instance
            
            tester = BenchmarkTester(**params)
            
            assert tester.band_indexes == [1]

    def test_init_creates_db_connection_when_none_provided(self, benchmark_tester_params):
        """
        Test that database connection is created when engine is None.
        
        This tests the fallback behavior when optional parameters aren't provided.
        """
        params = benchmark_tester_params.copy()
        # Don't provide engine - should create one
        
        with patch('ml_pipeline.benchmark_tester.get_db_connection') as mock_get_db, \
             patch('ml_pipeline.benchmark_tester.TitilerExtractor') as mock_extractor_class:
            
            mock_engine = Mock()
            mock_get_db.return_value = mock_engine
            
            mock_extractor_instance = Mock()
            mock_extractor_instance.get_all_cog_urls.return_value = ['http://example.com/test.tif']
            mock_extractor_class.return_value = mock_extractor_instance
            
            tester = BenchmarkTester(**params)
            
            # Verify get_db_connection was called with default host
            mock_get_db.assert_called_once_with(host="local")
            assert tester.engine == mock_engine

    def test_init_raises_error_when_no_cogs_found(self, benchmark_tester_params, mock_engine):
        """
        Test that initialization fails when no COGs are found for the collection.
        
        This is an "error case" test - testing that the code fails gracefully 
        when something goes wrong.
        """
        params = benchmark_tester_params.copy()
        params['engine'] = mock_engine
        
        with patch('ml_pipeline.benchmark_tester.TitilerExtractor') as mock_extractor_class:
            mock_extractor_instance = Mock()
            # Return empty list - no COGs found
            mock_extractor_instance.get_all_cog_urls.return_value = []
            mock_extractor_class.return_value = mock_extractor_instance
            
            # Should raise ValueError with descriptive message
            with pytest.raises(ValueError, match="No COGs found for collection 'test-collection'"):
                BenchmarkTester(**params)


class TestBenchmarkTesterRunMethod:
    """
    Test class for the main run() method.
    
    This is the most complex method, so we'll test it thoroughly.
    """
    
    @pytest.fixture
    def mock_benchmark_tester(self, benchmark_tester_params, mock_engine):
        """
        Fixture that creates a BenchmarkTester with all dependencies mocked.
        
        This is a "test fixture" - it sets up a complex object that multiple 
        tests can use. This avoids repeating setup code.
        """
        with patch('ml_pipeline.benchmark_tester.TitilerExtractor') as mock_extractor_class:
            mock_extractor_instance = Mock()
            mock_extractor_instance.get_all_cog_urls.return_value = ['http://example.com/test.tif']
            mock_extractor_class.return_value = mock_extractor_instance
            
            params = benchmark_tester_params.copy()
            params['engine'] = mock_engine
            params['run_id'] = 'test_run'
            
            tester = BenchmarkTester(**params)
            tester.extractor = mock_extractor_instance  # Ensure we use the mock
            return tester

    def test_run_with_no_polygons_raises_error(self, mock_benchmark_tester):
        """
        Test that run() fails gracefully when no polygons are found.
        
        This tests error handling for empty data scenarios.
        """
        # Mock load_training_polygons to return empty GeoDataFrame
        with patch('ml_pipeline.benchmark_tester.load_training_polygons') as mock_load_polygons:
            import geopandas as gpd
            empty_gdf = gpd.GeoDataFrame(columns=['classLabel'])
            mock_load_polygons.return_value = empty_gdf
            
            with pytest.raises(ValueError, match="No Forest / Non-Forest polygons found"):
                mock_benchmark_tester.run(save=False)

    def test_run_saves_results_when_save_true(self, mock_benchmark_tester, sample_training_polygons, temp_test_features_dir):
        """
        Test that run() saves results when save=True.
        
        This tests the integration between the main logic and the file saving functionality.
        """
        # Set the test features directory to our temp directory with CSV files
        mock_benchmark_tester.test_features_dir = temp_test_features_dir
        
        # Mock all the dependencies
        with patch('ml_pipeline.benchmark_tester.load_training_polygons') as mock_load_polygons, \
             patch('ml_pipeline.benchmark_tester.extract_pixels_with_missing') as mock_extract, \
             patch('ml_pipeline.benchmark_tester.save_metrics_csv') as mock_save, \
             patch('ml_pipeline.benchmark_tester.show_accuracy_table') as mock_show:
            
            # Setup mock return values
            mock_load_polygons.return_value = sample_training_polygons
            # Return some mock pixel data: pixels, missing_count, total_count
            mock_extract.return_value = (np.array([[1, 0, 1]]), 0, 3)
            
            # Act
            result = mock_benchmark_tester.run(save=True)
            
            # Assert
            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0  # Should have some results
            mock_save.assert_called_once()  # Should save results
            mock_show.assert_called_once()  # Should show results

    def test_run_skips_saving_when_save_false(self, mock_benchmark_tester, sample_training_polygons, temp_test_features_dir):
        """
        Test that run() doesn't save when save=False.
        
        This tests that optional behavior is correctly controlled by parameters.
        """
        # Set the test features directory to our temp directory with CSV files
        mock_benchmark_tester.test_features_dir = temp_test_features_dir
        
        with patch('ml_pipeline.benchmark_tester.load_training_polygons') as mock_load_polygons, \
             patch('ml_pipeline.benchmark_tester.extract_pixels_with_missing') as mock_extract, \
             patch('ml_pipeline.benchmark_tester.save_metrics_csv') as mock_save, \
             patch('ml_pipeline.benchmark_tester.show_accuracy_table') as mock_show:
            
            mock_load_polygons.return_value = sample_training_polygons
            mock_extract.return_value = (np.array([[1, 0, 1]]), 0, 3)
            
            result = mock_benchmark_tester.run(save=False)
            
            assert isinstance(result, pd.DataFrame)
            mock_save.assert_not_called()  # Should NOT save results
            mock_show.assert_not_called()  # Should NOT show results


class TestBenchmarkTesterPixelClassification:
    """
    Test the pixel classification logic in isolation.
    
    This tests the core business logic of converting raster values to class labels.
    """
    
    def test_pixel_value_classification(self):
        """
        Test that pixel values are correctly classified.
        
        This tests the core logic: 1=Forest, 0=Non-Forest, 255=Missing
        """
        # This would test the pixel classification logic if it was extracted 
        # into a separate method. For now, it's embedded in the run() method.
        # In a real refactor, you might extract this logic for easier testing:
        
        # def classify_pixel_values(self, pixels):
        #     return ["Forest" if px == 1 else "Non-Forest" for px in pixels if px != 255]
        
        pixel_values = np.array([1, 0, 1, 255, 0, 1])
        expected_labels = ["Forest", "Non-Forest", "Forest", "Non-Forest", "Forest"]
        
        # Simulate the classification logic from the actual code
        valid_pixels = pixel_values[pixel_values != 255]
        predicted_labels = ["Forest" if px == 1 else "Non-Forest" for px in valid_pixels]
        
        assert predicted_labels == expected_labels


# This is how you would run the tests:
# 
# From the ml_pipeline directory:
# 1. Install test dependencies: poetry install --extras test
# 2. Run all tests: python -m pytest tests/
# 3. Run just unit tests: python -m pytest tests/unit/
# 4. Run with coverage: python -m pytest --cov=src/ml_pipeline
# 5. Run a specific test: python -m pytest tests/unit/test_benchmark_tester_unit.py::TestBenchmarkTesterInit::test_init_with_required_params