# app/controllers/report_routes.py

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from ..services import report_services
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/analytics/generate-report",
    tags=["Report"],
    responses={404: {"description": "Not found"}},
)


@router.get("/hoodwinked_onboard_data")
async def hoodwinked_onboard_data(
    email: str = Query(..., description="User's email address."),
    platform: str = Query(..., description="Platform name."),
    institution_id: str = Query(..., description="Institution ID."),
):
    """
    GET /api/analytics/generate-report/hoodwinked_onboard_data

    Endpoint to generate onboard data for a user.

    Args:
        email (str): User's email address.
        platform (str): Platform name.

    Returns:
        dict: Response message and onboard data.
    """
    try:
        return await report_services.generate_onboard_data(email, platform, institution_id)
    except HTTPException as e:
        logger.error(f"HTTPException in hoodwinked_onboard_data: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in hoodwinked_onboard_data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error occurred.")


@router.get("/hoodwinked_plaid")
async def hoodwinked_plaid(
    email: str = Query(..., description="User's email address."),
    platform: str = Query(..., description="Platform name."),
    institution_id: str = Query(..., description="Institution ID."),
):
    """
    GET /api/analytics/generate-report/hoodwinked_plaid

    Endpoint to generate a report for a user.

    Args:
        email (str): User's email address.
        platform (str): Platform name.

    Returns:
        str: Base64-encoded report.
    """
    try:
        return await report_services.generate_report(email, platform, institution_id)
    except HTTPException as e:
        logger.error(f"HTTPException in hoodwinked_plaid: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in hoodwinked_plaid: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error occurred.")


@router.get("/hoodwinked_pdf")
async def hoodwinked_pdf(
    file_id: str = Query(..., description="The unique identifier of the file."),
    platform: str = Query(..., description="Platform name."),
    site: Optional[str] = Query(None, description="Site parameter."),
    siteType: Optional[str] = Query(None, description="Site type parameter."),
):
    """
    GET /api/analytics/generate-report/hoodwinked_pdf

    Endpoint to generate a PDF for a user.

    Args:
        file_id (str): File ID.
        platform (str): Platform name.
        site (Optional[str]): Site parameter.
        siteType (Optional[str]): Site type parameter.

    Returns:
        str: Base64-encoded PDF report.
    """
    try:
        return await report_services.generate_pdf(file_id, platform, site, siteType)
    except HTTPException as e:
        logger.error(f"HTTPException in hoodwinked_pdf: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in hoodwinked_pdf: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error occurred.")