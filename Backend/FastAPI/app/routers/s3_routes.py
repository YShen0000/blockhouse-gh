from fastapi import APIRouter, HTTPException
from ..models import user_models
from ..services import s3_services, report_services, graph_services
import logging


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/analytics",
    tags=["S3"],
    responses={404: {"description": "Not found"}},
)


@router.post("/upload_plaid_to_s3")
async def upload_plaid_to_s3(user_transactions: user_models.UserTransactions):
    """
    POST :- /api/analytics/upload_plaid_to_s3

    Endpoint to upload user transactions to S3.

    Request Body:
        user_transactions (UserTransactions): User transactions data.

    Returns:
        dict: Response message and uploaded data.

    Raises:
        HTTPException: 
            - 400: If JSON data is invalid or malformed
            - 500: If any operation fails
    """
    try:
        # First attempt the S3 upload which includes data validation
        upload_result = s3_services.upload_s3(
            user_transactions.json_data, 
            user_transactions.user_email,
            user_transactions.institution_id,
        )

        # Only proceed with subsequent operations if upload succeeds
        try:
            await report_services.generate_onboard_data(
                email=user_transactions.user_email, 
                platform="Plaid",
                institution_id=user_transactions.institution_id,
                is_new_data=True,
            )

            await report_services.generate_report(
                email=user_transactions.user_email, 
                platform="Plaid",
                institution_id=user_transactions.institution_id,
                is_new_data=True,
            )

            await graph_services.get_hoodwinked_analyze_plaid(
                email=user_transactions.user_email, 
                platform="Plaid",
                institution_id=user_transactions.institution_id,
                is_new_data=True,
            )
        except Exception as e:
            # Log but don't fail the request if subsequent operations fail
            logger.error(f"Error in subsequent operations: {str(e)}", exc_info=True)

        return upload_result

    except ValueError as e:
        # Handle validation errors from the modified service
        raise HTTPException(
            status_code=400,
            detail=str(e)  # Use the exact error message from service validation
        )
    except Exception as e:
        logger.error(f"Unexpected error in upload_plaid_to_s3: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Please try again later."
        )
