import boto3
import argparse
import sagemaker
import tarfile
import os
from sagemaker.serverless import ServerlessInferenceConfig
from sagemaker.model import Model

# Argument parser
parser = argparse.ArgumentParser(description="Deploy the model to Amazon SageMaker")

# Add arguments here
parser.add_argument("--region", default="us-east-1", help="AWS Region")
parser.add_argument("--model_name", required=True, help="Sagemaker model name")
parser.add_argument("--account_id", required=True, help="Sagemaker account id")
parser.add_argument("--image_tag", default="deploy-test3", type=str, help="Sagemaker image tag")
parser.add_argument("--version", required=True, type=int, help="production version")
parser.add_argument("--s3_bucket", type=str, default='sagemaker-tradingmodel-us-east-1', help="S3 bucket")
parser.add_argument("--model_files", type=str, nargs="+", default=["blockhouse_ml", "inference.py", "deployment_utils/requirements.txt"], help="model files")
parser.add_argument("--sagemaker_role", required=True, help="Sagemaker role")

# New arguments for endpoint config and endpoint name
parser.add_argument("--endpoint_config_name", required=False, help="Sagemaker endpoint configuration name")
parser.add_argument("--endpoint_name", required=False, help="Sagemaker endpoint name")

os.environ['S3_BUCKET'] = 'sagemaker-tradingmodel-us-east-1'
os.environ['PROD_VERSION'] = '1'

def create_model_package(model_files, output_path):
    # Create tar.gz file with model files
    with tarfile.open(output_path, "w:gz") as tar:
        print(f"Packaging model files: {model_files}")
        for file in model_files:
            tar.add(file, arcname=os.path.join("code", os.path.basename(file)))
    print(f"Model package {output_path} created successfully.")

if __name__ == "__main__":
    
    args = parser.parse_args()
    
    print("Starting deployment process...")
    
    model_name = args.model_name
    image_uri = f'{args.account_id}.dkr.ecr.{args.region}.amazonaws.com/blockhouse-ml:{args.image_tag}'
    
    print(f"Using image URI: {image_uri}")
    
    # Package model files
    output_path = "model_serverless.tar.gz"
    create_model_package(args.model_files, output_path)

    # S3 client to upload the model package
    s3_client = boto3.client('s3')
    version = args.version
    bucket_name = args.s3_bucket
    s3_key = f'production/version_{version}/model_serverless.tar.gz'
    
    print(f"Uploading model package to S3 bucket: {bucket_name}, key: {s3_key}")
    
    # Upload model package to S3
    s3_client.upload_file(output_path, bucket_name, s3_key)
    
    print(f"Model package uploaded to S3: s3://{bucket_name}/{s3_key}")

    # Define model data URL for S3
    model_data_url = f's3://{bucket_name}/{s3_key}'
    
    print(f"Model data URL: {model_data_url}")

    # Create a serverless inference configuration
    print("Creating serverless inference configuration...")
    serverless_config = ServerlessInferenceConfig(
        memory_size_in_mb=6143,  # Adjust memory size
        max_concurrency=5        # Adjust concurrency
    )

    print("Serverless inference configuration created.")

    # Create SageMaker Model
    print(f"Creating SageMaker Model with model name: {model_name}")
    model = Model(
        model_data=model_data_url,
        role=args.sagemaker_role,
        image_uri=image_uri,
        entry_point='inference.py',
        source_dir='.',  # Adjust if necessary
        name=model_name
    )
    print("SageMaker Model created successfully.")

    # Use custom endpoint_name if provided, otherwise default
    endpoint_name = args.endpoint_name if args.endpoint_name else f"{model_name}-endpoint"
    
    print(f"Deploying the model as a serverless endpoint with endpoint name: {endpoint_name}")
    
    # Deploy the model as a serverless endpoint
    # predictor = model.deploy(
    #     serverless_inference_config=serverless_config,
    #     endpoint_name=endpoint_name
    #
    predictor = model.deploy(
                            instance_type="ml.m5.large",  # Choose an instance type that suits your needs
                            initial_instance_count=1,     # Number of instances to deploy
                            endpoint_name=endpoint_name
                            )

    print(f"Serverless endpoint created successfully: {predictor.endpoint_name}")




























# import boto3
# import argparse
# import sagemaker
# import tarfile
# import os
# from sagemaker.serverless import ServerlessInferenceConfig
# from sagemaker.model import Model

# # Argument parser
# parser = argparse.ArgumentParser(description="Deploy the model to Amazon SageMaker")

# # Add arguments here
# parser.add_argument("--region", default="us-east-1", help="AWS Region")
# parser.add_argument("--model_name", required=True, help="Sagemaker model name")
# parser.add_argument("--account_id", required=True, help="Sagemaker account id")
# parser.add_argument("--image_tag", default="deploy-test3", type=str, help="Sagemaker image tag")
# parser.add_argument("--version", required=True, type=int, help="production version")
# parser.add_argument("--s3_bucket", type=str, default='sagemaker-tradingmodel-us-east-1', help="S3 bucket")
# parser.add_argument("--model_files", type=str, nargs="+", default=["blockhouse_ml", "inference.py", "deployment_utils/requirements.txt"], help="model files")
# parser.add_argument("--sagemaker_role", required=True, help="Sagemaker role")

# # New arguments for endpoint config and endpoint name
# parser.add_argument("--endpoint_config_name", required=False, help="Sagemaker endpoint configuration name")
# parser.add_argument("--endpoint_name", required=False, help="Sagemaker endpoint name")

# os.environ['S3_BUCKET'] = 'sagemaker-tradingmodel-us-east-1'
# os.environ['PROD_VERSION'] = '1'

# def create_model_package(model_files, output_path):
#     # Create tar.gz file with model files
#     with tarfile.open(output_path, "w:gz") as tar:
#         print("Files to package: ", model_files)
#         for file in model_files:
#             tar.add(file, arcname=os.path.join("code", os.path.basename(file)))

# if __name__ == "__main__":
    
#     args = parser.parse_args()
    
#     model_name = args.model_name
#     image_uri = f'{args.account_id}.dkr.ecr.{args.region}.amazonaws.com/blockhouse-ml:{args.image_tag}'

#     # Package model files
#     output_path = "model.tar.gz"
#     create_model_package(args.model_files, output_path)

#     # S3 client to upload the model package
#     s3_client = boto3.client('s3')
#     version = args.version
#     bucket_name = args.s3_bucket
#     s3_key = f'production/version_{version}/model.tar.gz'
    
#     # Upload model package to S3
#     s3_client.upload_file(output_path, bucket_name, s3_key)

#     # Define model data URL for S3
#     model_data_url = f's3://{bucket_name}/{s3_key}'

#     # Create a serverless inference configuration
#     serverless_config = ServerlessInferenceConfig(
#         memory_size_in_mb=4096,  # Adjust memory size
#         max_concurrency=5        # Adjust concurrency
#     )

#     # Create SageMaker Model
#     model = Model(
#         model_data=model_data_url,
#         role=args.sagemaker_role,
#         image_uri=image_uri,
#         entry_point='inference.py',
#         source_dir='.',  # Adjust if necessary
#         name=model_name
#     )

#     # Use custom endpoint_name if provided, otherwise default
#     endpoint_name = args.endpoint_name if args.endpoint_name else f"{model_name}-endpoint"

#     # Deploy the model as a serverless endpoint
#     predictor = model.deploy(
#         serverless_inference_config=serverless_config,
#         endpoint_name=endpoint_name
#     )

#     print(f"Serverless endpoint created: {predictor.endpoint_name}")
