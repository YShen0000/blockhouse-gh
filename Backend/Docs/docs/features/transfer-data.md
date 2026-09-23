---
sidebar_position: 1
---

# Transfer Data

This guide explains how to use the Blockhouse SDK to interact with the Blockhouse API and transfer trade data to a Kafka topic.

---

### Example Code

Below is an example of how to use the `TransferData` class provided by the SDK:

```python
from blockhouse import TransferData

# Initialize the SDK with your API key
td = TransferData(api_key="your-api-key")

# Fetch and transfer trade data
try:
    res = td.transfer_data()
    print("Data transfer successful:", res)
except Exception as e:
    print("An error occurred:", e)
```

---

### API Response Format

The `transfer_data` method returns a dictionary with the following structure:

```json
{
  "message": "Data successfully sent to Kafka topic",
  "symbol": "BTC-USD",
  "price": 50000.0,
  "volume": 0.1,
  "timestamp": 1631533200
}
```
