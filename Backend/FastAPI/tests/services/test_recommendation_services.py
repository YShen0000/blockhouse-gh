import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
import requests

from app.services.recommendation_services import generate_buy_recommendations, validate_ticker, generate_sell_recommendations

def test_validate_ticker_success():
    """
    Test successful ticker validation
    """
    # Mock the requests.get to simulate a successful API response
    with patch('requests.get') as mock_get:
        # Create a mock response object with a 200 status code
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # This should not raise an exception
        try:
            validate_ticker('AAPL')
        except Exception as e:
            pytest.fail(f"validate_ticker raised an unexpected exception: {e}")

def test_validate_ticker_invalid_ticker():
    """
    Test ticker validation with an invalid ticker (404 response)
    """
    # Mock the requests.get to simulate a 404 response
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Expect an HTTPException with 400 status code
        with pytest.raises(HTTPException) as exc_info:
            validate_ticker('INVALIDTICKER')
        
        assert exc_info.value.status_code == 400
        assert "Invalid ticker" in str(exc_info.value.detail)

def test_validate_ticker_request_error():
    """
    Test ticker validation when there's a request error
    """
    # Mock the requests.get to raise a RequestException
    with patch('requests.get', side_effect=requests.exceptions.RequestException("Connection error")):
        # Expect an HTTPException with 500 status code
        with pytest.raises(HTTPException) as exc_info:
            validate_ticker('AAPL')
        
        assert exc_info.value.status_code == 500
        assert "Error validating ticker" in str(exc_info.value.detail)

def test_generate_buy_recommendations_success():
    """
    Test successful generation of buy recommendations
    """
    # Prepare mock data
    ticker = 'AAPL'
    inventory = 100
    timeframe = 30

    # Create mock returns for the dependencies
    mock_sagemaker_client = MagicMock()
    mock_inference_results = {"recommendation": "buy", "confidence": 0.85}

    # Patch the dependencies
    with (
        patch('requests.get') as mock_get,  # For ticker validation
        patch('app.services.recommendation_services.initialize_sagemaker_client', 
              return_value=mock_sagemaker_client) as mock_init_client,
        patch('app.services.recommendation_services.get_inference_response', 
              return_value=mock_inference_results) as mock_inference
    ):
        # Setup a successful validation response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the function
        result = generate_buy_recommendations(ticker, inventory, timeframe)

        # Assertions
        assert result['ticker'] == ticker
        assert result['inventory'] == inventory
        assert result['timeframe'] == timeframe
        assert result['results'] == mock_inference_results
        assert result['message'] == "Buy recommendations generated successfully."

        # Verify method calls
        mock_get.assert_called_once()  # Ticker validation called
        mock_init_client.assert_called_once()  # SageMaker client initialized
        mock_inference.assert_called_once_with(
            mock_sagemaker_client, 
            'MainPackage-website-endpoint', 
            {
                "ticker": ticker,
                "action": "buy",
                "inventory": inventory,
                "timeframe": timeframe
            }
        )

def test_generate_buy_recommendations_invalid_ticker():
    """
    Test buy recommendations with an invalid ticker
    """
    # Prepare mock data
    ticker = 'INVALIDTICKER'
    inventory = 100
    timeframe = 30

    # Patch the requests.get to simulate 404 response
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Expect an HTTPException
        with pytest.raises(HTTPException) as exc_info:
            generate_buy_recommendations(ticker, inventory, timeframe)
        
        assert exc_info.value.status_code == 400
        assert f"Invalid ticker '{ticker}'" in str(exc_info.value.detail)

def test_generate_buy_recommendations_sagemaker_error():
    """
    Test buy recommendations when SageMaker inference fails
    """
    # Prepare mock data
    ticker = 'AAPL'
    inventory = 100
    timeframe = 30

    # Create mock returns for the dependencies
    mock_sagemaker_client = MagicMock()

    # Patch the dependencies
    with (
        patch('requests.get') as mock_get,  # For ticker validation
        patch('app.services.recommendation_services.initialize_sagemaker_client', 
              return_value=mock_sagemaker_client),
        patch('app.services.recommendation_services.get_inference_response', 
              side_effect=Exception("SageMaker inference failed"))
    ):
        # Setup a successful validation response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Expect an HTTPException
        with pytest.raises(HTTPException) as exc_info:
            generate_buy_recommendations(ticker, inventory, timeframe)
        
        assert exc_info.value.status_code == 500
        assert "Failed to generate buy recommendations" in str(exc_info.value.detail)

def test_generate_sell_recommendations_success():
    """
    Test successful generation of sell recommendations
    """
    # Prepare mock data
    ticker = 'AAPL'
    inventory = 100
    timeframe = 30

    # Create mock returns for the dependencies
    mock_sagemaker_client = MagicMock()
    mock_inference_results = {"recommendation": "sell", "confidence": 0.85}

    # Patch the dependencies
    with (
        patch('requests.get') as mock_get,  # For ticker validation
        patch('app.services.recommendation_services.initialize_sagemaker_client', 
              return_value=mock_sagemaker_client) as mock_init_client,
        patch('app.services.recommendation_services.get_inference_response', 
              return_value=mock_inference_results) as mock_inference
    ):
        # Setup a successful validation response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the function
        result = generate_sell_recommendations(ticker, inventory, timeframe)

        # Assertions
        assert result['ticker'] == ticker
        assert result['inventory'] == inventory
        assert result['timeframe'] == timeframe
        assert result['results'] == mock_inference_results
        assert result['message'] == "Sell recommendations generated successfully."

        # Verify method calls
        mock_get.assert_called_once()  # Ticker validation called
        mock_init_client.assert_called_once()  # SageMaker client initialized
        mock_inference.assert_called_once_with(
            mock_sagemaker_client, 
            'MainPackage-website-endpoint', 
            {
                "ticker": ticker,
                "action": "sell",
                "inventory": inventory,
                "timeframe": timeframe
            }
        )

def test_generate_sell_recommendations_invalid_ticker():
    """
    Test sell recommendations with an invalid ticker
    """
    # Prepare mock data
    ticker = 'INVALIDTICKER'
    inventory = 100
    timeframe = 30

    # Patch the requests.get to simulate 404 response
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Expect an HTTPException
        with pytest.raises(HTTPException) as exc_info:
            generate_sell_recommendations(ticker, inventory, timeframe)
        
        assert exc_info.value.status_code == 400
        assert f"Invalid ticker '{ticker}'" in str(exc_info.value.detail)

def test_generate_sell_recommendations_sagemaker_error():
    """
    Test sell recommendations when SageMaker inference fails
    """
    # Prepare mock data
    ticker = 'AAPL'
    inventory = 100
    timeframe = 30

    # Create mock returns for the dependencies
    mock_sagemaker_client = MagicMock()

    # Patch the dependencies
    with (
        patch('requests.get') as mock_get,  # For ticker validation
        patch('app.services.recommendation_services.initialize_sagemaker_client', 
              return_value=mock_sagemaker_client),
        patch('app.services.recommendation_services.get_inference_response', 
              side_effect=Exception("SageMaker inference failed"))
    ):
        # Setup a successful validation response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Expect an HTTPException
        with pytest.raises(HTTPException) as exc_info:
            generate_sell_recommendations(ticker, inventory, timeframe)
        
        assert exc_info.value.status_code == 500
        assert "Failed to generate sell recommendations" in str(exc_info.value.detail)

def test_generate_sell_recommendations_invalid_inventory():
    """
    Test sell recommendations with invalid inventory
    """
    # Prepare mock data
    ticker = 'AAPL'
    inventory = -100  # Negative inventory
    timeframe = 30

    # Patch the requests.get to simulate a successful validation
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Expect an HTTPException
        with pytest.raises(HTTPException) as exc_info:
            generate_sell_recommendations(ticker, inventory, timeframe)
        
        assert exc_info.value.status_code == 400
        assert "Invalid inventory" in str(exc_info.value.detail)

def test_generate_sell_recommendations_invalid_timeframe():
    """
    Test sell recommendations with invalid timeframe
    """
    # Prepare mock data
    ticker = 'AAPL'
    inventory = 100
    timeframe = 0  # Invalid timeframe

    # Patch the requests.get to simulate a successful validation
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Expect an HTTPException
        with pytest.raises(HTTPException) as exc_info:
            generate_sell_recommendations(ticker, inventory, timeframe)
        
        assert exc_info.value.status_code == 400
        assert "Invalid timeframe" in str(exc_info.value.detail)