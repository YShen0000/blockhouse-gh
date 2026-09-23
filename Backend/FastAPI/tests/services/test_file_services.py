import pytest
from unittest.mock import patch, Mock
from fastapi import UploadFile
from datetime import datetime
from app.services.file_services import upload_file,delete_file
from app.config.s3 import s3
from app.config.settings import settings

def create_mock_file(filename="test.csv", content=b"test content"):
    """Helper function to create properly structured mock file"""
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = filename
    mock_file.file = Mock()
    mock_file.file.read = Mock(return_value=content)
    return mock_file

def test_upload_file_single_file_success():
    """Test successful single file upload"""
    mock_file = create_mock_file()
    
    with patch.object(s3, 'upload', return_value={"message": "File created and uploaded to S3 successfully."}):
        result = upload_file(
            files=[mock_file],
            user_email="test@example.com",
            platform="test_platform"
        )
        
        assert "responses" in result
        assert len(result["responses"]) == 1
        assert result["responses"][0]["file_name"] == "test.csv"
        assert "file_url" in result["responses"][0]
        assert result["responses"][0]["message"] == "File uploaded successfully"
        assert result["user_email"] == "test@example.com"
        assert result["platform"] == "test_platform"

def test_upload_file_multiple_files_success():
    """Test successful multiple files upload"""
    mock_files = [
        create_mock_file("file1.csv", b"content1"),
        create_mock_file("file2.csv", b"content2")
    ]
    
    with patch.object(s3, 'upload', return_value={"message": "File created and uploaded to S3 successfully."}):
        result = upload_file(
            files=mock_files,
            user_email="test@example.com",
            platform="test_platform"
        )
        
        assert "responses" in result
        assert len(result["responses"]) == 2
        assert all(response["message"] == "File uploaded successfully" for response in result["responses"])
        assert result["responses"][0]["file_name"] == "file1.csv"
        assert result["responses"][1]["file_name"] == "file2.csv"
        assert result["user_email"] == "test@example.com"
        assert result["platform"] == "test_platform"

def test_upload_file_no_files():
    """Test upload with no files provided"""
    with pytest.raises(ValueError) as exc_info:
        upload_file(
            files=[],
            user_email="test@example.com",
            platform="test_platform"
        )
    assert str(exc_info.value) == "No files provided for upload."

def test_upload_file_none_files():
    """Test upload with None files"""
    with pytest.raises(ValueError) as exc_info:
        upload_file(
            files=None,
            user_email="test@example.com",
            platform="test_platform"
        )
    assert str(exc_info.value) == "No files provided for upload."

def test_upload_file_s3_upload_error():
    """Test handling of S3 upload error"""
    mock_file = create_mock_file()
    
    with (
        patch.object(s3, 'upload', side_effect=Exception("S3 upload failed")),
        pytest.raises(Exception) as exc_info
    ):
        upload_file(
            files=[mock_file],
            user_email="test@example.com",
            platform="test_platform"
        )
    assert "S3 upload failed" in str(exc_info.value)

def test_upload_file_file_read_error():
    """Test handling of file read error"""
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.csv"
    mock_file.file = Mock()
    mock_file.file.read = Mock(side_effect=Exception("File read error"))
    
    with pytest.raises(Exception) as exc_info:
        upload_file(
            files=[mock_file],
            user_email="test@example.com",
            platform="test_platform"
        )
    assert "File read error" in str(exc_info.value)

def test_delete_file_success():
    """Test successful file deletion"""
    mock_head_response = {"ContentLength": 100}
    
    with (
        patch.object(s3.s3, 'head_object', return_value=mock_head_response),
        patch.object(s3, 'delete', return_value={"message": "File deleted successfully"})
    ):
        result = delete_file("https://bucket.s3.region.amazonaws.com/test/path/file.csv")
        assert result == {"message": "File deleted successfully"}

def test_delete_file_not_found():
    """Test deletion of non-existent file"""
    client_error = s3.s3.exceptions.ClientError(
        error_response={"Error": {"Code": "404"}},
        operation_name="head_object"
    )
    
    with (
        patch.object(s3.s3, 'head_object', side_effect=client_error),
        pytest.raises(FileNotFoundError) as exc_info
    ):
        delete_file("https://bucket.s3.region.amazonaws.com/test/path/nonexistent.csv")
    assert "No such file found at path" in str(exc_info.value)

def test_delete_file_head_object_error():
    """Test error during file existence check"""
    client_error = s3.s3.exceptions.ClientError(
        error_response={"Error": {"Code": "403"}},
        operation_name="head_object"
    )
    
    with (
        patch.object(s3.s3, 'head_object', side_effect=client_error),
        pytest.raises(ValueError) as exc_info
    ):
        delete_file("https://bucket.s3.region.amazonaws.com/test/path/file.csv")
    assert "Error checking file existence" in str(exc_info.value)

def test_delete_file_deletion_error():
    """Test error during file deletion"""
    mock_head_response = {"ContentLength": 100}
    
    with (
        patch.object(s3.s3, 'head_object', return_value=mock_head_response),
        patch.object(s3, 'delete', side_effect=Exception("Deletion failed")),
        pytest.raises(ValueError) as exc_info
    ):
        delete_file("https://bucket.s3.region.amazonaws.com/test/path/file.csv")
    assert "Failed to delete file" in str(exc_info.value)
