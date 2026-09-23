import pytest
from unittest.mock import patch
import pandas as pd
from fastapi import HTTPException
from io import StringIO
from app.services import s3_services
from app.config.s3 import s3

def test_upload_s3_success():
    """Test successful upload to S3"""
    mock_json_data = [
        {"id": 1, "name": "test1", "amount": 100},
        {"id": 2, "name": "test2", "amount": 200}
    ]
    
    with patch.object(s3, 'upload', return_value={"message": "File created and uploaded to S3 successfully."}):
        result = s3_services.upload_s3(
            json_data=mock_json_data,
            user_email="test@example.com",
            institution_id="test_institution"
        )
        
        assert result == {"message": "File created and uploaded to S3 successfully."}

def test_upload_s3_empty_data():
    """Test upload_s3 with empty data"""
    with pytest.raises(ValueError) as exc_info:
        s3_services.upload_s3(
            json_data=[],
            user_email="test@example.com",
            institution_id="test_institution"
        )
    assert str(exc_info.value) == "JSON data must be a non-empty list of dictionaries"

def test_upload_s3_invalid_data_type():
    """Test upload_s3 with invalid data type"""
    with pytest.raises(ValueError) as exc_info:
        s3_services.upload_s3(
            json_data="invalid_data",
            user_email="test@example.com",
            institution_id="test_institution"
        )
    assert str(exc_info.value) == "JSON data must be a non-empty list of dictionaries"

def test_upload_s3_inconsistent_keys():
    """Test upload_s3 with inconsistent dictionary keys"""
    mock_json_data = [
        {"id": 1, "name": "test1", "amount": 100},
        {"id": 2, "amount": 200}  # Missing 'name' key
    ]
    
    with pytest.raises(ValueError) as exc_info:
        s3_services.upload_s3(
            json_data=mock_json_data,
            user_email="test@example.com",
            institution_id="test_institution"
        )
    assert "All dictionaries must have the same keys" in str(exc_info.value)

def test_upload_s3_non_dict_items():
    """Test upload_s3 with non-dictionary items in the list"""
    mock_json_data = [
        {"id": 1, "name": "test1"},
        "not_a_dict"
    ]
    
    with pytest.raises(ValueError) as exc_info:
        s3_services.upload_s3(
            json_data=mock_json_data,
            user_email="test@example.com",
            institution_id="test_institution"
        )
    assert str(exc_info.value) == "All items in JSON data must be dictionaries"

def test_upload_s3_upload_error():
    """Test upload_s3 when S3 upload fails"""
    mock_json_data = [
        {"id": 1, "name": "test1", "amount": 100},
        {"id": 2, "name": "test2", "amount": 200}
    ]
    
    with patch.object(s3, 'upload', side_effect=HTTPException(status_code=500, detail="S3 upload failed")):
        with pytest.raises(HTTPException) as exc_info:
            s3_services.upload_s3(
                json_data=mock_json_data,
                user_email="test@example.com",
                institution_id="test_institution"
            )
        assert exc_info.value.status_code == 500
        assert "S3 upload failed" in str(exc_info.value.detail)
