from fastapi.testclient import TestClient
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from app.main import app  # Assuming this is how you import your FastAPI app

client = TestClient(app)

# hoodwinked_onboard_data
@pytest.mark.asyncio
async def test_hoodwinked_onboard_data_success():
    """
    Test the hoodwinked_onboard_data endpoint with successful scenario
    """
    # Prepare mock data for the service
    mock_report_data = {
        "data": {"trading_overview": {"total_trades": 10}},
        "message": "Report generation successful"
    }
    
    # Mock the service method
    with patch('app.services.report_services.generate_onboard_data', 
               return_value=mock_report_data):
        
        # Make the request
        response = client.get(
            "/api/analytics/generate-report/hoodwinked_onboard_data",
            params={
                "email": "test@example.com",
                "platform": "test_platform",
                "institution_id": "inst123"
            }
        )
        
        # Assertions
        assert response.status_code == 200
        assert response.json()['data']['trading_overview']['total_trades'] == 10
        assert response.json()['message'] == "Report generation successful"

@pytest.mark.asyncio
async def test_hoodwinked_onboard_data_missing_params():
    """
    Test the endpoint with missing required parameters
    """
    response = client.get(
        "/api/analytics/generate-report/hoodwinked_onboard_data",
        params={
            "email": "test@example.com"
            # Missing platform and institution_id
        }
    )
    
    # Expect a 422 Unprocessable Entity
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_hoodwinked_onboard_data_service_error():
    """
    Test the endpoint when the service raises an HTTPException
    """
    # Mock the service to raise an HTTPException
    with patch('app.services.report_services.generate_onboard_data', 
               side_effect=HTTPException(status_code=500, detail="Failed to fetch user data")):
        
        response = client.get(
            "/api/analytics/generate-report/hoodwinked_onboard_data",
            params={
                "email": "test@example.com",
                "platform": "test_platform",
                "institution_id": "inst123"
            }
        )
        
        # Assertions
        assert response.status_code == 500
        assert "Failed to fetch user data" in response.json()['detail']

# hoodwinked_plaid Route Tests
@pytest.mark.asyncio
async def test_hoodwinked_plaid_success():
    """
    Test the hoodwinked_plaid endpoint with successful scenario
    """
    # Prepare mock data for the service
    mock_report_data = {
        "data": {"report_link": "https://example.com/report.pdf"},
        "message": "Report generation successful"
    }
    
    # Mock the service method
    with patch('app.services.report_services.generate_report', 
               return_value=mock_report_data):
        # Make the request
        response = client.get(
            "/api/analytics/generate-report/hoodwinked_plaid",
            params={
                "email": "test@example.com",
                "platform": "test_platform",
                "institution_id": "inst123"
            }
        )
        
        # Assertions
        assert response.status_code == 200
        assert response.json()['data']['report_link'] == "https://example.com/report.pdf"
        assert response.json()['message'] == "Report generation successful"

@pytest.mark.asyncio
async def test_hoodwinked_plaid_missing_params():
    """
    Test the endpoint with missing required parameters
    """
    response = client.get(
        "/api/analytics/generate-report/hoodwinked_plaid",
        params={
            "email": "test@example.com"
            # Missing platform and institution_id
        }
    )
    # Expect a 422 Unprocessable Entity
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_hoodwinked_plaid_service_error():
    """
    Test the endpoint when the service raises an HTTPException
    """
    # Mock the service to raise an HTTPException
    with patch('app.services.report_services.generate_report', 
               side_effect=HTTPException(status_code=500, detail="Failed to generate report")):
        response = client.get(
            "/api/analytics/generate-report/hoodwinked_plaid",
            params={
                "email": "test@example.com",
                "platform": "test_platform",
                "institution_id": "inst123"
            }
        )
        # Assertions
        assert response.status_code == 500
        assert "Failed to generate report" in response.json()['detail']

# test for hoodwinked_pdf route tests
@pytest.mark.asyncio
async def test_hoodwinked_pdf_success():
    """
    Test the hoodwinked_pdf endpoint with successful scenario
    """
    # Prepare mock data for the service
    mock_report_data = {
        "data": {"report_link": "https://example.com/report.pdf"},
        "message": "Report generation successful"
    }
    
    # Mock the service method
    with patch('app.services.report_services.generate_pdf', 
               return_value=mock_report_data):
        # Make the request
        response = client.get(
            "/api/analytics/generate-report/hoodwinked_pdf",
            params={
                "file_id": "test_file_123",
                "platform": "test_platform",
                "site": "test_site",
                "siteType": "test_site_type"
            }
        )
        
        # Assertions
        assert response.status_code == 200
        assert response.json()['data']['report_link'] == "https://example.com/report.pdf"
        assert response.json()['message'] == "Report generation successful"

@pytest.mark.asyncio
async def test_hoodwinked_pdf_missing_required_params():
    """
    Test the endpoint with missing required parameters
    """
    response = client.get(
        "/api/analytics/generate-report/hoodwinked_pdf",
        params={
            # Missing file_id and platform
            "site": "test_site"
        }
    )
    # Expect a 422 Unprocessable Entity
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_hoodwinked_pdf_service_error():
    """
    Test the endpoint when the service raises an HTTPException
    """
    # Mock the service to raise an HTTPException
    with patch('app.services.report_services.generate_pdf', 
               side_effect=HTTPException(status_code=500, detail="Failed to generate PDF")):
        response = client.get(
            "/api/analytics/generate-report/hoodwinked_pdf",
            params={
                "file_id": "test_file_123",
                "platform": "test_platform",
                "site": "test_site",
                "siteType": "test_site_type"
            }
        )
        # Assertions
        assert response.status_code == 500
        assert "Failed to generate PDF" in response.json()['detail']