import csv
from datetime import datetime
from io import StringIO
from ..config.s3 import s3


def upload_s3(json_data: dict, user_email: str, institution_id: str):
    """
    Uploads transaction data to S3 as a CSV.

    Args:
        json_data (dict): JSON data to upload.
        user_email (str): User's email.
        institution_id (str): Institution ID.

    Raises:
        ValueError: If JSON data is invalid or empty.
        ValueError: If JSON data format is inconsistent.
        HTTPException: If S3 upload fails.
    """
    # Validate input type and emptiness
    if not isinstance(json_data, list) or not json_data:
        raise ValueError("JSON data must be a non-empty list of dictionaries")

    # Validate all items are dictionaries and have the same keys
    if not all(isinstance(item, dict) for item in json_data):
        raise ValueError("All items in JSON data must be dictionaries")
    
    expected_keys = set(json_data[0].keys())
    if not all(set(item.keys()) == expected_keys for item in json_data):
        raise ValueError("All dictionaries must have the same keys")

    output = StringIO()
    csv_writer = csv.writer(output)
    csv_writer.writerow(json_data[0].keys())
    for row in json_data:
        csv_writer.writerow(row.values())

    # Upload the file to S3
    user_folder = f"hoodwinked/plaid/{user_email}"
    filepath = f"{user_folder}/{institution_id}.csv"

    return s3.upload(filepath, output.getvalue())
