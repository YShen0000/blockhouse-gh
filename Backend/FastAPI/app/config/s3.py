import boto3
from fastapi import HTTPException

from .settings import settings


class S3:
    """
    A class to interact with AWS S3 for uploading, downloading, and deleting files.

    Attributes:
        access_key_id (str): AWS access key ID.
        secret_access_key (str): AWS secret access key.
        region (str): AWS region.
        bucket (str): S3 bucket name.
    """

    def __init__(self, access_key_id, secret_access_key, region, bucket):
        """
        Initializes the S3 client with the provided credentials and bucket information.

        Args:
            access_key_id (str): AWS access key ID.
            secret_access_key (str): AWS secret access key.
            region (str): AWS region.
            bucket (str): S3 bucket name.
        """
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self.bucket = bucket
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
        )

    def upload(self, filepath, data, content_type="octet-stream"):
        """
        Uploads a file to the specified S3 bucket.

        Args:
            filepath (str): The path where the file will be stored in the S3 bucket.
            data (bytes): The file data to be uploaded.

        Returns:
            dict: A dictionary containing a success message or an error message with details.
        """
        try:
            self.s3.put_object(Bucket=self.bucket, Key=filepath, Body=data, ContentType=content_type)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to S3. Details: {str(e)}",
            )

        return {
            "message": "File created and uploaded to S3 successfully.",
        }

    def download(self, filepath):
        """
        Downloads a file from the specified S3 bucket.

        Args:
            filepath (str): The path of the file to be downloaded from the S3 bucket.

        Returns:
            bytes: The file data if the download is successful.
            dict: A dictionary containing an error message with details if the download fails.
        """
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=filepath)
            return response["Body"].read()

        except Exception as e:
            raise HTTPException(
                status_code=404, detail=f"File not found. Details: {str(e)}"
            )

    def delete(self, filepath):
        """
        Deletes a file from the specified S3 bucket.

        Args:
            filepath (str): The path of the file to be deleted from the S3 bucket.

        Returns:
            dict: A dictionary containing a success message or an error message with details.
        """
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=filepath)
            return {
                "message": "File deleted from S3 successfully.",
            }
        except Exception as e:
            raise HTTPException(
                status_code=404, detail=f"File not found. Details: {str(e)}"
            )

    def list_objects(self, prefix):
        try:
            return self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        except Exception as e:
            raise HTTPException(
                status_code=404, detail=f"No files found for the given user"
            )

    def get_object(self, key):
        try:
            return self.s3.get_object(Bucket=self.bucket, Key=key)
        except Exception as e:
            raise HTTPException(
                status_code=404, detail=f"No files found for the given user"
            )

    def get_url(self, key):
        try:
            url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
            return url
        except Exception as e:
            raise HTTPException(
                status_code=404, detail=f"No files found for the given user"
            )


s3 = S3(
    access_key_id=settings.AWS_ACCESS_KEY_ID,
    secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region=settings.AWS_REGION,
    bucket=settings.AWS_STORAGE_BUCKET,
)
