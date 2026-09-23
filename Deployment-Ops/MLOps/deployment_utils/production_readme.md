# Production Deployment Steps:

The files and details are present [here](https://github.com/Blockhouse-Repo/Blockhouse-ML/tree/deployment-branch)

## Building and Running Docker 
* If you have new container with different dependencies then you need to build the docker image.
```
docker build -t blockhouse_ml:<image_tag> -f Dockerfile_Inference .
docker run -it blockhouse_ml:<image_tag> /bin/bash
```
* If want to use latest sagemaker pytorch image or different version of sagemaker image, then use this code:
```
from sagemaker import image_uris
image_uris.retrieve(framework='pytorch',region='us-east-1',version='2.2.0',py_version='py310',image_scope='inference', instance_type='ml.g4dn.xlarge')
```


## Adding to ECR
* After building the docker image, push it to ECR.
```
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account_id>.dkr.ecr.us-east-1.amazonaws.com
docker tag blockhouse_ml:v1 <account_id>.dkr.ecr.us-east-1.amazonaws.com/blockhouse-ml:<image_tag>
docker push <account_id>.dkr.ecr.us-east-1.amazonaws.com/blockhouse-ml:<image_tag>
```
* If want to use existing ECR image based on pytorch gpu for sagemaker, then use this id:
```
433046797920.dkr.ecr.us-east-1.amazonaws.com/blockhouse-ml:deploy-test3
```

## Add models to S3
* Current format to store models in S3 is:
    - S3 bucket: `sagemaker-tradingmodel-us-east-1`
    - S3 Key:
        - for sell:
            - macro_trader_models:
                - `production/version_{version}/equities/sell/macro_trader/`
            - micro_trader_models:
                - `production/version_{version}/equities/sell/micro_trader/`
        - for buy:
            - macro_trader_models:
                - `production/version_{version}/equities/buy/macro_trader/`
            - micro_trader_models:
                - `production/version_{version}/equities/buy/micro_trader/`
* Note: version number is the production version number of the model, current first deployment version is `1`.

## Deploy to SageMaker
* To deploy the model, run the following command.
```
python deployment.py \
  --region "us-east-1" \
  --model_name "my_model" \
  --endpoint_name "my_endpoint" \
  --version 1 \
  --sagemaker_role "my_sagemaker_role" \
  --account_id "my_account_id" \
  --image_tag "deploy-test3" \
  --model_files blockhouse_ml inference.py requirements.txt my_additional_file.py
```
### Additional Arguments
**Required Arguments**

* `--model_name`: Name of the Sagemaker model to deploy
* `--endpoint_name`: Name of the Sagemaker endpoint to create
* `--version`: Production version of the model, type `int`
* `--sagemaker_role`: IAM role for Sagemaker to use
* `--account_id`: AWS account ID 

**Optional Arguments**

* `--region`: AWS region to deploy to (default: `us-east-1`)
* `--image_tag`: Docker image tag to use (default: `latest`)
* `--endpoint_config_name`: Name of the Sagemaker endpoint configuration (default: `aws-endpoint-config`)
* `--s3_bucket`: S3 bucket to store model artifacts (default: `sagemaker-tradingmodel-us-east-1`)
* `--model_files`: List of files to include in the model package (default: `["blockhouse_ml", "inference.py", "deployment_utils/requirements.txt"]`)
* `--instance_type`: Sagemaker instance type (default: `ml.g4dn.xlarge`)

**Important Notes**

* `inference.py` should be there in as given by the user in argument `model_files`, or the deployment will fail.


## For Client Inference
* Details are present [here](https://www.notion.so/blockhouse1/How-to-Infer-on-client-side-9a00607c79ee4effa887b16a5cf4cb62?pvs=4)

* Example usage of the deployed model:
```
## Run inference from endpoint (AWS) real time inference, this code will be used by front end app

import json

endpoint_name = "my_endpoint" # where the model is deployed
model_name = "my_model" # deployed model name

# Prepare your JSON payload
payload = {
        "ticker": "AAPL",
        "action": "sell",
        "inventory": 5000,
        "timeframe": 390
    }
request_body = json.dumps(payload)
# Create a low-level client representing Amazon SageMaker Runtime
sagemaker_runtime = boto3.client(
    "sagemaker-runtime", region_name='us-east-1')
# Make the prediction

# Gets inference from the model hosted at the specified endpoint:
response = sagemaker_runtime.invoke_endpoint(
    EndpointName=endpoint_name, 
    Body=request_body, #bytes(request_body, 'utf-8')
    ContentType='application/json',
    InferenceComponentName=model_name+"-inference-component"
    )

# Decodes and prints the response body:
print(response['Body'].read().decode('utf-8'))
```