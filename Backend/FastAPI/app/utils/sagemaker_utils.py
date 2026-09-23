# FastAPI/app/utils/sagemaker_utils.py
import boto3
import json
import requests
from fastapi import HTTPException
from app.config.settings import Settings
import logging

settings = Settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SageMaker client
def initialize_sagemaker_client():
    try:
        logger.info("Initializing SageMaker client...")
        sagemaker_runtime = boto3.client(
            "sagemaker-runtime",
            region_name=settings.AWS_REGION,  # Use settings from config.py
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        return sagemaker_runtime
    except Exception as e:
        logger.error(f"Error initializing SageMaker client: {str(e)}")
        raise

# Make prediction using SageMaker endpoint
def get_inference_response(sagemaker_client, endpoint_name, payload):
    try:
        request_body = json.dumps(payload)
        logger.info(f"Invoking SageMaker endpoint '{endpoint_name}' with payload: {request_body}")
        response = sagemaker_client.invoke_endpoint(
            EndpointName=endpoint_name,
            Body=request_body,
            ContentType='application/json',
        )
        response_body = response['Body'].read().decode('utf-8')
        response_json = json.loads(response_body)
        logger.info(f"Response from SageMaker: {response_json}")
        return response_json
    except Exception as e:
        logger.error(f"Error invoking SageMaker endpoint: {str(e)}")
        raise

# Example usage of the functions
if __name__ == "__main__":
    sagemaker_client = initialize_sagemaker_client()
    endpoint_name = 'MainPackage-website-endpoint'
    payload = {"key": "value"}
    response = get_inference_response(sagemaker_client, endpoint_name, payload)