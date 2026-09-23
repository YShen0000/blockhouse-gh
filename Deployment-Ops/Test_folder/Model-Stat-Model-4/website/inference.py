import logging
import os
import sys
import json
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
import time
from pandas.tseries.holiday import USFederalHolidayCalendar
from Adjusted_VWAP.adjusted_VWAP import Model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

def model_fn(model_dir):
    """Load both sell and buy models (macro and micro) when the SageMaker endpoint is initialized."""
    logger.info("Initializing model")
    start_t = time.perf_counter()
    model = Model()
    logger.info(f"Model initialized in {time.perf_counter() - start_t} seconds!!!")
    return model

# Input deserialization function
def input_fn(request_body, content_type='application/json'):
    """Deserialize the request body into a Python dictionary."""
    if content_type == 'application/json':
        logger.info("Deserializing the input data.")
        input_data = json.loads(request_body)
        logger.info(f"Input data: {input_data}")
        return input_data
    else:
        raise ValueError(f"Unsupported content type: {content_type}")

# Prediction function
def predict_fn(input_data, model):
    """Run the inference logic."""
    ticker = input_data.get('ticker')
    action = input_data.get('action', 'buy').lower()
    inventory = input_data.get('inventory', 10000)
    timeframe = input_data.get('timeframe', 390)  # Default to 390 if not provided

    if action not in ['buy', 'sell']:
        raise ValueError("Invalid action. Must be 'buy' or 'sell'.")

    logger.info(f"Running {action} inference for ticker: {ticker}")

    # Run the model inference
    result = model.infer_model(
        ticker=ticker,
        side=action,
        timeframe=timeframe,
        inventory=inventory,
    )

    print(f'Result: {result}')

    # Convert to structured format
    formatted_result = format_result(result)
    logger.info(f"Inference result: {formatted_result}")
    return formatted_result

# Output serialization function
def output_fn(prediction, content_type='application/json'):
    """Serialize the output into JSON format."""
    return json.dumps({"body": prediction}, indent=4)


def format_result(result):
    """Format the model's output to match the specified JSON structure."""
    formatted_result = []

    # Check if result is a DataFrame
    if isinstance(result, pd.DataFrame):
        for index, row in result.iterrows():
            # Replace `limit_price` with `price` if `limit_price` is null (NaN)
            limit_price = row["limit_price"] if pd.notnull(row["limit_price"]) else row["price"]
            
            formatted_result.append({
                "step": int(index),
                "timestamp": convert_to_serializable(row["timestamp"]),
                "order_type": row["order_type"],
                "volume": float(row["shares"]),
                "limit_price": float(limit_price),
            })
    else:
        logger.warning(f"Unexpected result format: {type(result)}")
    
    return formatted_result  # Return the formatted result



# Convert and format results to match desired output
# def format_result(result):
#     """Format the model's output to match the specified JSON structure."""
#     formatted_result = []

#     # Check if result is a DataFrame
#     if isinstance(result, pd.DataFrame):
#         for index, row in result.iterrows():
#             # Replace `limit_price` with `price` if `limit_price` is null (NaN)
#             limit_price = row["limit_price"] if pd.notnull(row["limit_price"]) else row["price"]
            
#             formatted_result.append({
#                 "step": index,
#                 "timestamp": convert_to_serializable(row["timestamp"]),
#                 "order_type": row["order_type"], #if pd.notnull(row["order_type"]) else "market",
#                 "volume": row["shares"],
#                 "limit_price": limit_price,
#                 # "price": row["price"]
#             })
#     else:
#         logger.warning(f"Unexpected result format: {type(result)}")

#     return formatted_result

# Convert to a serializable format
# def convert_to_serializable(obj):
#     """Convert non-serializable objects to a serializable format."""
#     if isinstance(obj, pd.Timestamp):
#         return obj.isoformat()  # Convert pd.Timestamp to ISO format string
#     elif isinstance(obj, pd.DataFrame):
#         return obj.to_dict(orient='records')
#     elif isinstance(obj, np.ndarray):
#         return obj.tolist()
#     elif isinstance(obj, np.generic):
#         return obj.item()
#     elif isinstance(obj, dict):
#         return {k: convert_to_serializable(v) for k, v in obj.items()}
#     elif isinstance(obj, list):
#         return [convert_to_serializable(item) for item in obj]
#     else:
#         return obj


def convert_to_serializable(obj):
    """Convert non-serializable objects to a serializable format."""
    if isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
#     else:
        return obj

if __name__ == "__main__":
    # Load the models from S3 and local storage
    model = model_fn(None)

    # Simulate a request body
    request_body = json.dumps({
        "ticker": "AMZN",
        "action": "buy",
        "inventory": 10000,
        "timeframe": 390
    })

    # Run the inference process
    input_data = input_fn(request_body, 'application/json')
    prediction = predict_fn(input_data, model)
    output = output_fn(prediction, 'application/json')
    print(output)  # Print the formatted output













# import logging
# import os
# import sys
# import json
# from datetime import datetime, timedelta
# import pytz
# import pandas as pd
# import numpy as np
# import time
# from pandas.tseries.holiday import USFederalHolidayCalendar
# from Adjusted_VWAP.adjusted_VWAP import Model
# # from blockhouse_ml.equities.buy.inference import EquitiesBuyInference


# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# logger.addHandler(logging.StreamHandler(sys.stdout))

# def model_fn(model_dir):
#     """Load both sell and buy models (macro and micro) when the SageMaker endpoint is initialized."""
#     logger.info("Initializing model")
#     start_t = time.perf_counter()
#     model = Model()
#     logger.info(f"Model initialized in {time.perf_counter() - start_t} seconds!!!")
#     return model


# # Input deserialization function
# def input_fn(request_body, content_type='application/json'):
#     """Deserialize the request body into a Python dictionary."""
#     if content_type == 'application/json':
#         logger.info("Deserializing the input data.")
#         # Parse the request body into a dictionary
#         input_data = json.loads(request_body)
        
#         logger.info(f"Input data: {input_data}")
#         return input_data
#         # return json.loads(request_body)
#     else:
#         raise ValueError(f"Unsupported content type: {content_type}")

# # Prediction function
# def predict_fn(input_data, model):
#     """Run the inference logic."""
#     ticker = input_data.get('ticker')
#     action = input_data.get('action', 'buy').lower()
#     inventory = input_data.get('inventory', 10000)
#     timeframe = input_data.get('timeframe', 390)  # Default to 390 if not provided

#     if action not in ['buy', 'sell']:
#         raise ValueError("Invalid action. Must be 'buy' or 'sell'.")

#     logger.info(f"Running {action} inference for ticker: {ticker}")

#     result = model.infer_model(
#         ticker=ticker,
#         side=action,
#         timeframe=timeframe,
#         inventory=inventory,
#     )

#     print(f'Result: {result}')

#     result = convert_to_serializable(result)

#     logger.info(f"Inference result: {result}")
#     return result

# # Output serialization function
# def output_fn(prediction, content_type='application/json'):
#     """Serialize the output into JSON format."""
#     prediction_serializable = convert_to_serializable(prediction)
#     return json.dumps(prediction_serializable)


# # Convert to a serializable format
# def convert_to_serializable(obj):
#     """Convert non-serializable objects to a serializable format."""
#     if isinstance(obj, pd.Timestamp):
#         return obj.isoformat()  # Convert pd.Timestamp to ISO format string
#     elif isinstance(obj, pd.DataFrame):
#         return obj.to_dict(orient='records')
#     elif isinstance(obj, np.ndarray):
#         return obj.tolist()
#     elif isinstance(obj, np.generic):
#         return obj.item()
#     elif isinstance(obj, dict):
#         return {k: convert_to_serializable(v) for k, v in obj.items()}
#     elif isinstance(obj, list):
#         return [convert_to_serializable(item) for item in obj]
#     else:
#         return obj

    
    
# if __name__ == "__main__":

#     # Load the models from S3 and local storage
#     model = model_fn(None)

#     # Simulate a request body
#     request_body = json.dumps({
#         "ticker": "AAPL",
#         "action": "buy",
#         "inventory": 2,
#         "timeframe": 390
#     })

#     # Run the inference process
#     input_data = input_fn(request_body, 'application/json')
#     prediction = predict_fn(input_data, model)
#     output = output_fn(prediction, 'application/json')

#     print("Prediction Result:", output)