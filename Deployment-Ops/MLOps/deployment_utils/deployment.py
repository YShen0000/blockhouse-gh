import boto3
import argparse
import sagemaker
import tarfile
import os

parser = argparse.ArgumentParser(description="Deploy the model to Amazon SageMaker")

# Add arguments here
parser.add_argument("--region", default="us-east-1", help="AWS Region")
parser.add_argument("--model_name", required=True, help="Sagemaker model name")
parser.add_argument("--account_id", required=True, help="Sagemaker account id")
parser.add_argument("--image_tag", default="deploy-test3", type=str, help="Sagemaker image tag")
parser.add_argument("--endpoint_name", type=str, required=True, help="Sagemaker endpoint name")
parser.add_argument("--endpoint_config_name", type=str, default="aws-endpoint-config", help="Sagemaker endpoint config name")
parser.add_argument("--version", required=True, type=int, help="production version")
parser.add_argument("--s3_bucket", type=str, default='sagemaker-tradingmodel-us-east-1', help="S3 bucket")
parser.add_argument("--model_files",type=str, nargs="+", default=["blockhouse_ml","inference.py", "deployment_utils/requirements.txt"], help="model files")
parser.add_argument("--sagemaker_role", required=True, help="Sagemaker role")
parser.add_argument("--instance_type", default="ml.g4dn.xlarge", help="Sagemaker instance type")

def create_model_package(model_files, inference_script, output_path):
    with tarfile.open(output_path, "w:gz") as tar:
        print("Files to package: ", model_files)
        for file in model_files:
            print(os.path.basename(file))
            tar.add(file, arcname=os.path.join("code", os.path.basename(file)))

def create_sagemaker_model(model_name, role_arn, image_uri, model_data_url, bucket_name, version):
    """
    Creates a Sagemaker model.

    Parameters
    ----------
    model_name : str
        The name of the Sagemaker model.
    role_arn : str
        The ARN of the IAM role to use for the Sagemaker model.
    image_uri : str
        The URI of the Docker image to use for the Sagemaker model.
    model_data_url : str
        The URL of the S3 bucket containing the model data.
    bucket_name : str
        The name of the S3 bucket containing the model data.
    version : int
        The production version of the model.

    Returns
    -------
    dict
        The response from the Sagemaker API.
    """
    sagemaker_client = boto3.client('sagemaker')
    
    response = sagemaker_client.create_model(
        ModelName=model_name,
        PrimaryContainer={
            'Image': image_uri,
            'ModelDataUrl': model_data_url,
            'Environment': {
                'SAGEMAKER_PROGRAM': 'inference.py',
                'SAGEMAKER_CONTAINER_LOG_LEVEL': '10',
                'PYTHONUNBUFFERED':'1',
                # refernce :https://github.com/aws/sagemaker-python-sdk/issues/2574#issuecomment-1854585409
                'SAGEMAKER_TS_RESPONSE_TIMEOUT': '600', # 10 minutes
                'SAGEMAKER_MODEL_SERVER_TIMEOUT': '600', # 10 minutes
                # 'SAGEMAKER_SUBMIT_DIRECTORY': '/opt/ml'
                'S3_BUCKET': bucket_name,
                'PROD_VERSION': str(version),
            }
            
        },
        ExecutionRoleArn=role_arn,
        # EnableNetworkIsolation=False,
        # Mode="SingleModel",
    )
    
    return response


def create_sagemaker_endpoint(model_name,  endpoint_config_name, endpoint_name, role_arn, instance_type="ml.g4dn.xlarge"):
    """
    Creates a Sagemaker endpoint.

    Parameters
    ----------
    model_name : str
        The name of the Sagemaker model.
    endpoint_config_name : str
        The name of the Sagemaker endpoint configuration.
    endpoint_name : str
        The name of the Sagemaker endpoint.
    role_arn : str
        The ARN of the IAM role to use for the Sagemaker endpoint.
    instance_type : str, optional
        The instance type of the Sagemaker endpoint. Defaults to "ml.g4dn.xlarge".

    Returns
    -------
    dict
        The response from the Sagemaker API.
    """
    sagemaker_client = boto3.client('sagemaker')
    
    variant_name = 'AllTraffic'

    response = sagemaker_client.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ExecutionRoleArn = role_arn,
        ProductionVariants=[
            {
                'InstanceType': instance_type,
                'InitialInstanceCount': 1,
                "ManagedInstanceScaling": { 
                    "MaxInstanceCount": 1,
                    "MinInstanceCount": 1,
                },
                "VariantName": variant_name,
            }
        ]
    )
    
    sagemaker_client.create_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=endpoint_config_name)
    
    response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
    
    sagemaker_client.create_inference_component(
        InferenceComponentName=model_name+"-inference-component",
        EndpointName=endpoint_name,
        VariantName=variant_name,
        Specification={
            "ModelName": model_name, 
            "ComputeResourceRequirements": { 
                "NumberOfAcceleratorDevicesRequired": 1,
                "NumberOfCpuCoresRequired": 1, 
                "MinMemoryRequiredInMb": 128,
            }
        },
        RuntimeConfig={"CopyCount": 1},
    )
    # response["EndpointStatus"]
    return response

if __name__ == "__main__":
    
    args = parser.parse_args()
    
    model_name = args.model_name
    # role_arn = 'arn:aws:iam:::role/your-sagemaker-role'
    image_uri = f'{args.account_id}.dkr.ecr.{args.region}.amazonaws.com/blockhouse-ml:{args.image_tag}'

    # Usage
    model_files = args.model_files
    inference_script = ""
    output_path = "model.tar.gz"
    create_model_package(model_files, inference_script, output_path)

    s3_client = boto3.client('s3')

    version = args.version
    bucket_name = args.s3_bucket
    s3_key = f'production/version_{version}/model.tar.gz'

    s3_client.upload_file(output_path, bucket_name, s3_key)
    
    # Usage
    model_name = args.model_name
    role_arn = args.sagemaker_role #'arn:aws:iam::your-account-id:role/your-sagemaker-role' #"arn:aws:iam::433046797920:role/service-role/AmazonSageMaker-ExecutionRole-20240227T184832"
    image_uri = f'{args.account_id}.dkr.ecr.{args.region}.amazonaws.com/blockhouse-ml:{args.image_tag}' #'433046797920.dkr.ecr.us-east-1.amazonaws.com/blockhouse-ml:deploy-test3'
    model_data_url = f's3://{bucket_name}/{s3_key}'

    response = create_sagemaker_model(model_name, role_arn, image_uri, model_data_url, bucket_name, version)
    print("model created: ", response['ModelArn'])

    endpoint_config_name = args.endpoint_config_name + f"-{version}"
    endpoint_name = args.endpoint_name

    response = create_sagemaker_endpoint(model_name, endpoint_config_name, endpoint_name, role_arn, instance_type=args.instance_type)
    print(f"Endpoint created: {response['EndpointArn']}")
    print(f"Inference component created: {model_name+'-inference-component'}")
