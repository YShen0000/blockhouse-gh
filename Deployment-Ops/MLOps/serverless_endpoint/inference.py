import logging
import os
import sys
import json
from datetime import datetime, timedelta
import pytz
import boto3
import pandas as pd
import numpy as np
current_directory = os.getcwd()
print("Current Directory:", current_directory)
sys.path.append(os.getcwd())
from blockhouse_ml.equities.sell.inference import EquitiesSellInference
from blockhouse_ml.equities.buy.inference import EquitiesBuyInference

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

s3 = boto3.client('s3', region_name='us-east-1')
os.environ['S3_BUCKET'] = 'sagemaker-tradingmodel-us-east-1'
os.environ['PROD_VERSION'] = '1'

def download_model_from_s3(bucket_name, model_prefix, local_dir):
    """Download specific model files from S3 to the local directory."""
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    logger.info(f"Downloading {model_prefix} from {bucket_name} to {local_dir}")
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=model_prefix)

    if 'Contents' in response:
        for obj in response['Contents']:
            s3_key = obj['Key']
            local_file_path = os.path.join(local_dir, os.path.basename(s3_key))

            if s3_key.endswith('/'):
                continue

            s3.download_file(bucket_name, s3_key, local_file_path)
            logger.info(f"Downloaded {s3_key} to {local_file_path}")
    else:
        logger.warning(f"No files found for {model_prefix}")

def model_fn(model_dir):
    """Load both sell and buy models (macro and micro) when the SageMaker endpoint is initialized."""
    os.system("conda install -y -c conda-forge ta-lib")
    os.environ['S3_BUCKET'] = 'sagemaker-tradingmodel-us-east-1'
    os.environ['PROD_VERSION'] = '1'
    
    bucket_name = os.environ['S3_BUCKET']
    version = os.environ['PROD_VERSION']

    sell_macro_prefix = f'production/version_{version}/equities/sell/macro_trader/'
    sell_micro_prefix = f'production/version_{version}/equities/sell/micro_trader/'
    buy_macro_prefix = f'production/version_{version}/equities/buy/macro_trader/'
    buy_micro_prefix = f'production/version_{version}/equities/buy/micro_trader/'

    sell_macro_dir = os.path.join(model_dir, 'SellEquityModels')
    sell_micro_dir = os.path.join(model_dir, 'MicroSellEquityModels')
    buy_macro_dir = os.path.join(model_dir, 'BuyEquityModels')
    buy_micro_dir = os.path.join(model_dir, 'MicroBuyEquityModels')

    # Download models from S3
    download_model_from_s3(bucket_name, sell_macro_prefix, sell_macro_dir)
    download_model_from_s3(bucket_name, sell_micro_prefix, sell_micro_dir)
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

    logger.info("Initialized sell and buy models successfully.")
    
    return {
        'equities_sell_inference': equities_sell_inference,
        'equities_buy_inference': equities_buy_inference
    }

def input_fn(request_body):
    """Deserialize the request body into a Python dictionary."""
    return json.loads(request_body)

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

def output_fn(prediction):
    """Serialize the output into JSON format."""
    return json.dumps(prediction)

def run_equities_inference(ticker, action, timeframe, inventory, model):
    utc = pytz.UTC

    # Set end_timestamp to now
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
        elif action == 'buy':
            result = model['equities_buy_inference'].run_pipeline(
                ticker, start_timestamp=start_timestamp_str, end_timestamp=end_timestamp_str,
                timeframe=timeframe, inventory=inventory, trade_set_counter=1
            )

        return convert_to_serializable(result)
    
    except Exception as e:
        logger.error(f"Error running inference: {e}")
        raise ValueError(f"Error running inference: {e}")

def convert_to_serializable(obj):
    """Convert non-serializable objects to a serializable format."""
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
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
    elif isinstance(obj, (int, float, str)):  # Handle int, float, and str
        return obj  # Directly return these types
    else:
        logger.warning(f"Unexpected type encountered during serialization: {type(obj)}")
    
    return None  # Fallback case
    
# Remove or comment out this section when deploying in SageMaker
if __name__ == "__main__":
    
    # Define the directory where models will be downloaded and stored locally
    model_dir = './'

    # Load the models from S3 and local storage
    model = model_fn(model_dir)

    # Simulate a request body (for local testing only)
    request_body = json.dumps({
        "ticker": "JPM",
        "action": "sell",
        "inventory": 500,
        "timeframe": 390
    })

    # Run the inference process (for local testing only)
    input_data = input_fn(request_body)
    prediction = predict_fn(input_data, model)
    
    output = output_fn(prediction)

    print("Prediction Result:", output)