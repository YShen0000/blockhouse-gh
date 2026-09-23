## Blockhouse SDK API Package

This is a Python SDK package that is used for various functionality from the Blockhouse API. The package is published on PyPI and can be installed using pip.

## Table of Contents

1. Features
2. Usage
3. Available Functions
4. License
5. Contributing
6. Support
7. Changelog

## Features

- Fetch trade data from the Blockhouse API and send them to our kafka topic.

## Usage

Get the API key from the Blockhouse API and install the package using pip:

```bash
pip install blockhouse
```

Using as a Python Library

```python
from blockhouse import Transfer

client = Transfer(api_key="your_api_key_here")

send = client.send_file(local_file_path="test123.txt", bucket_name="blockhouse-sdk")

print(send)

trades = client.trades_data()

print(trades)
```

Sending SOR data to the Blockhouse API

```python
from blockhouse import TradeClient

client = TradeClient("your_api_key_here")
res = client.send_trade(
    order_id="12345",
    symbol="AAPL",
    quantity=100,
    side="buy",
    price=150.50,
    order_type="limit",
)
print(res)
```

## Available Functions:

- TransferData: Fetch trade data from the Blockhouse API and send them to our kafka topic.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## Support

If you encounter any issues or have questions, feel free to open email us.

## Changelog

Version 1.0.9

- Added the ability to send files to the Blockhouse API.
- Added the ability to fetch trade data from the Blockhouse API.
- Added the ability to send SOR data to the Blockhouse API and create FIX messages.
