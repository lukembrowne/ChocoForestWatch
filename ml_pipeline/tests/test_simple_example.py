"""
Simple example test to verify pytest setup works.

This is a minimal test to confirm everything is configured correctly.
Run this first to make sure your testing environment is working.
"""
import pytest
import numpy as np


def test_pytest_works():
    """Basic test to verify pytest is working."""
    assert True


def test_fixtures_work(sample_project_id, sample_year):
    """Test that fixtures from conftest.py are available."""
    assert sample_project_id == 123
    assert sample_year == "2022"


def test_sample_data_fixtures(sample_training_polygons, sample_pixel_data):
    """Test that more complex fixtures work."""
    # Test the training polygons fixture
    assert len(sample_training_polygons) == 3
    assert 'classLabel' in sample_training_polygons.columns
    assert set(sample_training_polygons['classLabel']) == {'Forest', 'Non-Forest'}
    
    # Test the pixel data fixture
    assert sample_pixel_data.shape == (4, 4)
    assert sample_pixel_data.dtype == np.uint8
    unique_values = np.unique(sample_pixel_data)
    # Should contain values: 0 (Non-Forest), 1 (Forest), 255 (Missing)
    expected_values = {0, 1, 255}
    assert set(unique_values).issubset(expected_values)


@pytest.mark.unit
def test_unit_marker():
    """Test that unit test marker works."""
    assert 1 + 1 == 2


@pytest.mark.integration  
def test_integration_marker():
    """Test that integration test marker works."""
    assert "hello" + " world" == "hello world"


@pytest.mark.slow
def test_slow_marker():
    """Test that slow test marker works."""
    # This would be a slow operation in real tests
    import time
    time.sleep(0.1)  # Simulate slow operation
    assert True