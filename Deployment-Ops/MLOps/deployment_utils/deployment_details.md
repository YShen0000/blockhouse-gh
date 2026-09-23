# How Deployment Works Under the hood
The Deployment file is present [here](https://github.com/Blockhouse-Repo/Blockhouse-ML/blob/deployment-branch/deployment_utils/deployment.py)

This script deploys a machine learning model to Amazon SageMaker.

## Brief: 
It first parses command line arguments using the `argparse` library. Then it creates a model package by calling the `create_model_package` function with the `model_files`, `inference_script`, and `output_path` arguments. The package is then uploaded to an S3 bucket.

After that, it creates a SageMaker model using the `create_sagemaker_model` function. The function takes the model name, role ARN, image URI, model data URL, bucket name, and version as arguments. The function uses the `boto3` library to interact with the AWS services.

Finally, it creates a SageMaker endpoint using the `create_sagemaker_endpoint` function. The function takes the model name, endpoint configuration name, endpoint name, role ARN, and instance type as arguments.

The script prints the ARN of the created model and endpoint.

The script assumes that the necessary AWS credentials are already set up and that the S3 bucket and SageMaker resources exist.

## Details:

### Package the model files:
* Package the model files into a tar.gz file, using the `create_model_package`function, and it will save all the files in structure like this:
    - code/file1
    - code/file2
    - ...
* After packaging, upload the tar.gz file to an S3 bucket using the `upload_model_to_s3` function from boto3.

### Create a SageMaker model using the `create_sagemaker_model` function: 

This code creates a SageMaker model using the AWS SageMaker API. It takes in several parameters such as the model name, IAM role, ECR image URI (docker image in Amazon ECR), model data URL, S3 bucket name, and production version. The function returns the response from the SageMaker API.

The model is created with a primary container that uses the specified Docker image and model data URL. The environment variables for the container are also set, including the program to run (`inference.py`), log level, and timeouts. The execution role ARN is also specified.

* Additional details are present [here](docs/create_model.md)

### Create a SageMaker endpoint using the `create_sagemaker_endpoint` function:

This function creates a Sagemaker endpoint, which is a hosted model that can be used for real-time inference. It takes in the model name, endpoint configuration name, endpoint name, IAM role ARN, and instance type as parameters. The function creates an endpoint configuration, an endpoint, and an inference component, and returns the response from the Sagemaker API.

* Additional details are present [here](docs/create_endpoint.md)