# app/services/report_services.py

import base64
import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from ..repositories import report_repositories
from ..utils import report_calculation
from ..utils import testreports

logger = logging.getLogger(__name__)


async def generate_onboard_data(email: str, platform: str, institution_id: str, is_new_data: bool = False) -> Dict[str, Any]:
    """
    Generate onboard data for a user with detailed logging for debugging.

    Args:
        email (str): User's email address.
        platform (str): Platform name.

    Returns:
        Dict[str, Any]: Response data with serialized report and message.

    Raises:
        HTTPException: On various failures during data fetching and processing.
    """
    onboard_data = await report_repositories.db_get_report(user_email=email, institution_id=institution_id)
    if onboard_data and onboard_data.get("onboard_data") and not is_new_data:
        return {
            "data": onboard_data["onboard_data"],
            "message": "Report generation successful",
        }

    try:
        logger.info(f"Starting report generation for email: {email}, platform: {platform}")

        # Fetch data from S3
        try:
            df = report_repositories.db_fetch_data_from_s3(email, institution_id)
            logger.info(f"Data fetched from S3 for email {email}: {df}")

            if df is None or df.empty:
                raise HTTPException(status_code=404, detail="No data found for the user.")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching data from S3: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to fetch user data.")

        # Calculate report
        try:
            logger.info(f"Starting report calculation for platform: {platform}, email: {email}")
            report_calculation_data = report_calculation.main(df, platform, email)
            logger.info(f"Report calculation successful: {report_calculation_data}")
        except Exception as e:
            logger.error(f"Error in report calculation: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to calculate report.")
        
        # Get Plaid AUM data
        try:
            logger.info("Calculating Plaid AUM data...")
            plaid_aum_data = report_calculation.get_plaid_aum(df)
            report_calculation_data["plaid_aum"] = plaid_aum_data
            logger.info(f"Plaid AUM data calculation successful: {plaid_aum_data}")
        except Exception as e:
            logger.error(f"Error in Plaid AUM calculation: {str(e)}", exc_info=True)
            report_calculation_data["plaid_aum"] = (
                None  # Set to None if calculation fails
            )
            raise HTTPException(status_code=500, detail="Failed to calculate Plaid AUM data.")

        # Convert to serializable format
        try:
            logger.info("Converting report data to serializable format...")
            serializable_data = report_calculation.convert_to_serializable(
                report_calculation_data
            )
            logger.info(f"Data serialization successful: {serializable_data}")
        except Exception as e:
            logger.error(f"Error in data serialization: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="Failed to serialize report data."
            )

        # Save report data to DB (Add exception handling here)
        try:
            await report_repositories.db_save_report(
                user_email=email, institution_id=institution_id, onboard_data=serializable_data
            )
            logger.info("Report data saved successfully.")
        except Exception as e:
            logger.error(f"Error saving report to DB: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to save report data.")

        return {"data": serializable_data, "message": "Report generation successful"}

    except HTTPException as http_exc:
        logger.error(f"HTTPException encountered: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in generate_onboard_data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error occurred.")


async def generate_report(email: str, platform: str, institution_id: str, is_new_data: bool = False) -> Dict[str, Any]:
    """
    Generate a Plaid report for a user.

    Args:
        email (str): User's email address.
        platform (str): Platform name.

    Returns:
        str: Base64-encoded report.

    Raises:
        HTTPException: On various failures during data fetching and processing.
    """
    report_link = await report_repositories.db_get_report(user_email=email, institution_id=institution_id)
    if report_link and report_link.get("report_link") and not is_new_data:
        return {
            "data": {"report_link": report_link["report_link"]},
            "message": "Report generation successful",
        }
    try:
        file_id = email  # Use email directly as file_id
        logger.info(
            f"Starting report generation for email: {email}, platform: {platform}"
        )

        # Fetch data from S3
        try:
            df = report_repositories.db_fetch_data_from_s3(email, institution_id)
            logger.info(f"Data fetched successfully from S3 for email {email}")

            if df is None or df.empty:
                raise HTTPException(status_code=404, detail="No data found for the user.")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching data from S3: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to fetch user data.")
        
        # Report Calculation
        try:
            logger.info("Starting report calculation...")
            report_calculation_data = report_calculation.main(df, platform, file_id)
            logger.info("Report calculation completed successfully.")
        except Exception as e:
            logger.error(f"Error in report calculation: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to calculate report.")
            
        # Generate Report
        try:
            logger.info("Generating the report...")
            document_base64 = testreports.generate_report(report_calculation_data)
            logger.info("Report generated successfully.")
        except HTTPException as e:
            # Let HTTPExceptions from generate_report propagate
            raise e
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate report.",
            )

        # Save to S3 bucket
        try:
            logger.info("Saving report to S3 bucket...")
            pdf_bytes = base64.b64decode(document_base64)
            s3_url = report_repositories.save_report_to_s3(email, institution_id, pdf_bytes)
            logger.info(f"Report saved to S3 successfully: {s3_url}")
        except Exception as e:
            logger.error(f"Error saving report to S3: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save report to S3.",
            )

        # Save the report link in the database
        try:
            logger.info("Saving report link to database...")
            await report_repositories.db_save_report(user_email=email, institution_id=institution_id, report_link=s3_url)
            logger.info("Report link saved to database successfully.")
        except Exception as e:
            logger.error(f"Error saving report link to database: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save report link to database.",
            )

        return {
            "data": {"report_link": s3_url},
            "message": "Report generation successful",
        }

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions to be handled by FastAPI
        logger.error(f"HTTPException encountered: {http_exc.detail}")
        raise http_exc

    except ZeroDivisionError as e:
        logger.error(f"ZeroDivisionError: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Division by zero occurred.",
        )

    except IndexError as e:
        logger.error(f"IndexError: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index out of bounds.",
        )

    except ValueError as e:
        logger.error(f"ValueError: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid value provided.",
        )

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in generate_report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred. Please check logs for details.",
        )


async def generate_pdf(
    file_id: str,
    platform: str,
    site: Optional[str] = None,
    siteType: Optional[str] = None,
) -> str:
    """
    Generate a PDF report for a specific file.

    Args:
        file_id (str): File ID.
        platform (str): Platform name.
        site (Optional[str]): Site parameter.
        siteType (Optional[str]): Site type parameter.

    Returns:
        str: Base64-encoded PDF report.

    Raises:
        HTTPException: On various failures during data fetching and processing.
    """
    try:
        logger.info(f"Checking if report exists for file_id: {file_id}")
        s3_url = await report_repositories.db_get_report_link(file_id)
        if s3_url:
            logger.info(f"Report already exists for file_id {file_id}: {s3_url}")
            return {
                "data": {"report_link": s3_url},
                "message": "Report generation successful",
            }
    except Exception as e:
        logger.error(f"Error checking existing report link: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check existing report link.",
        )
    

    try:
        # Fetch data from S3 using the file_id and other parameters
        try:
            logger.info(f"Fetching file from S3 for file_id: {file_id}")
            df = report_repositories.fetch_file_from_s3(file_id, site, siteType)
            logger.info(f"File fetched successfully from S3 for file_id {file_id}")

            if df is None or df.empty:
                logger.error("No data found in the fetched file.")
                raise HTTPException(
                    status_code=404, detail="No data found for the specified file."
                )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error fetching file from S3: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch data from S3.",
            )
        

        # Report Calculation
        try:
            logger.info("Starting report calculation...")
            report_calculation_data = report_calculation.main(df, platform, file_id)
            logger.info("Report calculation completed successfully.")
        except Exception as e:
            logger.error(f"Error in report calculation: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to calculate report.")

        # Generate PDF report
        try:
            logger.info("Generating PDF report...")
            document_base64 = testreports.generate_report(report_calculation_data)
            logger.info("PDF report generated successfully.")
        except HTTPException as e:
            # Let HTTPExceptions propagate naturally
            raise e
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate PDF report.",
            )

        # Save the PDF report to S3 bucket
        try:
            logger.info("Saving PDF report to S3 bucket...")
            s3_url = report_repositories.save_report_to_s3(file_id, document_base64)
            logger.info(f"PDF report saved to S3 successfully: {s3_url}")
        except Exception as e:
            logger.error(f"Error saving PDF report to S3: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save PDF report to S3.",
            )

        # Save the report link in the database
        try:
            logger.info("Saving PDF report link to database...")
            await report_repositories.db_save_report_link(file_id, s3_url)
            logger.info("PDF report link saved to database successfully.")
        except Exception as e:
            logger.error(
                f"Error saving PDF report link to database: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save PDF report link to database.",
            )

        return {
            "data": {"report_link": s3_url},
            "message": "Report generation successful",
        }

    except ValueError as e:
        logger.error(f"ValueError encountered: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions to be handled by FastAPI
        logger.error(f"HTTPException encountered: {http_exc.detail}")
        raise http_exc

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in generate_pdf: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred. Please check logs for details.",
        )