from io import StringIO
import pandas as pd
from typing import Any, Dict, Optional
from fastapi import HTTPException, status

from ..config.s3 import s3
from ..config.database import db


def fetch_file_from_s3(
    file_id: str, site: Optional[str] = None, siteType: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch a specific file from S3 based on file_id, site, and siteType.

    Args:
        file_id (str): File identifier.
        site (Optional[str]): Site parameter.
        siteType (Optional[str]): Site type parameter.

    Returns:
        pd.DataFrame: The data fetched from S3.

    Raises:
        HTTPException: If no files found or data is empty.
    """
    try:
        # Construct the base S3 folder path based on the input parameters
        if site is None:
            s3_folder = f"hoodwinked/app/{file_id}"
        else:
            if siteType == "demo":
                s3_folder = f"Blockhouse/demo/{file_id}"
            else:
                s3_folder = f"Blockhouse/app/{file_id}"

        # Generate the full S3 file path
        s3_file_path = f"{s3_folder}/{file_id}.csv"

        # Fetch the file content from S3
        try:
            obj = s3.get_object(s3_file_path)
            file_content = obj["Body"].read().decode("utf-8")
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to fetch the file from S3. Details: {str(e)}",
            )

        # Convert the CSV content to a DataFrame
        df = pd.read_csv(StringIO(file_content))

        if df.empty:
            raise HTTPException(
                status_code=404, detail="No data found in the fetched file."
            )

        return df

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching the file. Details: {str(e)}",
        )


def db_fetch_data_from_s3(email: str, institution_id: str) -> pd.DataFrame:
    # Fetch data from S3
    filepath = f"hoodwinked/plaid/{email}/{institution_id}.csv"
    file_content = s3.download(filepath)

    # Read the CSV file into a DataFrame
    df = pd.read_csv(StringIO(file_content.decode("utf-8")))

    return df


def save_report_to_s3(user_email: str, institution_id: str, report_pdf: bytes) -> str:
    user_folder = f"hoodwinked/report_pdf/{user_email}"
    filename = f"report-{institution_id}.pdf"
    filepath = f"{user_folder}/{filename}"
    s3.upload(filepath, report_pdf, content_type="application/pdf")
    s3_url = s3.get_url(filepath)

    return s3_url


async def db_save_report(
    user_email: str,
    institution_id: str,
    report_link: Optional[str] = None,
    onboard_data: Optional[Dict[str, Any]] = None,
):
    """
    Save or update the user's report data in the database.

    Args:
        user_email (str): User's email address.
        report_link (Optional[str]): Report link to save.
        onboard_data (Optional[dict]): Onboarding data to save.

    Returns:
        None
    """
    update_data = {"institution_id": institution_id}

    # Append the report link if provided
    if report_link:
        update_data["report_link"] = report_link

    # Add onboarding data if provided
    if onboard_data:
        update_data["onboard_data"] = onboard_data

    if not update_data:
        return  # Nothing to update

    # Update or insert the document in the report collection
    await db.get_collection("Report").update_one(
        {
            "user_email": user_email,
            "institution_id": institution_id,
        },  # Filter by user_email and institution_id
        {"$set": update_data},  # Update or set fields
        upsert=True,  # Create a new document if none exists
    )


async def db_get_report(user_email: str, institution_id: str) -> Dict[str, Any]:
    """
    Retrieve the user's report data from the database.

    Args:
        user_email (str): User's email address.

    Returns:
        dict: The report data, including the report link and onboarding data.
    """
    report_data = await db.get_collection("Report").find_one(
        {"user_email": user_email, "institution_id": institution_id},
        {"_id": 0},  # Exclude the MongoDB ID field
    )

    if not report_data:
        return None

    # Ensure missing fields are handled gracefully
    return {
        "report_link": report_data.get("report_link"),
        "onboard_data": report_data.get("onboard_data"),
    }