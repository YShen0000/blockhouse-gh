import boto3
import argparse
import sagemaker
import tarfile
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Deploy the model to Amazon SageMaker for Asynchronous Inference")

# Add arguments here
parser.add_argument("--region", default="us-east-1", help="AWS Region")
parser.add_argument("--model_name", required=True, help="Sagemaker model name")
parser.add_argument("--account_id", required=True, help="Sagemaker account id")
parser.add_argument("--image_tag", default="deploy-test3", type=str, help="Sagemaker image tag")
parser.add_argument("--endpoint_name", type=str, required=True, help="Sagemaker endpoint name")
parser.add_argument("--endpoint_config_name", type=str, default="aws-endpoint-config", help="Sagemaker endpoint config name")
parser.add_argument("--version", required=True, type=int, help="production version")
parser.add_argument("--s3_bucket", type=str, default='sagemaker-tradingmodel-us-east-1', help="S3 bucket")
parser.add_argument("--model_files", type=str, nargs="+", default=["blockhouse_ml", "inference.py", "deployment_utils/requirements.txt"], help="model files")
parser.add_argument("--sagemaker_role", required=True, help="Sagemaker role")
parser.add_argument("--instance_type", default="ml.g4dn.xlarge", help="Sagemaker instance type")
parser.add_argument("--input_s3_location", required=True, help="S3 location for asynchronous input data")
parser.add_argument("--output_s3_location", required=True, help="S3 location for asynchronous output data")

def create_model_package(model_files, output_path):
    """
    Packages model files into a tar.gz file for deployment to SageMaker.
    """
    with tarfile.open(output_path, "w:gz") as tar:
        logger.info(f"Packaging files: {model_files}")
        for file in model_files:
            logger.info(f"Adding file: {os.path.basename(file)}")
            tar.add(file, arcname=os.path.join("code", os.path.basename(file)))

def create_sagemaker_model(model_name, role_arn, image_uri, model_data_url, bucket_name, version):
    """
    Creates a SageMaker model.
    """
    sagemaker_client = boto3.client('sagemaker')

    # Check if model already exists
    # try:
    #     sagemaker_client.describe_model(ModelName=model_name)
    #     logger.info(f"Model {model_name} already exists.")
    #     return None
    # except sagemaker_client.exceptions.ResourceNotFound:
    #     pass
    
    response = sagemaker_client.create_model(
        ModelName=model_name,
        PrimaryContainer={
            'Image': image_uri,
            'ModelDataUrl': model_data_url,
            'Environment': {
                'SAGEMAKER_PROGRAM': 'inference.py',
                'SAGEMAKER_CONTAINER_LOG_LEVEL': '10',
                'PYTHONUNBUFFERED': '1',
                'SAGEMAKER_TS_RESPONSE_TIMEOUT': '600',  # 10 minutes
                'SAGEMAKER_MODEL_SERVER_TIMEOUT': '600',  # 10 minutes
                'S3_BUCKET': bucket_name,
                'PROD_VERSION': str(version),
            }
        },
        ExecutionRoleArn=role_arn,
    )
    
    logger.info(f"Model {model_name} created successfully.")
    return response


    

def create_sagemaker_endpoint_async(model_name, endpoint_config_name, endpoint_name, role_arn, input_s3_location, output_s3_location, instance_type="ml.g4dn.xlarge"):
    """
    Creates a SageMaker endpoint for Asynchronous Inference.
    """
    sagemaker_client = boto3.client('sagemaker')

    # # Check if the endpoint already exists
    # try:
    #     response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
    #     logger.info(f"Endpoint {endpoint_name} already exists. Status: {response['EndpointStatus']}")
    #     return response
    # except sagemaker_client.exceptions.ResourceNotFound:
    #     pass

    # Create endpoint config
    sagemaker_client.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        AsyncInferenceConfig={
            'OutputConfig': {
                'S3OutputPath': output_s3_location,
            },
            'ClientConfig': {
                'MaxConcurrentInvocationsPerInstance': 1
            }
        },
        ProductionVariants=[
            {
                'ModelName': model_name,
                'VariantName': 'AllTraffic',
                'InitialInstanceCount': 1,
                'InstanceType': instance_type,
            }
        ]
    )

    # Create the endpoint
    sagemaker_client.create_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=endpoint_config_name
    )

    logger.info(f"Endpoint {endpoint_name} created. Waiting for it to be 'InService'...")
    
    # Wait for the endpoint to become 'InService'
    while True:
        response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
        status = response['EndpointStatus']
        logger.info(f"Current endpoint status: {status}")
        if status == 'InService':
            break
        elif status == 'Failed':
            raise Exception(f"Endpoint creation failed: {response['FailureReason']}")
        time.sleep(30)  # Wait before checking again

    return response
if __name__ == "__main__":
    
    args = parser.parse_args()
    
    model_name = args.model_name
    image_uri = f'{args.account_id}.dkr.ecr.{args.region}.amazonaws.com/blockhouse-ml:{args.image_tag}'

    # Package the model files into a tar.gz
    model_files = args.model_files
    output_path = "model-async-adjustedVWAP.tar.gz"
    create_model_package(model_files, output_path)

    # Upload the model to S3
    s3_client = boto3.client('s3')
    version = args.version
    bucket_name = args.s3_bucket
    s3_key = f'production/version_{version}/model-async-adjustedVWAP.tar.gz'
    logger.info(f"Uploading model package to s3://{bucket_name}/{s3_key}")
    s3_client.upload_file(output_path, bucket_name, s3_key)

    # Create the SageMaker model
    role_arn = args.sagemaker_role
    model_data_url = f's3://{bucket_name}/{s3_key}'

    try:
        response = create_sagemaker_model(model_name, role_arn, image_uri, model_data_url, bucket_name, version)
        if response:
            logger.info(f"Model created: {response['ModelArn']}")
    except Exception as e:
        logger.error(f"Failed to create model: {e}")
        raise

    # Add a delay or retry logic here if necessary
    time.sleep(10)  # Wait for a moment before describing the model

    # try:
    #     sagemaker_client.describe_model(ModelName=model_name)
    # except sagemaker_client.exceptions.ResourceNotFound:
    #     logger.error(f"Model {model_name} not found.")

    # Set up the SageMaker Asynchronous Endpoint
    endpoint_config_name = args.endpoint_config_name + f"-{version}"
    endpoint_name = args.endpoint_name
    input_s3_location = args.input_s3_location
    output_s3_location = args.output_s3_location

    response = create_sagemaker_endpoint_async(model_name, endpoint_config_name, endpoint_name, role_arn, input_s3_location, output_s3_location, instance_type=args.instance_type)
    logger.info(f"Async Endpoint created: {response['EndpointArn']}")










# if __name__ == "__main__":
    
#     args = parser.parse_args()
    
#     model_name = args.model_name
#     image_uri = f'{args.account_id}.dkr.ecr.{args.region}.amazonaws.com/blockhouse-ml:{args.image_tag}'

#     # Package the model files into a tar.gz
#     model_files = args.model_files
#     output_path = "model-async-adjustedVWAP.tar.gz"
#     create_model_package(model_files, output_path)

#     # Upload the model to S3
#     s3_client = boto3.client('s3')
#     version = args.version
#     bucket_name = args.s3_bucket
#     s3_key = f'production/version_{version}/model.tar.gz'
#     logger.info(f"Uploading model package to s3://{bucket_name}/{s3_key}")
#     s3_client.upload_file(output_path, bucket_name, s3_key)

#     # Create the SageMaker model
#     role_arn = args.sagemaker_role
#     model_data_url = f's3://{bucket_name}/{s3_key}'
#     response = create_sagemaker_model(model_name, role_arn, image_uri, model_data_url, bucket_name, version)
#     if response:
#         logger.info(f"Model created: {response['ModelArn']}")

#     # Set up the SageMaker Asynchronous Endpoint
#     endpoint_config_name = args.endpoint_config_name + f"-{version}"
#     endpoint_name = args.endpoint_name
#     input_s3_location = args.input_s3_location
#     output_s3_location = args.output_s3_location

#     response = create_sagemaker_endpoint_async(model_name, endpoint_config_name, endpoint_name, role_arn, input_s3_location, output_s3_location, instance_type=args.instance_type)
#     logger.info(f"Async Endpoint created: {response['EndpointArn']}")







































# import boto3
# import argparse
# import sagemaker
# import tarfile
# import os

# parser = argparse.ArgumentParser(description="Deploy the model to Amazon SageMaker for Asynchronous Inference")

# # Add arguments here
# parser.add_argument("--region", default="us-east-1", help="AWS Region")
# parser.add_argument("--model_name", required=True, help="Sagemaker model name")
# parser.add_argument("--account_id", required=True, help="Sagemaker account id")
# parser.add_argument("--image_tag", default="deploy-test3", type=str, help="Sagemaker image tag")
# parser.add_argument("--endpoint_name", type=str, required=True, help="Sagemaker endpoint name")
# parser.add_argument("--endpoint_config_name", type=str, default="aws-endpoint-config", help="Sagemaker endpoint config name")
# parser.add_argument("--version", required=True, type=int, help="production version")
# parser.add_argument("--s3_bucket", type=str, default='sagemaker-tradingmodel-us-east-1', help="S3 bucket")
# parser.add_argument("--model_files", type=str, nargs="+", default=["blockhouse_ml","inference.py", "deployment_utils/requirements.txt"], help="model files")
# parser.add_argument("--sagemaker_role", required=True, help="Sagemaker role")
# parser.add_argument("--instance_type", default="ml.g4dn.xlarge", help="Sagemaker instance type")
# parser.add_argument("--input_s3_location", required=True, help="S3 location for asynchronous input data")
# parser.add_argument("--output_s3_location", required=True, help="S3 location for asynchronous output data")

# def create_model_package(model_files, inference_script, output_path):
#     with tarfile.open(output_path, "w:gz") as tar:
#         print("Files to package: ", model_files)
#         for file in model_files:
#             print(os.path.basename(file))
#             tar.add(file, arcname=os.path.join("code", os.path.basename(file)))

# def create_sagemaker_model(model_name, role_arn, image_uri, model_data_url, bucket_name, version):
#     """
#     Creates a Sagemaker model.
#     """
#     sagemaker_client = boto3.client('sagemaker')
    
#     response = sagemaker_client.create_model(
#         ModelName=model_name,
#         PrimaryContainer={
#             'Image': image_uri,
#             'ModelDataUrl': model_data_url,
#             'Environment': {
#                 'SAGEMAKER_PROGRAM': 'inference.py',
#                 'SAGEMAKER_CONTAINER_LOG_LEVEL': '10',
#                 'PYTHONUNBUFFERED':'1',
#                 'SAGEMAKER_TS_RESPONSE_TIMEOUT': '600', # 10 minutes
#                 'SAGEMAKER_MODEL_SERVER_TIMEOUT': '600', # 10 minutes
#                 'S3_BUCKET': bucket_name,
#                 'PROD_VERSION': str(version),
#             }
#         },
#         ExecutionRoleArn=role_arn,
#     )
    
#     return response


# def create_sagemaker_endpoint_async(model_name, endpoint_config_name, endpoint_name, role_arn, input_s3_location, output_s3_location, instance_type="ml.g4dn.xlarge"):
#     """
#     Creates a Sagemaker endpoint for Asynchronous Inference.
#     """
#     sagemaker_client = boto3.client('sagemaker')

#     response = sagemaker_client.create_endpoint_config(
#         EndpointConfigName=endpoint_config_name,
#         AsyncInferenceConfig={
#             'OutputConfig': {
#                 'S3OutputPath': output_s3_location,
#             },
#             'ClientConfig': {
#                 'MaxConcurrentInvocationsPerInstance': 1
#             }
#         },
#         ProductionVariants=[
#             {
#                 'ModelName': model_name,
#                 'VariantName': 'AllTraffic',
#                 'InitialInstanceCount': 1,
#                 'InstanceType': instance_type,
#             }
#         ]
#     )

#     sagemaker_client.create_endpoint(
#         EndpointName=endpoint_name,
#         EndpointConfigName=endpoint_config_name
#     )

#     response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)

#     return response

# if __name__ == "__main__":
    
#     args = parser.parse_args()
    
#     model_name = args.model_name
#     image_uri = f'{args.account_id}.dkr.ecr.{args.region}.amazonaws.com/blockhouse-ml:{args.image_tag}'

#     # Package the model files into a tar.gz
#     model_files = args.model_files
#     inference_script = ""
#     output_path = "model.tar.gz"
#     create_model_package(model_files, inference_script, output_path)

#     # Upload the model to S3
#     s3_client = boto3.client('s3')
#     version = args.version
#     bucket_name = args.s3_bucket
#     s3_key = f'production/version_{version}/model.tar.gz'
#     s3_client.upload_file(output_path, bucket_name, s3_key)

#     # Create the SageMaker model
#     role_arn = args.sagemaker_role
#     model_data_url = f's3://{bucket_name}/{s3_key}'
#     response = create_sagemaker_model(model_name, role_arn, image_uri, model_data_url, bucket_name, version)
#     print("Model created: ", response['ModelArn'])

#     # Set up the SageMaker Asynchronous Endpoint
#     endpoint_config_name = args.endpoint_config_name + f"-{version}"
#     endpoint_name = args.endpoint_name
#     input_s3_location = args.input_s3_location
#     output_s3_location = args.output_s3_location

#     response = create_sagemaker_endpoint_async(model_name, endpoint_config_name, endpoint_name, role_arn, input_s3_location, output_s3_location, instance_type=args.instance_type)
#     print(f"Async Endpoint created: {response['EndpointArn']}")
