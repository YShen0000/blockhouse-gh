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

# Import Hoodwinked report calculation functions
from hoodwinked_report_calculations import preprocess_data, calculate_metrics, read_csv_from_s3  # Replace with actual paths

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
        logger.info(f"No files found for {model_prefix}")

def model_fn(model_dir):
    """Load both sell and buy models (macro and micro) when the SageMaker endpoint is initialized."""

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

    download_model_from_s3(bucket_name, sell_macro_prefix, sell_macro_dir)
    download_model_from_s3(bucket_name, sell_micro_prefix, sell_micro_dir)
    download_model_from_s3(bucket_name, buy_macro_prefix, buy_macro_dir)
    download_model_from_s3(bucket_name, buy_micro_prefix, buy_micro_dir)

    equities_sell_inference = EquitiesSellInference(macro_model_dir=sell_macro_dir, micro_model_dir=sell_micro_dir, data_dir=sell_macro_dir)
    equities_buy_inference = EquitiesBuyInference(macro_model_dir=buy_macro_dir, micro_model_dir=buy_micro_dir, data_dir=buy_macro_dir)

    logger.info(f"Initialized sell models at {sell_macro_dir} and {sell_micro_dir}")
    logger.info(f"Initialized buy models at {buy_macro_dir} and {buy_micro_dir}")

    return {
        'equities_sell_inference': equities_sell_inference,
        'equities_buy_inference': equities_buy_inference
    }

# Input deserialization function
def input_fn(request_body, content_type='application/json'):
    if content_type == 'application/json':
        input_data = json.loads(request_body)
        logger.info(f"Input data: {input_data}")
        return input_data
    else:
        raise ValueError(f"Unsupported content type: {content_type}")

# Prediction function
def predict_fn(input_data, model):
    action = input_data.get('action', 'buy').lower()
    
    if action in ['buy', 'sell']:
        # Run equities model inference
        ticker = input_data.get('ticker')
        inventory = input_data.get('inventory', 10000)
        timeframe = input_data.get('timeframe', 390)
        
        logger.info(f"Running {action} inference for ticker: {ticker}")
        result = run_equities_inference(ticker, action, timeframe, inventory, model)
        return result
    elif action == 'generate_report':
        # Generate Hoodwinked report from S3 CSV
        bucket_name = input_data.get('bucket_name')
        file_key = input_data.get('file_key')
        
        logger.info(f"Generating report for {bucket_name}/{file_key}")
        trade_blotter = read_csv_from_s3(bucket_name, file_key)
        trade_blotter = preprocess_data(trade_blotter)
        output = calculate_metrics(trade_blotter)
        return output
    else:
        raise ValueError(f"Invalid action: {action}")

# Output serialization function
def output_fn(prediction, content_type='application/json'):
    if content_type == 'application/json':
        return json.dumps(prediction)
    else:
        raise ValueError(f"Unsupported content type: {content_type}")

# Inference logic for buy/sell actions
def run_equities_inference(ticker, action, timeframe, inventory, model):
    utc = pytz.UTC
    end_timestamp = datetime.now(utc)
    start_timestamp = end_timestamp - timedelta(days=2)

    start_timestamp_str = start_timestamp.strftime('%Y-%m-%d')
    end_timestamp_str = end_timestamp.strftime('%Y-%m-%d')

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

# Convert to a serializable format
def convert_to_serializable(obj):
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
    else:
        return obj

# Main entry point for local testing (optional)
if __name__ == "__main__":
    model_dir = './'
    model = model_fn(model_dir)

    request_body = json.dumps({
        "ticker": "AAPL",
        "action": "buy",
        "inventory": 1,
        "timeframe": 390
    })

    input_data = input_fn(request_body, 'application/json')
    prediction = predict_fn(input_data, model)
    output = output_fn(prediction, 'application/json')

    print("Prediction Result:", output)
