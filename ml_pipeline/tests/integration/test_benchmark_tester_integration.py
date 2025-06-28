"""
Integration tests for BenchmarkTester class.

Integration tests focus on testing how multiple components work together.
They may use real databases, test servers, or actual file systems.
These tests are slower but catch issues that unit tests miss.

The key difference from unit tests:
- Unit tests: Test one function with mocked dependencies
- Integration tests: Test multiple components working together with real/realistic dependencies
"""
import pytest
import pandas as pd
import geopandas as gpd
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, Mock

from ml_pipeline.benchmark_tester import BenchmarkTester


@pytest.mark.integration
class TestBenchmarkTesterWithRealFiles:
    """
    Integration tests that use real file systems and temporary directories.
    
    The @pytest.mark.integration decorator allows you to run/skip these tests:
    - Run only integration tests: pytest -m integration
    - Skip integration tests: pytest -m "not integration"
    """
    
    def test_with_held_out_csv_files(self, benchmark_tester_params, mock_engine, temp_test_features_dir):
        """
        Test BenchmarkTester with real CSV files in temporary directory.
        
        This tests the file reading logic with actual files, but still mocks
        the database and external services for speed and reliability.
        """
        # Arrange: Set up BenchmarkTester with real CSV directory
        params = benchmark_tester_params.copy()
        params['engine'] = mock_engine
        params['run_id'] = None  # Don't use run_id
        params['test_features_dir'] = temp_test_features_dir  # Use real temp directory
        
        with patch('ml_pipeline.benchmark_tester.TitilerExtractor') as mock_extractor_class:
            mock_extractor_instance = Mock()
            mock_extractor_instance.get_all_cog_urls.return_value = ['http://example.com/test.tif']
            mock_extractor_class.return_value = mock_extractor_instance
            
            # Act: Create BenchmarkTester
            tester = BenchmarkTester(**params)
            
            # Assert: Should find the test features directory
            assert tester.test_features_dir == temp_test_features_dir
            assert tester.test_features_dir.exists()
            
            # Verify CSV files exist for each month
            for month in range(1, 13):
                month_str = f"2022-{month:02d}"
                csv_path = tester.test_features_dir / f"test_features_{month_str}.csv"
                assert csv_path.exists()
                
                # Verify CSV content
                df = pd.read_csv(csv_path)
                assert 'feature_id' in df.columns
                assert len(df) > 0

    def test_run_id_creates_correct_path(self, benchmark_tester_params, mock_engine):
        """
        Test that run_id creates the correct directory path.
        
        This tests the path construction logic without needing the actual directories.
        """
        params = benchmark_tester_params.copy()
        params['engine'] = mock_engine
        params['run_id'] = 'test_run_123'
        
        with patch('ml_pipeline.benchmark_tester.TitilerExtractor') as mock_extractor_class:
            mock_extractor_instance = Mock()
            mock_extractor_instance.get_all_cog_urls.return_value = ['http://example.com/test.tif']
            mock_extractor_class.return_value = mock_extractor_instance
            
            tester = BenchmarkTester(**params)
            
            # Should construct path: ml_pipeline/runs/test_run_123/feature_ids_testing/
            expected_path = Path(__file__).parent.parent.parent / "runs" / "test_run_123" / "feature_ids_testing"
            assert tester.test_features_dir == expected_path


@pytest.mark.integration  
@pytest.mark.slow
class TestBenchmarkTesterWithMockServices:
    """
    Integration tests that mock external services but test the full workflow.
    
    These tests are marked as "slow" because they run the complete algorithm,
    just with mocked data sources.
    """
    
    def test_complete_workflow_single_month(self, benchmark_tester_params, mock_engine, sample_training_polygons):
        """
        Test the complete workflow for a single month with realistic data.
        
        This is an end-to-end test that exercises the entire run() method
        but with controlled, predictable inputs.
        """
        params = benchmark_tester_params.copy()
        params['engine'] = mock_engine
        params['run_id'] = 'test_run'
        
        with patch('ml_pipeline.benchmark_tester.TitilerExtractor') as mock_extractor_class, \
             patch('ml_pipeline.benchmark_tester.load_training_polygons') as mock_load_polygons, \
             patch('ml_pipeline.benchmark_tester.extract_pixels_with_missing') as mock_extract, \
             patch('ml_pipeline.benchmark_tester.save_metrics_csv') as mock_save, \
             patch('ml_pipeline.benchmark_tester.show_accuracy_table') as mock_show:
            
            # Setup mocks
            mock_extractor_instance = Mock()
            mock_extractor_instance.get_all_cog_urls.return_value = ['http://example.com/test.tif']
            mock_extractor_class.return_value = mock_extractor_instance
            
            # Return training polygons for each month (BenchmarkTester loops through all 12 months)
            mock_load_polygons.return_value = sample_training_polygons
            
            # Mock pixel extraction to return realistic data
            # Simulate extracting different pixels for each polygon
            def mock_extract_side_effect(extractor, geometry, band_indexes, verbose=False):
                # Return different pixel patterns for different polygons
                if hasattr(geometry, 'bounds'):
                    bounds = geometry.bounds
                    if bounds[0] < -79.8:  # First polygon
                        return (np.array([[1, 1, 1, 0]]), 1, 5)  # Mostly forest
                    elif bounds[0] < -79.7:  # Second polygon  
                        return (np.array([[0, 0, 1, 0]]), 0, 4)  # Mostly non-forest
                    else:  # Third polygon
                        return (np.array([[1, 0, 1, 1]]), 2, 6)  # Mixed with missing data
                return (np.array([[1, 0]]), 0, 2)
            
            mock_extract.side_effect = mock_extract_side_effect
            
            # Act: Run the complete workflow
            tester = BenchmarkTester(**params)
            result_df = tester.run(save=True)
            
            # Assert: Verify results structure
            assert isinstance(result_df, pd.DataFrame)
            assert len(result_df) > 0
            
            # Should have monthly results plus overall summary
            months_in_result = result_df['month'].unique()
            assert 'overall' in months_in_result
            
            # Verify required columns exist
            required_columns = [
                'run_id', 'collection', 'month', 'n_polygons', 'n_pixels',
                'accuracy', 'f1_forest', 'f1_nonforest', 'missing_pct'
            ]
            for col in required_columns:
                assert col in result_df.columns
            
            # Verify metrics are reasonable
            overall_row = result_df[result_df['month'] == 'overall'].iloc[0]
            assert 0 <= overall_row['accuracy'] <= 1
            assert 0 <= overall_row['missing_pct'] <= 1
            assert overall_row['n_pixels'] > 0
            
            # Verify save functions were called
            mock_save.assert_called_once()
            mock_show.assert_called_once()


@pytest.mark.integration
class TestBenchmarkTesterErrorHandling:
    """
    Integration tests for error handling scenarios.
    
    These test what happens when external dependencies fail or return 
    unexpected data - important for production robustness.
    """
    
    def test_database_connection_failure(self, benchmark_tester_params):
        """
        Test behavior when database connection fails.
        """
        params = benchmark_tester_params.copy()
        # Don't provide engine, force it to try creating one
        
        with patch('ml_pipeline.benchmark_tester.get_db_connection') as mock_get_db, \
             patch('ml_pipeline.benchmark_tester.TitilerExtractor') as mock_extractor_class:
            
            # Make database connection fail
            mock_get_db.side_effect = Exception("Database connection failed")
            
            mock_extractor_instance = Mock()
            mock_extractor_instance.get_all_cog_urls.return_value = ['http://example.com/test.tif']
            mock_extractor_class.return_value = mock_extractor_instance
            
            # Should propagate the database error
            with pytest.raises(Exception, match="Database connection failed"):
                BenchmarkTester(**params)

    def test_polygon_loading_failure(self, benchmark_tester_params, mock_engine):
        """
        Test behavior when polygon loading fails.
        """
        params = benchmark_tester_params.copy()
        params['engine'] = mock_engine
        params['run_id'] = 'test_run'
        
        with patch('ml_pipeline.benchmark_tester.TitilerExtractor') as mock_extractor_class, \
             patch('ml_pipeline.benchmark_tester.load_training_polygons') as mock_load_polygons:
            
            mock_extractor_instance = Mock()
            mock_extractor_instance.get_all_cog_urls.return_value = ['http://example.com/test.tif']
            mock_extractor_class.return_value = mock_extractor_instance
            
            # Make polygon loading fail
            mock_load_polygons.side_effect = Exception("Failed to load polygons from database")
            
            tester = BenchmarkTester(**params)
            
            # Should wrap the error with context
            with pytest.raises(RuntimeError, match="Failed to load polygons for 2022-01"):
                tester.run(save=False)


# How to run these integration tests:
#
# 1. Run all tests: pytest tests/
# 2. Run only integration tests: pytest -m integration
# 3. Skip slow tests: pytest -m "not slow" 
# 4. Run integration but not slow: pytest -m "integration and not slow"
# 5. Run with verbose output: pytest -v tests/integration/