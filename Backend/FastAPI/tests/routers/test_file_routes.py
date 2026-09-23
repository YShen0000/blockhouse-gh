import pytest
from unittest.mock import patch, Mock
from fastapi import UploadFile, HTTPException
from app.routers.file_routes import upload_hoodwinked,delete_hoodwinked
from app.services import file_services

@pytest.mark.asyncio
async def test_upload_hoodwinked_success():
    """Test successful file upload through route"""
    # Create mock file with proper nested structure
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test1.csv"
    mock_file.file = Mock()  # Create the nested file attribute
    mock_file.file.read = Mock(return_value=b"test content 1")
    
    expected_response = {
        "responses": [{
            "file_name": "test1.csv",
            "file_url": "https://test-bucket.s3.region.amazonaws.com/test1.csv",
            "message": "File uploaded successfully"
        }],
        "user_email": "test@example.com",
        "platform": "test_platform"
    }
    
    with patch.object(file_services, 'upload_file', return_value=expected_response):
        result = await upload_hoodwinked(
            files=[mock_file],
            user_email="test@example.com",
            platform="test_platform"
        )
        assert result == expected_response

@pytest.mark.asyncio
async def test_upload_hoodwinked_value_error():
    """Test route handling of ValueError"""
    mock_file = Mock(spec=UploadFile)
    
    with (
        patch.object(file_services, 'upload_file', side_effect=ValueError("No files provided")),
        pytest.raises(HTTPException) as exc_info
    ):
        await upload_hoodwinked(
            files=[mock_file],
            user_email="test@example.com",
            platform="test_platform"
        )
    assert exc_info.value.status_code == 400
    assert "No files provided" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_upload_hoodwinked_unexpected_error():
    """Test route handling of unexpected errors"""
    mock_file = Mock(spec=UploadFile)
    
    with (
        patch.object(file_services, 'upload_file', side_effect=Exception("Unexpected error")),
        pytest.raises(HTTPException) as exc_info
    ):
        await upload_hoodwinked(
            files=[mock_file],
            user_email="test@example.com",
            platform="test_platform"
        )
    assert exc_info.value.status_code == 500
    assert "Internal server error" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_delete_hoodwinked_success():
    """Test successful file deletion through route"""
    with patch.object(file_services, 'delete_file', return_value={"message": "File deleted successfully"}):
        result = await delete_hoodwinked(file_path="test/path/file.csv")
        assert result == {"message": "File deleted successfully"}

@pytest.mark.asyncio
async def test_delete_hoodwinked_file_not_found():
    """Test route handling of FileNotFoundError"""
    with (
        patch.object(file_services, 'delete_file', side_effect=FileNotFoundError("No such file found")),
        pytest.raises(HTTPException) as exc_info
    ):
        await delete_hoodwinked(file_path="test/path/nonexistent.csv")
    assert exc_info.value.status_code == 404
    assert "No such file found" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_delete_hoodwinked_value_error():
    """Test route handling of ValueError"""
    with (
        patch.object(file_services, 'delete_file', side_effect=ValueError("Invalid file path")),
        pytest.raises(HTTPException) as exc_info
    ):
        await delete_hoodwinked(file_path="invalid/path")
    assert exc_info.value.status_code == 400
    assert "Invalid file path" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_delete_hoodwinked_unexpected_error():
    """Test route handling of unexpected errors"""
    with (
        patch.object(file_services, 'delete_file', side_effect=Exception("Unexpected error")),
        pytest.raises(HTTPException) as exc_info
    ):
        await delete_hoodwinked(file_path="test/path/file.csv")
    assert exc_info.value.status_code == 500
    assert "Internal server error" in str(exc_info.value.detail)
