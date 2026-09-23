import json
import boto3


class SORConnector:
    def __init__(self, aws_access_key_id, aws_secret_access_key, region_name, endpoint):
        self.sor_client = boto3.client(
            "sagemaker-runtime",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )
        self.endpoint = endpoint

    def _invoke_sagemaker(self, payload: dict) -> dict:
        try:
            response = self.sor_client.invoke_endpoint(
                EndpointName=self.endpoint,
                Body=json.dumps(payload),
                ContentType="application/json",
            )
            response_body = response["Body"].read().decode("utf-8")
            return json.loads(response_body)
        except Exception as e:
            raise ValueError(f"Error invoking SageMaker endpoint: {str(e)}")
