import requests
from blockhouse.client.s3_connector import S3Connector


class Transfer:
    def __init__(self, api_key: str):
        """
        Initialize the Transfer class with an API key.

        Args:
            api_key (str): API key for authentication, used to connect to the Go API.
        """
        self.api_key = api_key
        self.api_url = "https://go-api.blockhouse.app"
        self.s3_connector = None

    def fetch_aws_credentials(self) -> dict:
        """
        Fetch AWS credentials from the Go API.

        Returns:
            dict: AWS credentials including access key, secret key, and region.
        """
        headers = {"x-api-key": self.api_key}
        response = requests.get(
            self.api_url + "/transfer-data/s3-credentials", headers=headers
        )
        response.raise_for_status()

        credentials_data = response.json().get("data")
        if not credentials_data:
            raise ValueError("Failed to retrieve AWS credentials.")

        return credentials_data

    def initialize_s3_connector(self):
        """
        Initialize the S3 connector with fetched AWS credentials.
        """
        credentials = self.fetch_aws_credentials()
        self.s3_connector = S3Connector(
            aws_access_key_id=credentials["aws_access_key_id"],
            aws_secret_access_key=credentials["aws_secret_access_key"],
            region_name=credentials["s3_region"],
        )

    def send_file(self, local_file_path: str, bucket_name: str) -> dict:
        """
        Upload a file to an S3 bucket.

        Args:
            local_file_path (str): Path to the local file.
            bucket_name (str): Name of the S3 bucket.

        Returns:
            dict: Response from the S3 file upload.
        """
        if not self.s3_connector:
            self.initialize_s3_connector()

        return self.s3_connector.upload_file(local_file_path, bucket_name)

    def trades_data(self) -> dict:
        """
        Calls the Go API to generate trades and transfer trading data to Kafka.

        Returns:
            dict: Response from the Go API.
        """
        headers = {"x-api-key": self.api_key}

        try:
            response = requests.get(
                self.api_url + "/transfer-data/trades", headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}


if __name__ == "__main__":
    client = Transfer(api_key="your_api_key_here")

    send = client.send_file(local_file_path="test123.txt", bucket_name="blockhouse-sdk")

    print(send)

    trades = client.trades_data()

    print(trades)
