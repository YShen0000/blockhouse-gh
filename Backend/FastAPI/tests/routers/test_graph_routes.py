import pytest
from unittest.mock import patch
from fastapi import HTTPException
from app.services import graph_services
from app.routers.graph_routes import hoodwinked_analyze, hoodwinked_analyze_plaid, hoodwinked_graph, hoodwinked_graph_plaid

@pytest.mark.asyncio
async def test_hoodwinked_analyze_success():
    """Test successful hoodwinked analysis"""
    mock_response = {
        "analysis_data": {"some": "analysis_result"},
        "message": "Analysis completed successfully"
    }
    
    with patch.object(graph_services, 'get_hoodwinked_analyze_plaid', return_value=mock_response):
        result = await hoodwinked_analyze(
            file_id="test_file_id",
            platform="test_platform",
            institution_id="test_institution"
        )
        assert result == mock_response

@pytest.mark.asyncio
async def test_hoodwinked_analyze_file_not_found():
    """Test file not found error"""
    with (
        patch.object(graph_services, 'get_hoodwinked_analyze_plaid', side_effect=FileNotFoundError("File not found")),
        pytest.raises(HTTPException) as exc_info
    ):
        await hoodwinked_analyze(
            file_id="nonexistent_file",
            platform="test_platform",
            institution_id="test_institution"
        )
        assert exc_info.value.status_code == 404
        assert "File not found" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_hoodwinked_analyze_value_error():
    """Test value error handling"""
    with (
        patch.object(graph_services, 'get_hoodwinked_analyze_plaid', side_effect=ValueError("Invalid parameter")),
        pytest.raises(HTTPException) as exc_info
    ):
        await hoodwinked_analyze(
            file_id="test_file_id",
            platform="invalid_platform",
            institution_id="test_institution"
        )
        assert exc_info.value.status_code == 400
        assert "Invalid parameter" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_hoodwinked_analyze_unexpected_error():
    """Test handling of unexpected errors"""
    with (
        patch.object(graph_services, 'get_hoodwinked_analyze_plaid', side_effect=Exception("Unexpected error")),
        pytest.raises(HTTPException) as exc_info
    ):
        await hoodwinked_analyze(
            file_id="test_file_id",
            platform="test_platform",
            institution_id="test_institution"
        )
        assert exc_info.value.status_code == 500
        assert "Internal Server Error" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_hoodwinked_analyze_plaid_success():
    """Test successful hoodwinked plaid analysis"""
    mock_response = {
        "analysis_data": {"some": "analysis_result"},
        "message": "Analysis completed successfully"
    }
    
    with patch.object(graph_services, 'get_hoodwinked_analyze_plaid', return_value=mock_response):
        result = await hoodwinked_analyze_plaid(
            email="test@example.com",
            platform="test_platform",
            institution_id="test_institution"
        )
        assert result == mock_response

@pytest.mark.asyncio
async def test_hoodwinked_analyze_plaid_file_not_found():
    """Test file not found error"""
    with patch.object(graph_services, 'get_hoodwinked_analyze_plaid', side_effect=FileNotFoundError("File not found")):
        with pytest.raises(HTTPException) as exc_info:
            await hoodwinked_analyze_plaid(
                email="test@example.com",
                platform="test_platform",
                institution_id="test_institution"
            )
        assert exc_info.value.status_code == 404
        assert "File not found" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_hoodwinked_analyze_plaid_value_error():
    """Test value error handling"""
    with patch.object(graph_services, 'get_hoodwinked_analyze_plaid', side_effect=ValueError("Invalid parameter")):
        with pytest.raises(HTTPException) as exc_info:
            await hoodwinked_analyze_plaid(
                email="test@example.com",
                platform="invalid_platform",
                institution_id="test_institution"
            )
        assert exc_info.value.status_code == 400
        assert "Invalid parameter" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_hoodwinked_analyze_plaid_unexpected_error():
    """Test handling of unexpected errors"""
    with patch.object(graph_services, 'get_hoodwinked_analyze_plaid', side_effect=Exception("Unexpected error")):
        with pytest.raises(HTTPException) as exc_info:
            await hoodwinked_analyze_plaid(
                email="test@example.com",
                platform="test_platform",
                institution_id="test_institution"
            )
        assert exc_info.value.status_code == 500
        assert "Internal Server Error" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_hoodwinked_graph_success():
    """Test successful graph generation"""
    mock_response = {
        "graph_data": {"some": "graph_data"},
        "message": "Graph generated successfully"
    }
    
    with patch.object(graph_services, 'get_hoodwinked_graph_plaid', return_value=mock_response):
        result = await hoodwinked_graph(
            platform="test_platform",
            institution_id="test_institution",
            chart_type="test_chart",
            email="test@example.com",
            stock="all_trades",
            benchmark="all_trades",
            trade_option="All Trades",
            start_date=None,
            end_date=None
        )
        assert result == mock_response

@pytest.mark.asyncio
async def test_hoodwinked_graph_file_not_found():
    """Test file not found error"""
    with patch.object(
        graph_services, 
        'get_hoodwinked_graph_plaid', 
        side_effect=FileNotFoundError("File not found")
    ):
        with pytest.raises(HTTPException) as exc_info:
            await hoodwinked_graph(
                platform="test_platform",
                institution_id="test_institution",
                chart_type="test_chart",
                email="test@example.com",
                stock="all_trades",
                benchmark="all_trades",
                trade_option="All Trades",
                start_date=None,
                end_date=None
            )
        assert exc_info.value.status_code == 404
        assert "File not found" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_hoodwinked_graph_value_error():
    """Test value error handling"""
    with patch.object(
        graph_services, 
        'get_hoodwinked_graph_plaid', 
        side_effect=ValueError("Invalid parameters")
    ):
        with pytest.raises(HTTPException) as exc_info:
            await hoodwinked_graph(
                platform="invalid_platform",
                institution_id="test_institution",
                chart_type="invalid_chart",
                email="test@example.com",
                stock="all_trades",
                benchmark="all_trades",
                trade_option="All Trades",
                start_date=None,
                end_date=None
            )
        assert exc_info.value.status_code == 400
        assert "Invalid parameters" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_hoodwinked_graph_unexpected_error():
    """Test handling of unexpected errors"""
    with patch.object(
        graph_services, 
        'get_hoodwinked_graph_plaid', 
        side_effect=Exception("Unexpected error")
    ):
        with pytest.raises(HTTPException) as exc_info:
            await hoodwinked_graph(
                platform="test_platform",
                institution_id="test_institution",
                chart_type="test_chart",
                email="test@example.com",
                stock="all_trades",
                benchmark="all_trades",
                trade_option="All Trades",
                start_date=None,
                end_date=None
            )
        assert exc_info.value.status_code == 500
        assert "Internal Server Error" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_hoodwinked_graph_plaid_success():
    """Test successful plaid graph generation"""
    mock_response = {
        "graph_data": {"some": "visualization_data"},
        "message": "Graph generated successfully"
    }
    
    with patch.object(graph_services, 'get_hoodwinked_graph_plaid', return_value=mock_response):
        result = await hoodwinked_graph_plaid(
            platform="test_platform",
            institution_id="test_institution",
            chart_type="test_chart",
            email="test@example.com",
            stock="all_trades",
            benchmark="all_trades",
            trade_option="All Trades",
            start_date=None,
            end_date=None
        )
        assert result == mock_response

@pytest.mark.asyncio
async def test_hoodwinked_graph_plaid_file_not_found():
    """Test file not found error handling"""
    with patch.object(
        graph_services, 
        'get_hoodwinked_graph_plaid', 
        side_effect=FileNotFoundError("Data not found")
    ):
        with pytest.raises(HTTPException) as exc_info:
            await hoodwinked_graph_plaid(
                platform="test_platform",
                institution_id="test_institution",
                chart_type="test_chart",
                email="test@example.com",
                stock="all_trades",
                benchmark="all_trades",
                trade_option="All Trades",
                start_date=None,
                end_date=None
            )
        assert exc_info.value.status_code == 404
        assert "Data not found" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_hoodwinked_graph_plaid_value_error():
    """Test value error handling"""
    with patch.object(
        graph_services, 
        'get_hoodwinked_graph_plaid', 
        side_effect=ValueError("Invalid parameters")
    ):
        with pytest.raises(HTTPException) as exc_info:
            await hoodwinked_graph_plaid(
                platform="invalid_platform",
                institution_id="test_institution",
                chart_type="invalid_chart",
                email="test@example.com",
                stock="all_trades",
                benchmark="all_trades",
                trade_option="All Trades",
                start_date=None,
                end_date=None
            )
        assert exc_info.value.status_code == 400
        assert "Invalid parameters" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_hoodwinked_graph_plaid_unexpected_error():
    """Test handling of unexpected errors"""
    with patch.object(
        graph_services, 
        'get_hoodwinked_graph_plaid', 
        side_effect=Exception("Unexpected error")
    ):
        with pytest.raises(HTTPException) as exc_info:
            await hoodwinked_graph_plaid(
                platform="test_platform",
                institution_id="test_institution",
                chart_type="test_chart",
                email="test@example.com",
                stock="all_trades",
                benchmark="all_trades",
                trade_option="All Trades",
                start_date=None,
                end_date=None
            )
        assert exc_info.value.status_code == 500
        assert "Internal Server Error" in str(exc_info.value.detail)