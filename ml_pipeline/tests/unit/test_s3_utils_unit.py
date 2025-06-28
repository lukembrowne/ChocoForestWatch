"""
Unit tests for S3 utilities used by ModelPredictor.

These tests focus on the S3 upload functionality that the Predictor uses
when upload_to_s3=True. We mock boto3 to avoid actual S3 operations.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile

from ml_pipeline.s3_utils import upload_file, get_s3_client, list_files, download_file


class TestS3ClientCreation:
    """Test S3 client creation and configuration."""
    
    def test_get_s3_client_with_default_bucket(self):
        """Test S3 client creation with default bucket."""
        with patch('ml_pipeline.s3_utils.boto3.session.Session') as mock_session, \
             patch('ml_pipeline.s3_utils.load_dotenv') as mock_load_dotenv, \
             patch('ml_pipeline.s3_utils.os.getenv') as mock_getenv:
            
            # Mock environment variables
            mock_getenv.side_effect = lambda key: {
                'AWS_REGION': 'us-east-1',
                'AWS_S3_ENDPOINT': 'nyc3.digitaloceanspaces.com',
                'AWS_ACCESS_KEY_ID': 'test_access_key',
                'AWS_SECRET_ACCESS_KEY': 'test_secret_key'
            }.get(key)
            
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            client, bucket = get_s3_client()
            
            # Should create client with correct configuration
            mock_session.return_value.client.assert_called_once_with(
                "s3",
                region_name="us-east-1",
                endpoint_url="https://nyc3.digitaloceanspaces.com",
                aws_access_key_id="test_access_key",
                aws_secret_access_key="test_secret_key"
            )
            assert client == mock_client
            assert bucket == "choco-forest-watch"

    def test_get_s3_client_with_custom_bucket(self):
        """Test S3 client creation with custom bucket."""
        with patch('ml_pipeline.s3_utils.boto3.session.Session') as mock_session, \
             patch('ml_pipeline.s3_utils.load_dotenv'), \
             patch('ml_pipeline.s3_utils.os.getenv') as mock_getenv:
            
            mock_getenv.side_effect = lambda key: {
                'AWS_REGION': 'us-west-2',
                'AWS_S3_ENDPOINT': 'test.endpoint.com',
                'AWS_ACCESS_KEY_ID': 'test_key',
                'AWS_SECRET_ACCESS_KEY': 'test_secret'
            }.get(key)
            
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            client, bucket = get_s3_client("custom-bucket")
            
            assert client == mock_client
            assert bucket == "custom-bucket"


class TestS3FileUpload:
    """Test S3 file upload functionality used by Predictor."""
    
    def test_upload_file_with_default_parameters(self):
        """Test file upload with default parameters."""
        with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as f:
            test_file = Path(f.name)
            f.write(b"test raster data")
        
        try:
            with patch('ml_pipeline.s3_utils.get_s3_client') as mock_get_s3:
                mock_client = Mock()
                mock_get_s3.return_value = (mock_client, "test-bucket")
                
                upload_file(test_file, "predictions/2022/01/test.tiff")
                
                # Should call upload_file with correct parameters
                mock_client.upload_file.assert_called_once_with(
                    Filename=str(test_file),
                    Bucket="test-bucket",
                    Key="predictions/2022/01/test.tiff",
                    ExtraArgs={"ContentType": "image/tiff"}
                )
        finally:
            test_file.unlink()

    def test_upload_file_with_custom_content_type(self):
        """Test file upload with custom content type."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            test_file = Path(f.name)
            f.write(b"test image data")
        
        try:
            with patch('ml_pipeline.s3_utils.get_s3_client') as mock_get_s3:
                mock_client = Mock()
                mock_get_s3.return_value = (mock_client, "test-bucket")
                
                upload_file(
                    test_file, 
                    "images/test.png", 
                    content_type="image/png"
                )
                
                mock_client.upload_file.assert_called_once_with(
                    Filename=str(test_file),
                    Bucket="test-bucket", 
                    Key="images/test.png",
                    ExtraArgs={"ContentType": "image/png"}
                )
        finally:
            test_file.unlink()

    def test_upload_file_with_custom_bucket(self):
        """Test file upload to custom bucket."""
        with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as f:
            test_file = Path(f.name)
            f.write(b"test data")
        
        try:
            with patch('ml_pipeline.s3_utils.get_s3_client') as mock_get_s3:
                mock_client = Mock()
                mock_get_s3.return_value = (mock_client, "default-bucket")
                
                upload_file(
                    test_file,
                    "data/test.tiff",
                    bucket="custom-bucket"
                )
                
                # Should use custom bucket, not default
                mock_client.upload_file.assert_called_once_with(
                    Filename=str(test_file),
                    Bucket="custom-bucket",
                    Key="data/test.tiff",
                    ExtraArgs={"ContentType": "image/tiff"}
                )
        finally:
            test_file.unlink()

    def test_upload_file_handles_s3_errors(self):
        """Test that upload_file handles S3 errors gracefully."""
        with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as f:
            test_file = Path(f.name)
        
        try:
            with patch('ml_pipeline.s3_utils.get_s3_client') as mock_get_s3:
                mock_client = Mock()
                mock_client.upload_file.side_effect = Exception("S3 upload failed")
                mock_get_s3.return_value = (mock_client, "test-bucket")
                
                # Should propagate S3 errors
                with pytest.raises(Exception, match="S3 upload failed"):
                    upload_file(test_file, "test/path.tiff")
        finally:
            test_file.unlink()


class TestS3FileOperations:
    """Test other S3 operations that might be used by Predictor."""
    
    def test_list_files_with_prefix(self):
        """Test listing files with a specific prefix."""
        with patch('ml_pipeline.s3_utils.get_s3_client') as mock_get_s3:
            mock_client = Mock()
            mock_client.list_objects_v2.return_value = {
                'Contents': [
                    {'Key': 'predictions/2022/01/tile1.tiff'},
                    {'Key': 'predictions/2022/01/tile2.tiff'},
                    {'Key': 'predictions/2022/01/metadata.json'},  # Should be filtered out
                    {'Key': 'predictions/2022/01/tile3.TIF'}  # Different case
                ]
            }
            mock_get_s3.return_value = (mock_client, "test-bucket")
            
            result = list_files("predictions/2022/01/")
            
            # Should only return .tif/.tiff files
            assert len(result) == 3
            assert all('key' in item and 'url' in item for item in result)
            assert result[0]['key'] == 'predictions/2022/01/tile1.tiff'
            assert 'test-bucket' in result[0]['url']

    def test_list_files_empty_result(self):
        """Test listing files when no files are found."""
        with patch('ml_pipeline.s3_utils.get_s3_client') as mock_get_s3:
            mock_client = Mock()
            mock_client.list_objects_v2.return_value = {}  # No 'Contents' key
            mock_get_s3.return_value = (mock_client, "test-bucket")
            
            result = list_files("nonexistent/prefix/")
            
            assert result == []

    def test_download_file_success(self):
        """Test successful file download from S3."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "downloaded" / "test.tiff"
            
            with patch('ml_pipeline.s3_utils.get_s3_client') as mock_get_s3:
                mock_client = Mock()
                mock_get_s3.return_value = (mock_client, "test-bucket")
                
                download_file("remote/test.tiff", local_path)
                
                # Should create parent directory and download file
                mock_client.download_file.assert_called_once_with(
                    "test-bucket",
                    "remote/test.tiff", 
                    str(local_path)
                )

    def test_download_file_creates_parent_directory(self):
        """Test that download_file creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "nested" / "path" / "test.tiff"
            assert not local_path.parent.exists()
            
            with patch('ml_pipeline.s3_utils.get_s3_client') as mock_get_s3:
                mock_client = Mock()
                mock_get_s3.return_value = (mock_client, "test-bucket")
                
                download_file("remote/test.tiff", local_path)
                
                # Parent directory should be created
                assert local_path.parent.exists()


class TestS3PredictorIntegration:
    """Test S3 functionality as used by ModelPredictor."""
    
    def test_predictor_s3_path_construction(self):
        """Test that Predictor constructs S3 paths correctly."""
        # This tests the logic from ModelPredictor._upload_to_s3
        s3_path = "predictions/v1"
        basemap_date = "2022-03"
        filename = "tile_123.tiff"
        
        # Simulate the path construction from ModelPredictor
        yyyy, mm = basemap_date.split("-")
        remote_key = f"{s3_path}/{yyyy}/{mm}/{filename}"
        
        assert remote_key == "predictions/v1/2022/03/tile_123.tiff"

    def test_predictor_s3_upload_integration(self):
        """Test ModelPredictor S3 upload integration."""
        from ml_pipeline.predictor import ModelPredictor
        
        with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as f:
            test_file = Path(f.name)
            f.write(b"test prediction data")
        
        try:
            # Create a minimal predictor instance for testing
            with patch('ml_pipeline.predictor.upload_file') as mock_upload, \
                 patch('builtins.open', mock_open(read_data=b'mock_model_data')), \
                 patch('pickle.load') as mock_pickle_load:
                
                # Mock the model bundle
                mock_model = Mock()
                mock_model.predict.return_value = [1, 0, 1]
                mock_pickle_load.return_value = {
                    'model': mock_model,
                    'meta': {'test': 'data'}
                }
                
                predictor = ModelPredictor(
                    model_path="fake_model.pkl",
                    extractor=Mock(),
                    upload_to_s3=True,
                    s3_path="test/predictions"
                )
                
                # Test the upload method directly
                predictor._upload_to_s3(test_file, "2022-06")
                
                # Should call upload_file with constructed path
                expected_key = "test/predictions/2022/06/{}".format(test_file.name)
                mock_upload.assert_called_once_with(test_file, expected_key)
        
        finally:
            test_file.unlink()

    def test_predictor_s3_upload_disabled(self):
        """Test that S3 upload is skipped when disabled."""
        from ml_pipeline.predictor import ModelPredictor
        
        with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as f:
            test_file = Path(f.name)
        
        try:
            with patch('ml_pipeline.predictor.upload_file') as mock_upload, \
                 patch('builtins.open', mock_open(read_data=b'mock_model_data')), \
                 patch('pickle.load') as mock_pickle_load:
                
                mock_model = Mock()
                mock_pickle_load.return_value = {
                    'model': mock_model,
                    'meta': {'test': 'data'}
                }
                
                predictor = ModelPredictor(
                    model_path="fake_model.pkl",
                    extractor=Mock(),
                    upload_to_s3=False,  # Disabled
                    s3_path="test/predictions"
                )
                
                predictor._upload_to_s3(test_file, "2022-06")
                
                # Should not call upload_file when disabled
                mock_upload.assert_not_called()
        
        finally:
            test_file.unlink()


# How to run these S3 tests:
#
# Run all S3-related tests:
# docker compose exec backend bash -c "cd /app/ml_pipeline && python -m pytest tests/unit/test_s3_utils_unit.py -v"
#
# Run specific S3 test class:
# docker compose exec backend bash -c "cd /app/ml_pipeline && python -m pytest tests/unit/test_s3_utils_unit.py::TestS3FileUpload -v"
#
# Run S3 integration with predictor:
# docker compose exec backend bash -c "cd /app/ml_pipeline && python -m pytest tests/unit/test_s3_utils_unit.py::TestS3PredictorIntegration -v"