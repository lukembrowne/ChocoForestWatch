# Testing Guide for ML Pipeline

This guide explains how to write, run, and maintain tests for the ML Pipeline using pytest in a Docker environment with Poetry.

## Overview

We use **pytest** as our testing framework because it's:
- More powerful than unittest
- Excellent fixture support  
- Great Docker integration
- Industry standard for Python testing

## Test Structure

```
ml_pipeline/tests/
├── conftest.py                    # Shared fixtures for all tests
├── test_simple_example.py         # Basic setup verification tests
├── unit/                          # Unit tests (fast, isolated)
│   └── test_benchmark_tester_unit.py
├── integration/                   # Integration tests (slower, realistic)
│   └── test_benchmark_tester_integration.py
└── fixtures/                     # Test data files
```

## Running Tests

### Using Our Docker Test Runner

```bash
# Run all tests quickly (recommended for development)
docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh quick"

# Run only unit tests
docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh unit"

# Run only integration tests  
docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh integration"

# Run tests with coverage reporting
docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh coverage"

# Run basic setup tests
docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh simple"
```

### Using pytest directly

```bash
# Enter the backend container
docker compose exec backend bash

# Navigate to ml_pipeline directory
cd /app/ml_pipeline

# Run specific tests
python -m pytest tests/unit/test_benchmark_tester_unit.py::TestBenchmarkTesterInit::test_init_with_required_params -v

# Run tests by marker
python -m pytest -m unit          # Only unit tests
python -m pytest -m integration   # Only integration tests
python -m pytest -m "not slow"    # Skip slow tests

# Run with coverage
python -m pytest --cov=src/ml_pipeline --cov-report=html
```

## Test Types Explained

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual functions/methods in isolation
- **Speed**: Very fast (milliseconds)
- **Dependencies**: All external dependencies are mocked
- **When to use**: Testing business logic, edge cases, error handling

Example:
```python
def test_init_with_required_params(self, benchmark_tester_params, mock_engine):
    # This tests ONLY the initialization logic
    # Database, TiTiler, file system are all mocked
    with patch('ml_pipeline.benchmark_tester.TitilerExtractor'):
        tester = BenchmarkTester(**params)
        assert tester.project_id == 123
```

### Integration Tests (`tests/integration/`)
- **Purpose**: Test how multiple components work together
- **Speed**: Slower (seconds)
- **Dependencies**: Some real dependencies (files, temp databases)
- **When to use**: Testing workflows, API integrations, file operations

Example:
```python
def test_with_held_out_csv_files(self, temp_test_features_dir):
    # This tests with REAL CSV files in a temporary directory
    # Database and TiTiler are still mocked for speed
    tester = BenchmarkTester(test_features_dir=temp_test_features_dir)
    # Test file reading logic works with actual files
```

## Key Testing Concepts

### 1. Fixtures (Test Data)
Fixtures provide clean, reusable test data. They're defined in `conftest.py`:

```python
@pytest.fixture
def sample_project_id():
    return 123

def test_something(sample_project_id):
    # pytest automatically provides sample_project_id=123
    assert sample_project_id == 123
```

### 2. Mocking (Fake Dependencies)
Mocks replace external dependencies to make tests fast and reliable:

```python
with patch('ml_pipeline.benchmark_tester.TitilerExtractor') as mock_extractor:
    mock_extractor.return_value.get_all_cog_urls.return_value = ['fake.tif']
    # Now your code gets fake data instead of hitting real TiTiler API
```

### 3. Test Organization
- Group related tests in classes: `TestBenchmarkTesterInit`
- Use descriptive names: `test_init_raises_error_when_no_cogs_found`
- Follow Arrange-Act-Assert pattern

## Writing New Tests

### 1. Choose the Test Type
- **Unit test** if testing a single function with no external dependencies
- **Integration test** if testing multiple components or external services

### 2. Create Test File
- Unit tests: `tests/unit/test_[module_name]_unit.py`
- Integration tests: `tests/integration/test_[module_name]_integration.py`

### 3. Follow the Pattern
```python
class TestYourClassOrModule:
    def test_specific_behavior(self, fixture1, fixture2):
        # Arrange: Set up test data
        params = {...}
        
        # Act: Execute the code being tested
        result = function_under_test(params)
        
        # Assert: Verify the results
        assert result == expected_value
```

### 4. Add Fixtures if Needed
Add new fixtures to `conftest.py` if you need reusable test data.

## CI/CD Integration

Tests run automatically in GitHub Actions:

1. **On Pull Requests**: Full test suite runs to ensure changes don't break anything
2. **Before Deployment**: Unit tests run before deploying to production
3. **Coverage Reports**: Generated and uploaded as artifacts

## Best Practices

### ✅ Do:
- Write tests for new features and bug fixes
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies in unit tests
- Use fixtures for reusable test data

### ❌ Don't:
- Make tests depend on external services (use mocks)
- Write tests that modify production data
- Create tests that depend on specific test execution order
- Skip writing tests for "simple" functions

## Debugging Failed Tests

1. **Read the error message**: pytest gives detailed failure information
2. **Run specific test**: Isolate the failing test
3. **Add print statements**: Temporary debugging (remove afterward)
4. **Use pytest debugging**: `python -m pytest --pdb` to drop into debugger

## Coverage Reports

Coverage shows which code is tested:

```bash
# Generate HTML coverage report
docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh coverage"

# View report (copy from container)
docker compose cp backend:/app/ml_pipeline/htmlcov ./htmlcov
# Open htmlcov/index.html in browser
```

## Common Patterns

### Testing Error Conditions
```python
def test_raises_error_on_invalid_input():
    with pytest.raises(ValueError, match="Expected error message"):
        function_that_should_fail(invalid_input)
```

### Parameterized Tests (Multiple Inputs)
```python
@pytest.mark.parametrize("input_val,expected", [
    (1, "Forest"),
    (0, "Non-Forest"),
    (255, "Missing")
])
def test_pixel_classification(input_val, expected):
    result = classify_pixel(input_val)
    assert result == expected
```

### Testing with Temporary Files
```python
def test_file_processing(temp_test_features_dir):
    # temp_test_features_dir is automatically created and cleaned up
    csv_file = temp_test_features_dir / "test.csv"
    result = process_csv_file(csv_file)
    assert result is not None
```

## Dependencies for Poetry

The test dependencies are managed in `pyproject.toml`:

```toml
[tool.poetry.group.test.dependencies]
pytest = "^7.0.0"
pytest-cov = "^4.0.0"
pytest-mock = "^3.10.0"
pytest-asyncio = "^0.21.0"
pytest-xdist = "^3.0.0"
```

Install them with:
```bash
poetry install --with test
```

## Testing Different ML Pipeline Classes

### BenchmarkTester Tests
- **Unit Tests**: `tests/unit/test_benchmark_tester_unit.py`
- **Integration Tests**: `tests/integration/test_benchmark_tester_integration.py`
- **Coverage**: Initialization, polygon loading, pixel extraction, metrics calculation

### ModelPredictor Tests  
- **Unit Tests**: `tests/unit/test_predictor_unit.py`
- **Integration Tests**: `tests/integration/test_predictor_integration.py`
- **S3 Tests**: `tests/unit/test_s3_utils_unit.py`
- **Coverage**: Model loading, prediction workflows, file I/O, S3 upload, GDAL operations

### Running Tests by Component

```bash
# Test specific components
docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh quick -k benchmark"
docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh quick -k predictor"
docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh quick -k s3"

# Test by type
docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh unit"
docker compose exec backend bash -c "cd /app && /app/ml_pipeline/run_tests.sh integration"
```

## Key Testing Patterns Demonstrated

### 1. **Pickle-able Mock Objects**
For classes that load pickled models, create pickle-able mock classes:
```python
class MockModel:
    def __init__(self):
        self.consecutive_to_global = {0: 0, 1: 1}
    
    def predict(self, X):
        return np.array([i % 2 for i in range(len(X))])
```

### 2. **File System Testing**
Use temporary files and directories:
```python
@pytest.fixture
def temp_model_file():
    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
        pickle.dump(model_bundle, f)
        yield Path(f.name)
    # Automatic cleanup
```

### 3. **External Service Mocking**
Mock external dependencies like S3, GDAL, rasterio:
```python
with patch('ml_pipeline.predictor.rasterio.open') as mock_rasterio:
    mock_rasterio.return_value = mock_dataset
    # Test prediction logic without real raster files
```

### 4. **Parallel Processing Testing**
Mock parallel processing frameworks:
```python
with patch('ml_pipeline.predictor.Parallel') as mock_parallel:
    mock_parallel.return_value.return_value = expected_results
    # Test workflow without actual parallel execution
```

## Next Steps

1. **Expand Coverage**: Add tests for Trainer, Extractor, RunManager classes
2. **Performance Tests**: Add benchmarking for pixel extraction and model prediction
3. **End-to-End Tests**: Test complete workflows with real STAC data
4. **Property-Based Testing**: Use hypothesis for complex data validation
5. **Database Tests**: Add tests for database interactions and schema changes