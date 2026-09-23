# recommendation_routes.py

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from ..services import recommendation_services
import logging


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/analytics",
    tags=["Recommendations"],
    responses={404: {"description": "Not found"}},
)

@router.get("/get_buy_recommendations")
async def buy_recommendations(
    ticker: str = Query(..., regex="^[A-Z]+$"),
    inventory: int = Query(..., gt=0),
    timeframe: int = Query(..., gt=0),
):
    """
    GET :- /api/analytics/get_buy_recommendations
    Endpoint to get buy recommendations.
    """
    try:
        logger.debug(f"Request - Ticker: {ticker}, Inventory: {inventory}, Timeframe: {timeframe}")
        response = recommendation_services.generate_buy_recommendations(
            ticker, inventory, timeframe
        )
        logger.debug(f"Response from generate_buy_recommendations: {response}")
        return JSONResponse(content=response, status_code=200)
    except HTTPException as e:
        logger.error(f"HTTPException in buy_recommendation route: {str(e.detail)}")
        return JSONResponse(content={"detail": e.detail}, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Unexpected error in buy_recommendations route: {e}", exc_info=True)
        return JSONResponse(
            content={"detail": "An unexpected error occurred in the route."},
            status_code=500,
        )


@router.get("/get_sell_recommendations")
async def sell_recommendations(
    ticker: str = Query(...),
    inventory: int = Query(...),
    timeframe: int = Query(...),
):
    """
    GET :- /api/analytics/get_sell_recommendations

    Endpoint to get sell recommendations.
    """
    try:
        logger.debug(f"Request - Ticker: {ticker}, Inventory: {inventory}, Timeframe: {timeframe}")
        response = recommendation_services.generate_sell_recommendations(
            ticker, inventory, timeframe
        )
        logger.debug(f"Response from the generate_sell_recommendations: {response}")
        return JSONResponse(content=response, status_code=200)
    except HTTPException as e:
        logger.error(f"HTTPException in sell_recommendations route: {str(e.detail)}")
        return JSONResponse(content={"detail": e.detail}, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Unexpected error in the sell_recommendation_route: {e}", exc_info=True)
        return JSONResponse(
            content={"detail": "An unexpected error occurred in the route."},
            status_code=500,
        )