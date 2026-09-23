import logging
import os
import sys
import json
from datetime import datetime, timedelta, date
import pytz
import boto3
import pandas as pd
import numpy as np
from pandas.tseries.holiday import USFederalHolidayCalendar
from blockhouse_ml.equities.sell.inference import EquitiesSellInference
from blockhouse_ml.equities.buy.inference import EquitiesBuyInference
from io import StringIO
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))

s3 = boto3.client('s3', region_name='us-east-1')

def download_csv_from_s3(bucket_name, s3_key, local_file_path):
    s3.download_file(bucket_name, s3_key, local_file_path)
    logger.info(f"Downloaded CSV to {local_file_path}")

def upload_csv_to_s3(bucket_name, s3_key, local_file_path):
    s3.upload_file(local_file_path, bucket_name, s3_key)
    logger.info(f"Uploaded {local_file_path} to s3://{bucket_name}/{s3_key}")

    
    
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
    bucket_name = os.environ.get('S3_BUCKET', 'sagemaker-tradingmodel-us-east-1')
    version = os.environ.get('PROD_VERSION', '1')  # Default to version 1 if not set

    # Set directories to /tmp instead of /home/model-server/tmp
    sell_macro_dir = '/tmp/SellEquityModels'
    sell_micro_dir = '/tmp/MicroSellEquityModels'
    buy_macro_dir = '/tmp/BuyEquityModels'
    buy_micro_dir = '/tmp/MicroBuyEquityModels'

    # Download model files from S3
    download_model_from_s3(bucket_name, f'production/version_{version}/equities/sell/macro_trader/', sell_macro_dir)
    download_model_from_s3(bucket_name, f'production/version_{version}/equities/sell/micro_trader/', sell_micro_dir)
    download_model_from_s3(bucket_name, f'production/version_{version}/equities/buy/macro_trader/', buy_macro_dir)
    download_model_from_s3(bucket_name, f'production/version_{version}/equities/buy/micro_trader/', buy_micro_dir)

    equities_sell_inference = EquitiesSellInference(
        macro_model_dir=sell_macro_dir,
        micro_model_dir=sell_micro_dir,
        data_dir=sell_macro_dir
    )

    equities_buy_inference = EquitiesBuyInference(
        macro_model_dir=buy_macro_dir,
        micro_model_dir=buy_micro_dir,
        data_dir=buy_macro_dir
    )

    logger.info(f"Initialized sell models at {sell_macro_dir} and {sell_micro_dir}")
    logger.info(f"Initialized buy models at {buy_macro_dir} and {buy_micro_dir}")

    return {
        'equities_sell_inference': equities_sell_inference,
        'equities_buy_inference': equities_buy_inference
    }



def input_fn(input_data, content_type):
    logger.info(f"Input content_type: {content_type}")
    
    if content_type == 'text/csv':
        logger.info(f"Received input data: {input_data[:100]}...")  # Log part of the data for debugging

        # Convert the CSV string into a pandas DataFrame
        csv_data = StringIO(input_data)
        df = pd.read_csv(csv_data)
        
        logger.info(f"Loaded {len(df)} rows of input data.")
        return df
    else:
        raise ValueError(f"Unsupported content type: {content_type}")


# def input_fn(input_data, content_type):
#     logger.info(f"Input content_type: {content_type}")
#     logger.info(f"Input data received: {input_data[:100]}...") 
#     if content_type == 'text/csv':
#         logger.info(f"Received input data: {input_data[:100]}...")
#         logger.info(f"Received input data: {input_data}")
        
#         if not input_data.startswith('s3://'):
#             raise ValueError(f"Invalid input format. Expected S3 URI, got: {input_data[:100]}...")
        
#         # Remove 's3://' prefix
#         s3_path = input_data.replace("s3://", "")
        
#         # Split the remaining path into bucket name and key
#         parts = s3_path.split("/", 1)
#         if len(parts) != 2:
#             raise ValueError(f"Invalid S3 path format: {input_data}")
        
#         bucket_name, s3_key = parts
        
#         logger.info(f"Parsed S3 path - Bucket: {bucket_name}, Key: {s3_key}")
        
#         # Path where the file will be downloaded locally
#         local_csv_path = '/tmp/input_data.csv'
        
#         try:
#             # Download the CSV file from S3
#             download_csv_from_s3(bucket_name, s3_key, local_csv_path)
#         except Exception as e:
#             logger.error(f"Error downloading file from S3: {str(e)}")
#             raise
        
#         # Load the CSV into a pandas DataFrame
#         df = pd.read_csv(local_csv_path)
#         logger.info(f"Loaded {len(df)} rows from S3 location {input_data}")
#         return df
#     else:
#         raise ValueError(f"Unsupported content type: {content_type}")



def predict_fn(input_data, model):
    results = []
    utc = pytz.UTC
    current_time = datetime.now(utc)
    
    for _, row in input_data.iterrows():
        ticker = row.get('Symbol')
        action = row.get('Action', 'buy').lower()
        inventory = row.get('Quantity', 10000)
        timeframe = row.get('timeframe', 390)

        if action not in ['buy', 'sell']:
            logger.warning(f"Invalid action '{action}' for ticker {ticker}. Skipping.")
            continue

        logger.info(f"Running {action} inference for ticker: {ticker}")

        try:
            result = run_equities_inference(
                ticker=ticker,
                action=action,
                timeframe=timeframe,
                inventory=inventory,
                model=model
            )
            
            if not result or len(result) == 0:
                logger.warning(f"No result for ticker: {ticker}")
                result = [{
                    'ticker': ticker,
                    'date': current_time.strftime('%Y-%m-%d'),
                    'inventory': inventory,
                    'status': 'No result',
                    'action': action
                }]
            else:
                for trade in result:
                    trade['ticker'] = ticker

            results.extend(result)
        
        except Exception as e:
            logger.error(f"Error running inference for ticker: {ticker} - {str(e)}", exc_info=True)
            results.append({
                'ticker': ticker,
                'date': current_time.strftime('%Y-%m-%d'),
                'inventory': inventory,
                'status': 'Error',
                'error_message': str(e),
                'action': action
            })

    # Rest of the function remains the same
    # Convert results to DataFrame and save to CSV
    results_df = pd.DataFrame(results)
    local_dir = '/tmp'
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    local_csv_file = os.path.join(local_dir, 'predictions.csv')
    # local_csv_file = './tmp/predictions.csv'
    results_df.to_csv(local_csv_file, index=False)

    logger.info(f"Saved predictions to {local_csv_file}")

    # Upload the CSV to S3
    bucket_name = os.environ.get('S3_BUCKET', 'sagemaker-tradingmodel-us-east-1')
    s3_file_path = 'predictions/predictions.csv'
    upload_csv_to_s3(bucket_name, s3_file_path, local_csv_file)

    return results

def output_fn(predictions, accept):
    results_df = pd.DataFrame(predictions)
    local_csv_file = '/tmp/predictions.csv'
    results_df.to_csv(local_csv_file, index=False)

    bucket_name = os.environ.get('S3_BUCKET', 'sagemaker-tradingmodel-us-east-1')
    output_s3_key = f'predictions/predictions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    upload_csv_to_s3(bucket_name, output_s3_key, local_csv_file)

    return json.dumps({
        'status': 'Success',
        's3_output_path': f"s3://{bucket_name}/{output_s3_key}"
    })



def run_equities_inference(ticker, action, timeframe, inventory, model):
    utc = pytz.UTC
    end_timestamp = datetime.now(utc)
    start_timestamp = end_timestamp - timedelta(days=2)
    start_timestamp_str = start_timestamp.strftime('%Y-%m-%d')
    end_timestamp_str = end_timestamp.strftime('%Y-%m-%d')

    logger.info(f"Inference for {ticker}, {action} from {start_timestamp_str} to {end_timestamp_str}")

    try:
        if action == 'sell':
            logger.info(f"Running sell inference for {ticker}")
            result = model['equities_sell_inference'].run_pipeline(
                ticker, start_timestamp=start_timestamp_str, end_timestamp=end_timestamp_str,
                timeframe=timeframe, inventory=inventory, trade_set_counter=1
            )
            logger.info(f"Sell inference result: {result}")
            et_timezone = pytz.timezone('US/Eastern')
            results = []
            for res in result:
                if isinstance(res, dict) and 'timestamp' in res:
                    res['timestamp'] = res['timestamp'].astimezone(et_timezone)
                    results.append(res)
                else:
                    logger.warning(f"Unexpected result format for sell action: {res}")
            result = results
        elif action == 'buy':
            logger.info(f"Running buy inference for {ticker}")
            result = model['equities_buy_inference'].run_pipeline(
                ticker, start_timestamp=start_timestamp_str, end_timestamp=end_timestamp_str,
                timeframe=timeframe, inventory=inventory, trade_set_counter=1
            )
            logger.info(f"Buy inference result: {result}")

        serialized_result = convert_to_serializable(result)
        logger.info(f"Serialized result: {serialized_result}")
        return serialized_result
    except Exception as e:
        logger.error(f"Error in run_equities_inference: {str(e)}", exc_info=True)
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
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, set):
        return list(obj)
    else:
        try:
            json.dumps(obj)
            return obj
        except TypeError:
            return str(obj)


if __name__ == "__main__":
    # Define the directory where models will be downloaded and stored locally
    model_dir = './'

    # Load the models from S3 and local storage
    model = model_fn(model_dir)

    # Path to the CSV file in S3
    csv_s3_path = 's3://sagemaker-tradingmodel-us-east-1/csv_dump/corrected_dates_output.csv'

    # Load input data from CSV
    input_data = input_fn(csv_s3_path, 'text/csv')

    # Run inference for all rows in the CSV
    predictions = predict_fn(input_data, model)

    # Serialize and print output
    output = output_fn(predictions, 'application/json')
    print("Prediction Results:", output)

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    # def input_fn(input_data, content_type):
#     if content_type == 'text/csv':
#         logger.info(f"Received input data: {input_data}")
        
#         # Remove 's3://' prefix if present
#         s3_path = input_data.replace("s3://", "")
        
#         # Split the remaining path, but handle cases where there might not be a '/'
#         parts = s3_path.split("/", 1)
#         if len(parts) == 2:
#             bucket_name, s3_key = parts
#         elif len(parts) == 1:
#             bucket_name = parts[0]
#             s3_key = ''
#         else:
#             raise ValueError(f"Invalid S3 path format: {input_data}")
        
#         logger.info(f"Parsed S3 path - Bucket: {bucket_name}, Key: {s3_key}")
        
#         local_csv_path = '/tmp/input_data.csv'
        
#         download_csv_from_s3(bucket_name, s3_key, local_csv_path)
        
#         df = pd.read_csv(local_csv_path)
#         logger.info(f"Loaded {len(df)} rows from S3 location {input_data}")
#         return df
#     else:
#         raise ValueError(f"Unsupported content type: {content_type}")

# def input_fn(input_data, content_type):
#     if content_type == 'text/csv':
#         # input_data is now the S3 URI of the CSV file
#         bucket_name, s3_key = input_data.replace("s3://", "").split("/", 1)
#         local_csv_path = '/tmp/input_data.csv'
        
#         download_csv_from_s3(bucket_name, s3_key, local_csv_path)
        
#         df = pd.read_csv(local_csv_path)
#         logger.info(f"Loaded {len(df)} rows from S3 location {input_data}")
#         return df
#     else:
#         raise ValueError(f"Unsupported content type: {content_type}")

# def predict_fn(input_data, model):
#     """Run the inference for each row in the DataFrame and save results as CSV."""
#     results = []
#     utc = pytz.UTC
#     current_time = datetime.now(utc)
#     # time.time()
#     for _, row in input_data.iterrows():
#         ticker = row.get('Symbol')
#         action = row.get('Action', 'buy').lower()
#         inventory = row.get('Quantity', 10000)
#         timeframe = row.get('timeframe', 390)

#         if action not in ['buy', 'sell']:
#             raise ValueError("Invalid action. Must be 'buy' or 'sell'.")

#         logger.info(f"Running {action} inference for ticker: {ticker}")

#         try:
#             result = run_equities_inference(
#                 ticker=ticker,
#                 action=action,
#                 timeframe=timeframe,
#                 inventory=inventory,
#                 model=model
#             )
            
#             if not result or len(result) == 0:
#                 # If no result was returned, log and append a "No result" row
#                 logger.warning(f"No result for ticker: {ticker}")
#                 result = [{
#                     'ticker': ticker,
#                     'date': current_time.strftime('%Y-%m-%d'),
#                     'inventory': inventory,
#                     'status': 'No result',
#                     'action': action
#                 }]
#             else:
#                 # Append result with ticker info for valid results
#                 for trade in result:
#                     trade['ticker'] = ticker

#             results.extend(result)
        
#         except Exception as e:
#             # Catch any exceptions and log "No result" for the ticker
#             logger.error(f"Error running inference for ticker: {ticker} - {str(e)}")
#             results.append({
#                 'ticker': ticker,
#                 'date': current_time.strftime('%Y-%m-%d'),
#                 'inventory': inventory,
#                 'status': 'Error',
#                 'error_message': str(e),
#                 'action': action
#             })




# def run_equities_inference(ticker, action, timeframe, inventory, model):
#     utc = pytz.UTC

#     end_timestamp = datetime.now(utc)
#     start_timestamp = end_timestamp - timedelta(days=2)

#     start_timestamp_str = start_timestamp.strftime('%Y-%m-%d')
#     end_timestamp_str = end_timestamp.strftime('%Y-%m-%d')

#     logger.info(f"Inference for {ticker}, {action} from {start_timestamp_str} to {end_timestamp_str}")

#     try:
#         if action == 'sell':
#             result = model['equities_sell_inference'].run_pipeline(
#                 ticker, start_timestamp=start_timestamp_str, end_timestamp=end_timestamp_str,
#                 timeframe=timeframe, inventory=inventory, trade_set_counter=1
#             )
#             et_timezone = pytz.timezone('US/Eastern')
#             results = []
#             for res in result:
#                 res['timestamp'] = res['timestamp'].astimezone(et_timezone)
#                 results.append(res)
#             result = results
#         elif action == 'buy':
#             result = model['equities_buy_inference'].run_pipeline(
#                 ticker, start_timestamp=start_timestamp_str, end_timestamp=end_timestamp_str,
#                 timeframe=timeframe, inventory=inventory, trade_set_counter=1
#             )

#         return convert_to_serializable(result)
#     except Exception as e:
#         raise ValueError(f"Error running inference: {e}")

# def convert_to_serializable(obj):
#     """Convert non-serializable objects to a serializable format."""
#     if isinstance(obj, pd.Timestamp):
#         return obj.isoformat()
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