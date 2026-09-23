import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException, status
import pandas as pd
from typing import Dict, Any
import base64


from app.services.report_services import generate_onboard_data,generate_report,generate_pdf
from app.repositories import report_repositories
from app.utils import report_calculation, testreports

# tests for generate_onboard_data service 
@pytest.mark.asyncio
async def test_generate_onboard_data_existing_report():
    """
    Test generate_onboard_data when a report already exists in the database
    """
    # Prepare mock data for an existing report
    mock_existing_report = {
        "onboard_data": {"existing": "data"},
        "user_email": "test@example.com",
        "institution_id": "inst123"
    }
    
    # Mock the database get_report method to return existing report
    with patch.object(report_repositories, 'db_get_report', 
                      return_value=mock_existing_report):
        
        # Call the service method
        result = await generate_onboard_data(
            email="test@example.com", 
            platform="test_platform", 
            institution_id="inst123"
        )
        
        # Assertions
        assert result == {
            "data": {"existing": "data"},
            "message": "Report generation successful"
        }

@pytest.mark.asyncio
async def test_generate_onboard_data_new_report_success():
    """
    Test generate_onboard_data for a successful new report generation
    """
    # Prepare mock DataFrame
    mock_df = pd.DataFrame({
        'amount': [100, 200], 
        'type': ['transfer', 'transfer']
    })
    
    # Mock report calculation data
    mock_report_data = {
        'trading_overview': {'total_trades': 10},
        'generate_buffer_slippage': {}
    }
    
    # Mock Plaid AUM data
    mock_plaid_aum = {
        'aum': 1000, 
        'total_trades': 5
    }
    
    # Prepare comprehensive mocks for each external dependency
    with (
        patch.object(report_repositories, 'db_get_report', 
                     return_value=None),
        patch.object(report_repositories, 'db_fetch_data_from_s3', 
                     return_value=mock_df),
        patch.object(report_repositories, 'db_save_report', 
                     return_value=None),
        patch.object(report_calculation, 'main', 
                     return_value=mock_report_data),
        patch.object(report_calculation, 'get_plaid_aum', 
                     return_value=mock_plaid_aum),
        patch.object(report_calculation, 'convert_to_serializable', 
                     side_effect=lambda x: x)
    ):
        # Call the service method
        result = await generate_onboard_data(
            email="test@example.com", 
            platform="test_platform", 
            institution_id="inst123"
        )
        
        # Comprehensive assertions
        assert result['message'] == "Report generation successful"
        assert 'data' in result
        assert result['data'].get('plaid_aum') == mock_plaid_aum

@pytest.mark.asyncio
async def test_generate_onboard_data_no_s3_data():
    """
    Test scenario when no data is found in S3
    """
    # Mock the S3 data fetch to return None/empty DataFrame
    with (
        patch.object(report_repositories, 'db_get_report', 
                     return_value=None),
        patch.object(report_repositories, 'db_fetch_data_from_s3', 
                     return_value=pd.DataFrame())
    ):
        # Expect an HTTPException with 404 status for no data
        with pytest.raises(HTTPException) as exc_info:
            await generate_onboard_data(
                email="test@example.com", 
                platform="test_platform", 
                institution_id="inst123"
            )
        
        assert exc_info.value.status_code == 404
        assert "No data found for the user" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_generate_onboard_data_s3_fetch_error():
    """
    Test scenario when there's an error fetching data from S3
    """
    # Mock the S3 data fetch to raise an exception
    with (
        patch.object(report_repositories, 'db_get_report', 
                     return_value=None),
        patch.object(report_repositories, 'db_fetch_data_from_s3', 
                     side_effect=Exception("S3 access error"))
    ):
        # Expect an HTTPException with 500 status for fetch error
        with pytest.raises(HTTPException) as exc_info:
            await generate_onboard_data(
                email="test@example.com", 
                platform="test_platform", 
                institution_id="inst123"
            )
        
        assert exc_info.value.status_code == 500
        assert "Failed to fetch user data" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_generate_onboard_data_calculation_error():
    """
    Test scenario when report calculation fails
    """
    # Prepare mock DataFrame
    mock_df = pd.DataFrame({
        'amount': [100], 
        'type': ['transfer']
    })
    
    with (
        patch.object(report_repositories, 'db_get_report', 
                     return_value=None),
        patch.object(report_repositories, 'db_fetch_data_from_s3', 
                     return_value=mock_df),
        patch.object(report_calculation, 'main', 
                     side_effect=Exception("Calculation failed"))
    ):
        # Expect an HTTPException with 500 status
        with pytest.raises(HTTPException) as exc_info:
            await generate_onboard_data(
                email="test@example.com", 
                platform="test_platform", 
                institution_id="inst123"
            )
        
        assert exc_info.value.status_code == 500
        assert "Failed to calculate report" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_generate_onboard_data_plaid_aum_error():
    """
    Test scenario when Plaid AUM calculation fails
    """
    # Prepare mock DataFrame
    mock_df = pd.DataFrame({
        'amount': [100], 
        'type': ['transfer']
    })
    
    # Mock report calculation data
    mock_report_data = {
        'trading_overview': {'total_trades': 10},
        'generate_buffer_slippage': {}
    }
    
    with (
        patch.object(report_repositories, 'db_get_report', 
                     return_value=None),
        patch.object(report_repositories, 'db_fetch_data_from_s3', 
                     return_value=mock_df),
        patch.object(report_calculation, 'main', 
                     return_value=mock_report_data),
        patch.object(report_calculation, 'get_plaid_aum', 
                     side_effect=Exception("Plaid AUM calculation failed"))
    ):
        # Expect an HTTPException with 500 status
        with pytest.raises(HTTPException) as exc_info:
            await generate_onboard_data(
                email="test@example.com", 
                platform="test_platform", 
                institution_id="inst123"
            )
        
        assert exc_info.value.status_code == 500
        assert "Failed to calculate Plaid AUM data" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_generate_onboard_data_serialization_error():
    """
    Test scenario when data serialization fails
    """
    # Prepare mock DataFrame
    mock_df = pd.DataFrame({
        'amount': [100], 
        'type': ['transfer']
    })
    
    # Mock report calculation data
    mock_report_data = {
        'trading_overview': {'total_trades': 10},
        'generate_buffer_slippage': {}
    }
    
    with (
        patch.object(report_repositories, 'db_get_report', 
                     return_value=None),
        patch.object(report_repositories, 'db_fetch_data_from_s3', 
                     return_value=mock_df),
        patch.object(report_calculation, 'main', 
                     return_value=mock_report_data),
        patch.object(report_calculation, 'get_plaid_aum', 
                     return_value={'aum': 1000, 'total_trades': 5}),
        patch.object(report_calculation, 'convert_to_serializable', 
                     side_effect=Exception("Serialization failed"))
    ):
        # Expect an HTTPException with 500 status
        with pytest.raises(HTTPException) as exc_info:
            await generate_onboard_data(
                email="test@example.com", 
                platform="test_platform", 
                institution_id="inst123"
            )
        
        assert exc_info.value.status_code == 500
        assert "Failed to serialize report data" in str(exc_info.value.detail)

# tests for generate_report service
@pytest.mark.asyncio
async def test_generate_report_existing_report():
    """
    Test generate_report when an existing report link is found
    """
    # Mock the existing report link
    mock_report_link = {"report_link": "https://existing-report.com/report.pdf"}
    
    with (
        patch.object(report_repositories, 'db_get_report', return_value=mock_report_link)
    ):
        result = await generate_report(
            email="test@example.com", 
            platform="test_platform", 
            institution_id="inst123"
        )
        
        assert result == {
            "data": {"report_link": "https://existing-report.com/report.pdf"},
            "message": "Report generation successful"
        }

@pytest.mark.asyncio
async def test_generate_report_new_data_success():
    """
    Test generate_report with successful report generation for new data
    """
    # Create a mock DataFrame
    mock_df = pd.DataFrame({'column': [1, 2, 3]})
    
    # Mock the various dependencies
    with (
        patch.object(report_repositories, 'db_get_report', return_value=None),
        patch.object(report_repositories, 'db_fetch_data_from_s3', return_value=mock_df),
        patch.object(report_calculation, 'main', return_value={'some': 'calculation_data'}),
        patch.object(testreports, 'generate_report', return_value=base64.b64encode(b'mock pdf content').decode()),
        patch.object(report_repositories, 'save_report_to_s3', return_value='https://s3.com/report.pdf'),
        patch.object(report_repositories, 'db_save_report', return_value=None)
    ):
        result = await generate_report(
            email="test@example.com", 
            platform="test_platform", 
            institution_id="inst123",
            is_new_data=True
        )
        
        assert result == {
            "data": {"report_link": "https://s3.com/report.pdf"},
            "message": "Report generation successful"
        }

@pytest.mark.asyncio
async def test_generate_report_no_s3_data():
    """
    Test generate_report when no data is found in S3
    """
    with (
        patch.object(report_repositories, 'db_get_report', return_value=None),
        patch.object(report_repositories, 'db_fetch_data_from_s3', return_value=pd.DataFrame())
    ):
        with pytest.raises(HTTPException) as exc_info:
            await generate_report(
                email="test@example.com", 
                platform="test_platform", 
                institution_id="inst123"
            )
        
        assert exc_info.value.status_code == 404
        assert "No data found for the user" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_generate_report_s3_fetch_error():
    """
    Test generate_report when there's an error fetching data from S3
    """
    with (
        patch.object(report_repositories, 'db_get_report', return_value=None),
        patch.object(report_repositories, 'db_fetch_data_from_s3', side_effect=Exception("S3 fetch error"))
    ):
        with pytest.raises(HTTPException) as exc_info:
            await generate_report(
                email="test@example.com", 
                platform="test_platform", 
                institution_id="inst123"
            )
        
        assert exc_info.value.status_code == 500
        assert "Failed to fetch user data" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_generate_report_calculation_error():
    """
    Test generate_report when there's an error in report calculation
    """
    mock_df = pd.DataFrame({'column': [1, 2, 3]})
    
    with (
        patch.object(report_repositories, 'db_get_report', return_value=None),
        patch.object(report_repositories, 'db_fetch_data_from_s3', return_value=mock_df),
        patch.object(report_calculation, 'main', side_effect=Exception("Calculation error"))
    ):
        with pytest.raises(HTTPException) as exc_info:
            await generate_report(
                email="test@example.com", 
                platform="test_platform", 
                institution_id="inst123"
            )
        
        assert exc_info.value.status_code == 500
        assert "Failed to calculate report" in str(exc_info.value.detail)

# Additional error scenario tests can be added here
@pytest.mark.asyncio
async def test_generate_report_report_generation_error():
    """
    Test generate_report when there's an error generating the report
    """
    mock_df = pd.DataFrame({'column': [1, 2, 3]})
    
    with (
        patch.object(report_repositories, 'db_get_report', return_value=None),
        patch.object(report_repositories, 'db_fetch_data_from_s3', return_value=mock_df),
        patch.object(report_calculation, 'main', return_value={'some': 'calculation_data'}),
        patch.object(testreports, 'generate_report', side_effect=Exception("Report generation error"))
    ):
        with pytest.raises(HTTPException) as exc_info:
            await generate_report(
                email="test@example.com", 
                platform="test_platform", 
                institution_id="inst123"
            )
        
        assert exc_info.value.status_code == 500
        assert "Failed to generate report" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_generate_report_s3_save_error():
    """
    Test generate_report when there's an error saving to S3
    """
    mock_df = pd.DataFrame({'column': [1, 2, 3]})
    
    with (
        patch.object(report_repositories, 'db_get_report', return_value=None),
        patch.object(report_repositories, 'db_fetch_data_from_s3', return_value=mock_df),
        patch.object(report_calculation, 'main', return_value={'some': 'calculation_data'}),
        patch.object(testreports, 'generate_report', return_value=base64.b64encode(b'mock pdf content').decode()),
        patch.object(report_repositories, 'save_report_to_s3', side_effect=Exception("S3 save error"))
    ):
        with pytest.raises(HTTPException) as exc_info:
            await generate_report(
                email="test@example.com", 
                platform="test_platform", 
                institution_id="inst123"
            )
        
        assert exc_info.value.status_code == 500
        assert "Failed to save report to S3" in str(exc_info.value.detail)

# tests for generate_pdf endpoint
@pytest.mark.asyncio
async def test_generate_pdf_new_report_success():
    """Test generate_pdf with successful report generation"""
    mock_df = pd.DataFrame({'column': [1, 2, 3]})
    
    with (
        patch.object(report_repositories, 'db_get_report_link', return_value=None),  # Add this to bypass initial check
        patch.object(report_repositories, 'fetch_file_from_s3', return_value=mock_df),
        patch.object(report_calculation, 'main', return_value={'some': 'calculation_data'}),
        patch.object(testreports, 'generate_report', return_value=base64.b64encode(b'mock pdf content').decode()),
        patch.object(report_repositories, 'save_report_to_s3', return_value='https://s3.com/report.pdf'),
        patch.object(report_repositories, 'db_save_report_link', return_value=None)  # Add this to bypass final db save
    ):
        result = await generate_pdf(
            file_id="test_file_id",
            platform="test_platform",
            site="test_site",
            siteType="test_siteType"
        )
        
        assert result == {
            "data": {"report_link": "https://s3.com/report.pdf"},
            "message": "Report generation successful"
        }

@pytest.mark.asyncio
async def test_generate_pdf_no_s3_data():
    """Test generate_pdf when no data is found in S3"""
    with (
        patch.object(report_repositories, 'db_get_report_link', return_value=None),  # Add this
        patch.object(report_repositories, 'fetch_file_from_s3', return_value=pd.DataFrame())
    ):
        with pytest.raises(HTTPException) as exc_info:
            await generate_pdf(
                file_id="test_file_id",
                platform="test_platform"
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "No data found for the specified file."

@pytest.mark.asyncio
async def test_generate_pdf_s3_fetch_error():
    """Test generate_pdf when there's an error fetching data from S3"""
    with (
        patch.object(report_repositories, 'db_get_report_link', return_value=None),  # Add this
        patch.object(report_repositories, 'fetch_file_from_s3', side_effect=Exception("S3 fetch error"))
    ):
        with pytest.raises(HTTPException) as exc_info:
            await generate_pdf(
                file_id="test_file_id",
                platform="test_platform"
            )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to fetch data from S3."

@pytest.mark.asyncio
async def test_generate_pdf_calculation_error():
    """Test generate_pdf when there's an error in report calculation"""
    mock_df = pd.DataFrame({'column': [1, 2, 3]})
    
    with (
        patch.object(report_repositories, 'db_get_report_link', return_value=None),  # Add this
        patch.object(report_repositories, 'fetch_file_from_s3', return_value=mock_df),
        patch.object(report_calculation, 'main', side_effect=Exception("Calculation error"))
    ):
        with pytest.raises(HTTPException) as exc_info:
            await generate_pdf(
                file_id="test_file_id",
                platform="test_platform"
            )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to calculate report."

@pytest.mark.asyncio
async def test_generate_pdf_report_generation_error():
    """Test generate_pdf when there's an error generating the PDF report"""
    mock_df = pd.DataFrame({'column': [1, 2, 3]})
    
    with (
        patch.object(report_repositories, 'db_get_report_link', return_value=None),  # Add this
        patch.object(report_repositories, 'fetch_file_from_s3', return_value=mock_df),
        patch.object(report_calculation, 'main', return_value={'some': 'calculation_data'}),
        patch.object(testreports, 'generate_report', side_effect=Exception("PDF generation error"))
    ):
        with pytest.raises(HTTPException) as exc_info:
            await generate_pdf(
                file_id="test_file_id",
                platform="test_platform"
            )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to generate PDF report."

@pytest.mark.asyncio
async def test_generate_pdf_s3_save_error():
    """Test generate_pdf when there's an error saving to S3"""
    mock_df = pd.DataFrame({'column': [1, 2, 3]})
    
    with (
        patch.object(report_repositories, 'db_get_report_link', return_value=None),  # Add this
        patch.object(report_repositories, 'fetch_file_from_s3', return_value=mock_df),
        patch.object(report_calculation, 'main', return_value={'some': 'calculation_data'}),
        patch.object(testreports, 'generate_report', return_value=base64.b64encode(b'mock pdf content').decode()),
        patch.object(report_repositories, 'save_report_to_s3', side_effect=Exception("S3 save error"))
    ):
        with pytest.raises(HTTPException) as exc_info:
            await generate_pdf(
                file_id="test_file_id",
                platform="test_platform"
            )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to save PDF report to S3."
