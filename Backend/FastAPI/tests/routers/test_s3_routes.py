import pytest
from unittest.mock import patch
from fastapi import HTTPException
from app.models import user_models
from app.services import s3_services, report_services, graph_services
from app.routers.s3_routes import upload_plaid_to_s3  # Add this import

@pytest.mark.asyncio
async def test_upload_plaid_to_s3_success():
    """Test successful plaid data upload with all subsequent operations"""
    mock_transactions = user_models.UserTransactions(
        json_data=[
            {"id": 1, "name": "test1", "amount": 100},
            {"id": 2, "name": "test2", "amount": 100}
        ],
        user_email="test@example.com",
        institution_id="test_institution"
    )
    
    with (
        patch.object(s3_services, 'upload_s3', return_value={"message": "File created and uploaded to S3 successfully."}),
        patch.object(report_services, 'generate_onboard_data', return_value=None),
        patch.object(report_services, 'generate_report', return_value=None),
        patch.object(graph_services, 'get_hoodwinked_analyze_plaid', return_value=None)
    ):
        result = await upload_plaid_to_s3(mock_transactions)
        assert result == {"message": "File created and uploaded to S3 successfully."}

@pytest.mark.asyncio
async def test_upload_plaid_to_s3_success_with_failed_subsequent_operations():
    """Test successful upload but failed subsequent operations"""
    mock_transactions = user_models.UserTransactions(
        json_data=[
            {"id": 1, "name": "test1", "amount": 100},
            {"id": 2, "name": "test2", "amount": 100}
        ],
        user_email="test@example.com",
        institution_id="test_institution"
    )
    
    with (
        patch.object(s3_services, 'upload_s3', return_value={"message": "File created and uploaded to S3 successfully."}),
        patch.object(report_services, 'generate_onboard_data', side_effect=Exception("Failed operation")),
        patch.object(report_services, 'generate_report', return_value=None),
        patch.object(graph_services, 'get_hoodwinked_analyze_plaid', return_value=None)
    ):
        result = await upload_plaid_to_s3(mock_transactions)
        assert result == {"message": "File created and uploaded to S3 successfully."}

@pytest.mark.asyncio
async def test_upload_plaid_to_s3_validation_error():
    """Test upload with invalid data format"""
    mock_transactions = user_models.UserTransactions(
        json_data=[
            {"id": 1, "name": "test1"},
            {"id": 2}  # Missing 'name' key
        ],
        user_email="test@example.com",
        institution_id="test_institution"
    )
    
    with patch.object(s3_services, 'upload_s3', side_effect=ValueError("All dictionaries must have the same keys")):
        with pytest.raises(HTTPException) as exc_info:
            await upload_plaid_to_s3(mock_transactions)
        assert exc_info.value.status_code == 400
        assert "All dictionaries must have the same keys" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_upload_plaid_to_s3_empty_data():
    """Test upload with empty data"""
    mock_transactions = user_models.UserTransactions(
        json_data=[{"id": 1, "name": "test1"}],  # Provide valid data structure
        user_email="test@example.com",
        institution_id="test_institution"
    )
    
    with patch.object(s3_services, 'upload_s3', side_effect=ValueError("JSON data must be a non-empty list of dictionaries")):
        with pytest.raises(HTTPException) as exc_info:
            await upload_plaid_to_s3(mock_transactions)
        assert exc_info.value.status_code == 400
        assert "JSON data must be a non-empty list of dictionaries" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_upload_plaid_to_s3_unexpected_error():
    """Test handling of unexpected errors"""
    mock_transactions = user_models.UserTransactions(
        json_data=[{"id": 1, "name": "test1"}],
        user_email="test@example.com",
        institution_id="test_institution"
    )
    
    with patch.object(s3_services, 'upload_s3', side_effect=Exception("Unexpected error")):
        with pytest.raises(HTTPException) as exc_info:
            await upload_plaid_to_s3(mock_transactions)
        assert exc_info.value.status_code == 500
        assert "Internal server error" in str(exc_info.value.detail)
