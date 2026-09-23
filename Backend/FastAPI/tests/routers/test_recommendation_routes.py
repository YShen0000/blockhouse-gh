import pytest
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from app.services import recommendation_services
from app.routers.recommendation_routes import buy_recommendations, sell_recommendations

@pytest.mark.asyncio
async def test_buy_recommendations_success():
    """Test successful buy recommendations"""
    mock_response = {
        "ticker": "AAPL",
        "inventory": 100,
        "timeframe": 30,
        "results": {"some": "prediction_data"},
        "message": "Buy recommendations generated successfully."
    }
    
    with patch.object(recommendation_services, 'generate_buy_recommendations', return_value=mock_response):
        response = await buy_recommendations(ticker="AAPL", inventory=100, timeframe=30)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert response.body.decode().find("Buy recommendations generated successfully") != -1

@pytest.mark.asyncio
async def test_buy_recommendations_invalid_ticker():
    """Test with invalid ticker"""
    with patch.object(
        recommendation_services, 
        'generate_buy_recommendations', 
        side_effect=HTTPException(status_code=400, detail="Invalid ticker symbol")
    ):
        response = await buy_recommendations(ticker="INVALID", inventory=100, timeframe=30)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        assert response.body.decode().find("Invalid ticker symbol") != -1

@pytest.mark.asyncio
async def test_buy_recommendations_unexpected_error():
    """Test handling of unexpected errors"""
    with patch.object(
        recommendation_services, 
        'generate_buy_recommendations', 
        side_effect=Exception("Unexpected error")
    ):
        response = await buy_recommendations(ticker="AAPL", inventory=100, timeframe=30)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        assert response.body.decode().find("An unexpected error occurred in the route") != -1

@pytest.mark.asyncio
async def test_sell_recommendations_success():
    """Test successful sell recommendations"""
    mock_response = {
        "ticker": "AAPL",
        "inventory": 100,
        "timeframe": 30,
        "results": {"body": [{"predictions": [0.8, 0.2]}]},
        "message": "Sell recommendations generated successfully."
    }
    
    with patch.object(recommendation_services, 'generate_sell_recommendations', return_value=mock_response):
        response = await sell_recommendations(
            ticker="AAPL",
            inventory=100,
            timeframe=30
        )
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert response.body.decode().find("Sell recommendations generated successfully") != -1

@pytest.mark.asyncio
async def test_sell_recommendations_invalid_ticker():
    """Test with invalid ticker"""
    with patch.object(
        recommendation_services, 
        'generate_sell_recommendations', 
        side_effect=HTTPException(status_code=400, detail="Invalid ticker symbol")
    ):
        response = await sell_recommendations(
            ticker="INVALID",
            inventory=100,
            timeframe=30
        )
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        assert response.body.decode().find("Invalid ticker symbol") != -1

@pytest.mark.asyncio
async def test_sell_recommendations_unexpected_error():
    """Test handling of unexpected errors"""
    with patch.object(
        recommendation_services, 
        'generate_sell_recommendations', 
        side_effect=Exception("Unexpected error")
    ):
        response = await sell_recommendations(
            ticker="AAPL",
            inventory=100,
            timeframe=30
        )
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        assert response.body.decode().find("An unexpected error occurred in the route") != -1
