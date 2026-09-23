from datetime import datetime
from app.config.s3 import s3  # Using the pre-configured S3 class instance
from app.config.settings import settings


def upload_file(files: any, user_email: str, platform: str):
    """
    Upload files to S3.

    Args:
        files: Files to upload.
        user_email: User's email.
        platform: Platform name.

    Returns:
        dict: Information about uploaded files.
    """

    if not files:
        raise ValueError("No files provided for upload.")

    responses = []
    user_folder = f"uploads/{user_email}/{platform}"

    for file in files:
        # Generate unique file name using timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        s3_file_name = f"{user_folder}/{timestamp}_{file.filename}"

        # Upload file to S3 using the pre-configured s3 instance
        s3.upload(filepath=s3_file_name, data=file.file.read())
        
        # Construct file URL
        file_url = (
            f"https://{settings.AWS_STORAGE_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_file_name}"
        )

        responses.append(
            {
                "file_name": file.filename,
                "file_url": file_url,
                "message": "File uploaded successfully",
            }
        )

    return {"responses": responses, "user_email": user_email, "platform": platform}


def delete_file(file_path: str):
    """
    Delete a file from S3.

    Args:
        file_path: The full S3 file path.

    Returns:
        dict: Information about the deletion process.

    Raises:
        HTTPException: If the deletion fails or file does not exist.
    """
    # Filter the S3 key from the file path
    filtered_path = file_path.replace(
        f"https://{settings.AWS_STORAGE_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/", ""
    )

    try:
        # Check if the file exists in S3
        s3.s3.head_object(Bucket=settings.AWS_STORAGE_BUCKET, Key=filtered_path)
    except s3.s3.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "404":
            raise FileNotFoundError(f"No such file found at path: {file_path}")
        else:
            # Re-raise other exceptions
            raise ValueError(f"Error checking file existence: {str(e)}")

    # Delete the object from S3
    try:
        s3.delete(filepath=filtered_path)
    except Exception as e:
        raise ValueError(f"Failed to delete file. Details: {str(e)}")

    return {"message": "File deleted successfully"}
