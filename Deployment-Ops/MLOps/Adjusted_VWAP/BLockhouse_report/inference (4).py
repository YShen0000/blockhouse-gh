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
# from blockhouse_ml.equities.buy.inference import EquitiesBuyInference

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
        # Parse the request body into a dictionary
        input_data = json.loads(request_body)
        logger.info(f"Input data: {input_data}")
        return input_data
    else:
        raise ValueError(f"Unsupported content type: {content_type}")



def predict_fn(input_data, model):
    """Run the inference logic."""
    ticker = input_data.get('ticker')
    action = input_data.get('action', 'buy').lower()
    inventory = input_data.get('inventory', 1)
    timeframe = input_data.get('timeframe', 390)  # Default to 390 if not provided
    # end_timestamp = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    end_timestamp = input_data.get('end_timestamp')
    end_timestamp = datetime.strptime(end_timestamp, '%Y-%m-%d')
    end_timestamp = (end_timestamp - timedelta(days=1)).strftime('%Y-%m-%d')
    print("end_timestamp",end_timestamp)
    current_year = datetime.utcnow().year
    start_year = current_year - 1  # Check holidays from 3 years ago
    end_year = current_year + 1    # Check holidays up to 3 years in the future

    # Generate U.S. holidays dynamically within a range around the current year
    us_holidays = USFederalHolidayCalendar().holidays(
        start=f"{start_year}-01-01", 
        end=f"{end_year}-12-31"
    )

    end_date = pd.Timestamp(end_timestamp)

    # Adjust end_timestamp if it’s a holiday or weekend
    while end_date in us_holidays or end_date.weekday() >= 5:  # Saturday is 5, Sunday is 6
        end_date -= pd.Timedelta(days=1)
    end_timestamp = end_date.strftime('%Y-%m-%d')
    if action not in ['buy', 'sell']:
        raise ValueError("Invalid action. Must be 'buy' or 'sell'.")
    # end_timestamp = (datetime.strptime(end_timestamp, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    # end_timestamp = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    logger.info(f"Running {action} inference for ticker: {ticker}")

    result = model.infer_model(
        ticker=ticker,
        side=action,
        timeframe=timeframe,
        inventory=inventory,
        end_timestamp=end_timestamp
    )

    print(f'Result: {result}')

    result = convert_to_serializable(result)

    logger.info(f"Inference result: {result}")
    return result

# Output serialization function
def output_fn(prediction, content_type='application/json'):
    """Serialize the output into JSON format."""
    prediction_serializable = convert_to_serializable(prediction)
    return json.dumps(prediction_serializable)

# Convert to a serializable format
def convert_to_serializable(obj):
    """Convert non-serializable objects to a serializable format."""
    if obj is None or (isinstance(obj, float) and np.isnan(obj)):
        return None  # Convert None and NaN to None (for JSON compatibility)
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()  # Convert pd.Timestamp to ISO format string
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
    else:
        return obj

if __name__ == "__main__":
    # Get user inputs for ticker and action
    # ticker = input("Enter the ticker symbol (e.g., 'AAPL'): ")
    # action = input("Enter the action ('buy' or 'sell'): ").lower()
    
    # Load the models from S3 and local storage
    model = model_fn(None)

    # Prepare request data with defaults and dynamic end_timestamp
    request_body = json.dumps({
       "ticker": "JPM",
        "action": "buy",
        "end_timestamp": "2024-10-28"
    })

    # Run the inference process
    input_data = input_fn(request_body, 'application/json')
    prediction = predict_fn(input_data, model)
    output = output_fn(prediction, 'application/json')

    print("Prediction Result:", output)
