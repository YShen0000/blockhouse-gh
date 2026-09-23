import requests
import logging
from fastapi import HTTPException
from ..utils.sagemaker_utils import get_inference_response, initialize_sagemaker_client
from app.config.settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()

def validate_ticker(ticker: str) -> None:
    """
    Validate the ticker symbol using the Polygon API.
    Raises an HTTPException if the ticker is invalid.
    """
    polygon_url = f'https://api.polygon.io/v3/reference/tickers/{ticker}'
    params = {'apiKey': settings.POLYGON_API_KEY}

    logger.debug(f"Validating ticker with URL: {polygon_url} and params: {params}")
    try:
        response = requests.get(polygon_url, params=params)

        # Check if the ticker is valid (Polygon API returns 404 if not found)
        if response.status_code == 404:
            raise HTTPException(status_code=400, detail=f"Invalid ticker '{ticker}' provided.")

        # Raise HTTP errors for other status codes (non-2xx)
        response.raise_for_status()
    
    except requests.exceptions.RequestException as e:
        # Log the error and raise an HTTPException with a 500 status code for connection or other request-related issues
        logger.error(f"Error validating ticker '{ticker}': {e}")
        raise HTTPException(status_code=500, detail="Error validating ticker. Please try again later.")

def generate_buy_recommendations(ticker: str, inventory: int, timeframe: int) -> dict:
    """
    Service to generate buy recommendations.
    """
    logger.info(f"Generating buy recommendations for ticker '{ticker}'...")

    if inventory <= 0:
        raise HTTPException(status_code=400, detail="Invalid inventory")
    if timeframe <= 0:
        raise HTTPException(status_code=400, detail="Invalid timeframe")

    try:
        # Validate the ticker symbol
        validate_ticker(ticker)

        # Construct payload
        payload = {
            "ticker": ticker,
            "action": "buy",
            "inventory": inventory,
            "timeframe": timeframe
        }
        logger.debug(f"Payload for SageMaker: {payload}")

        # Initialize SageMaker client
        sagemaker_client = initialize_sagemaker_client()
        endpoint_name = 'MainPackage-website-endpoint'

        # Get inference response
        results = get_inference_response(sagemaker_client, endpoint_name, payload)
        logger.debug(f"SageMaker response: {results}")

        return {
            "ticker": ticker,
            "inventory": inventory,
            "timeframe": timeframe,
            "results": results,
            "message": "Buy recommendations generated successfully."
        }

    except HTTPException as e:
        # Catch HTTPException raised from validate_ticker and raise it again
        logger.error(f"HTTPException: {e.detail}")
        raise e  # Let the router handle it

    except Exception as e:
        # Catch unexpected errors
        logger.error(f"Unexpected error in buy recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate buy recommendations.")



def generate_sell_recommendations(ticker: str, inventory: int, timeframe: int) -> dict:
    """
    Service to generate sell recommendations.
    """
    logger.info(f"Generating sell recommendations for ticker '{ticker}'...")

    if inventory <= 0:
        raise HTTPException(status_code=400, detail="Invalid inventory")
    if timeframe <= 0:
        raise HTTPException(status_code=400, detail="Invalid timeframe")

    try:
        # Validate the ticker symbol
        validate_ticker(ticker)

        # Construct payload
        payload = {
            "ticker": ticker,
            "action": "sell",
            "inventory": inventory,
            "timeframe": timeframe
        }
        logger.debug(f"Payload for SageMaker: {payload}")

        # Initialize SageMaker client
        sagemaker_client = initialize_sagemaker_client()
        endpoint_name = 'MainPackage-website-endpoint'

        # Get inference response
        results = get_inference_response(sagemaker_client, endpoint_name, payload)
        logger.debug(f"SageMaker response: {results}")

        return {
            "ticker": ticker,
            "inventory": inventory,
            "timeframe": timeframe,
            "results": results,
            "message": "Sell recommendations generated successfully."
        }

    except HTTPException as e:
        # Catch HTTPException raised from validate_ticker and raise it again
        logger.error(f"HTTPException: {e.detail}")
        raise e  # Let the router handle it

    except Exception as e:
        # Catch unexpected errors
        logger.error(f"Unexpected error in sell recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate sell recommendations.")