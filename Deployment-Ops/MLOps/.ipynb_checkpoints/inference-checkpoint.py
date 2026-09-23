import logging
import os
import sys
import json
from datetime import datetime, timedelta
import pytz
import boto3
import pandas as pd
import numpy as np
from pandas.tseries.holiday import USFederalHolidayCalendar
from blockhouse_ml.equities.sell.inference import EquitiesSellInference
from blockhouse_ml.equities.buy.inference import EquitiesBuyInference


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

s3 = boto3.client('s3', region_name='us-east-1')

def download_model_from_s3(bucket_name, model_prefix, local_dir):
    """Download specific model files from S3 to the local directory."""
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    logger.info(f"Downloading {model_prefix} from {bucket_name} to {local_dir}")
    # List objects in the S3 bucket with the given prefix
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=model_prefix)

    if 'Contents' in response:
        logger.info(f"Got the following files for {model_prefix}:")
        for obj in response['Contents']:
            s3_key = obj['Key']
            local_file_path = os.path.join(local_dir, os.path.basename(s3_key))

            # Skip any key that represents a directory (ends with /)
            if s3_key.endswith('/'):
                continue

            # Download each valid file
            s3.download_file(bucket_name, s3_key, local_file_path)
            # print(f"Downloaded {s3_key} to {local_file_path}")
            logger.info(f"Downloaded {s3_key} to {local_file_path}")
    else:
        logger.info(f"No files found for {model_prefix}")

def model_fn(model_dir):
    """Load both sell and buy models (macro and micro) when the SageMaker endpoint is initialized."""

    # Define S3 bucket
    # Define S3 bucket
    bucket_name = os.environ['S3_BUCKET']
    version = os.environ['PROD_VERSION']

    # Define the paths for sell models (macro_trader and micro_trader)
    sell_macro_prefix = f'production/version_{version}/equities/sell/macro_trader/'
    sell_micro_prefix = f'production/version_{version}/equities/sell/micro_trader/'
    
    # Define the paths for buy models (macro_trader and micro_trader)
    buy_macro_prefix = f'production/version_{version}/equities/buy/macro_trader/'
    buy_micro_prefix = f'production/version_{version}/equities/buy/micro_trader/'

    # Define local directories for the sell and buy models
    sell_macro_dir = os.path.join(model_dir, 'SellEquityModels')
    sell_micro_dir = os.path.join(model_dir, 'MicroSellEquityModels')
    buy_macro_dir = os.path.join(model_dir, 'BuyEquityModels')
    buy_micro_dir = os.path.join(model_dir, 'MicroBuyEquityModels')

    # Download the sell models from S3
    download_model_from_s3(bucket_name, sell_macro_prefix, sell_macro_dir)
    download_model_from_s3(bucket_name, sell_micro_prefix, sell_micro_dir)

    # Download the buy models from S3
    download_model_from_s3(bucket_name, buy_macro_prefix, buy_macro_dir)
    download_model_from_s3(bucket_name, buy_micro_prefix, buy_micro_dir)

    # Initialize sell models after downloading
    equities_sell_inference = EquitiesSellInference(
        macro_model_dir=sell_macro_dir,
        micro_model_dir=sell_micro_dir,
        data_dir=sell_macro_dir  # Modify if data_dir is different
    )

    # Initialize buy models after downloading
    equities_buy_inference = EquitiesBuyInference(
        macro_model_dir=buy_macro_dir,
        micro_model_dir=buy_micro_dir,
        data_dir=buy_macro_dir  # Modify if data_dir is different
    )

    logger.info(f"Initialized sell models at {sell_macro_dir} and {sell_micro_dir}")
    logger.info(f"Initialized buy models at {buy_macro_dir} and {buy_micro_dir}")

    return {
        'equities_sell_inference': equities_sell_inference,
        'equities_buy_inference': equities_buy_inference
    }


# Input deserialization function
def input_fn(request_body, content_type='application/json'):
    """Deserialize the request body into a Python dictionary."""
    if content_type == 'application/json':
        logger.info("Deserializing the input data.")
        # Parse the request body into a dictionary
        input_data = json.loads(request_body)
        
        logger.info(f"Input data: {input_data}")
        return input_data
        # return json.loads(request_body)
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

    result = run_equities_inference(
        ticker=ticker,
        action=action,
        timeframe=timeframe,
        inventory=inventory,
        model=model
    )

    logger.info(f"Inference result: {result}")
    return result

# Output serialization function
def output_fn(prediction, content_type='application/json'):
    """Serialize the output into JSON format."""
    return json.dumps(prediction)

# Inference logic
def run_equities_inference(ticker, action, timeframe, inventory, model):
    utc = pytz.UTC

    # Set end_timestamp to 2 days ago
    end_timestamp = datetime.now(utc)
    start_timestamp = end_timestamp - timedelta(days=2)

    start_timestamp_str = start_timestamp.strftime('%Y-%m-%d')
    end_timestamp_str = end_timestamp.strftime('%Y-%m-%d')

    logger.info(f"Inference for {ticker}, {action} from {start_timestamp_str} to {end_timestamp_str}")
    try:
        if action == 'sell':
            result = model['equities_sell_inference'].run_pipeline(
                ticker, start_timestamp=start_timestamp_str, end_timestamp=end_timestamp_str,
                timeframe=timeframe, inventory=inventory, trade_set_counter=1
            )
            et_timezone = pytz.timezone('US/Eastern')
            results = []
            for res in result:
                res['timestamp'] = res['timestamp'].astimezone(et_timezone)
                results.append(res)
            result = results
        elif action == 'buy':
            result = model['equities_buy_inference'].run_pipeline(
                ticker, start_timestamp=start_timestamp_str, end_timestamp=end_timestamp_str,
                timeframe=timeframe, inventory=inventory, trade_set_counter=1
            )

        # print(result)

        return convert_to_serializable(result)
    except Exception as e:
        raise ValueError(f"Error running inference: {e}")

# Convert to a serializable format
def convert_to_serializable(obj):
    """Convert non-serializable objects to a serializable format."""
    if isinstance(obj, pd.Timestamp):
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
    # Define the directory where models will be downloaded and stored locally
    model_dir = './'

    # Load the models from S3 and local storage
    model = model_fn(model_dir)

    # Simulate a request body
    request_body = json.dumps({
        "ticker": "AAPL",
        "action": "buy",
        "inventory": 1,
        "timeframe": 390
    })

    # Run the inference process
    input_data = input_fn(request_body, 'application/json')
    prediction = predict_fn(input_data, model)
    output = output_fn(prediction, 'application/json')

    print("Prediction Result:", output)