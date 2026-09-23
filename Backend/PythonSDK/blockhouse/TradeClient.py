import requests
from blockhouse.client.sor_connector import SORConnector


class TradeClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://go-api.blockhouse.app"
        self.sor_connector = None
        self.trade = None

    def fetch_sor_credentials(self) -> dict:
        """
        Fetch SOR credentials from the Go API.

        Returns:
            dict: SOR credentials including access key, secret key, region, and endpoint.
        """
        headers = {"x-api-key": self.api_key}
        response = requests.get(self.api_url + "/fix/sor-credentials", headers=headers)
        response.raise_for_status()

        credentials_data = response.json().get("data")
        if not credentials_data:
            raise ValueError("Failed to retrieve SOR credentials.")

        return credentials_data

    def initialize_sor_connector(self):
        """
        Initialize the SOR connector with fetched SOR credentials.
        """
        credentials = self.fetch_sor_credentials()
        self.sor_connector = SORConnector(
            aws_access_key_id=credentials["aws_access_key_id"],
            aws_secret_access_key=credentials["aws_secret_access_key"],
            region_name=credentials["sor_region"],
            endpoint=credentials["sagemaker_endpoint"],
        )

    def send_trade(
        self,
        payload: dict,
    ) -> dict:
        """_summary_
        Send a trade to the Trade API.
        Args:
            order_id (str): Order ID
            symbol (str): Trading symbol
            quantity (float): Quantity of shares
            side (str): "buy" or "sell"
            price (float): Price per share
            order_type (str): "limit" or "market"

        Raises:
            ValueError: If side or order_type is invalid

        Returns:
            dict: Response from the Trade API
        """
        if not self.sor_connector:
            self.initialize_sor_connector()
        if payload["side"].lower() not in ["buy", "sell"]:
            raise ValueError("Side must be 'buy' or 'sell'.")

        headers = {"x-api-key": self.api_key}
        try:
            response = requests.post(
                self.api_url + "/fix/order", headers=headers, json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            return {"error": str(err)}


if __name__ == "__main__":
    client = TradeClient("API_KEY")
    res = client.send_trade(
        order_id="12345",
        symbol="AAPL",
        quantity=100,
        side="buy",
        price=150.50,
        order_type="limit",
    )
    print(res)
