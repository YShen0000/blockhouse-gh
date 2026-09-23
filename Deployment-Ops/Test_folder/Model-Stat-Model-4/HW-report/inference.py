import logging
import os
import sys
import json
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
import time
import boto3
from pandas.tseries.holiday import USFederalHolidayCalendar
from Adjusted_VWAP.adjusted_VWAP import Model
# from blockhouse_ml.equities.buy.inference import EquitiesBuyInference
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


def model_fn(model_dir):
    """Load both sell and buy models (macro and micro) when the SageMaker endpoint is initialized."""
    logger.info("Initializing model")
    start_t = time.perf_counter()
    model = Model()
    logger.info(f"Model initialized in {time.perf_counter() - start_t} seconds!!!")
    return model


# Input deserialization function

def input_fn(input_data, content_type):
    logger.info(f"Input content_type: {content_type}")
    
    if content_type == 'text/csv':
        if input_data.startswith("s3://"):
            # Parse S3 path to get bucket and key
            bucket_name, s3_key = input_data.replace("s3://", "").split("/", 1)
            local_file_path = '/tmp/downloaded_input.csv'
            
            # Download CSV from S3
            download_csv_from_s3(bucket_name, s3_key, local_file_path)
            
            # Load CSV into DataFrame
            df = pd.read_csv(local_file_path)
        else:
            # If input_data is CSV content, read directly from it
            csv_data = StringIO(input_data)
            df = pd.read_csv(csv_data)
        
        logger.info(f"Loaded {len(df)} rows of input data.")
        return df
    else:
        raise ValueError(f"Unsupported content type: {content_type}")

# Prediction function

def predict_fn(input_data, model):
    results = []
    utc = pytz.UTC
    current_time = datetime.now(utc)
    counter = 1  # Initialize counter
    
    for _, row in input_data.iterrows():
        ticker = row.get('Symbol')
        action = row.get('Action', 'buy').lower()
        inventory = row.get('Quantity', 10000)
        timeframe = row.get('timeframe', 390)
        end_timestamp = row.get('Date', datetime.now(utc))
        end_timestamp = datetime.strptime(end_timestamp, '%Y-%m-%d')
        # end_timestamp = (end_timestamp - timedelta(days=1)).strftime('%Y-%m-%d')
        
        current_year = datetime.utcnow().year
        start_year = current_year - 1
        end_year = current_year

        us_holidays = USFederalHolidayCalendar().holidays(
            start=f"{start_year}-01-01", 
            end=f"{end_year}-12-31"
        )
        
        end_date = pd.Timestamp(end_timestamp)

        while end_date in us_holidays or end_date.weekday() >= 5:
            end_date -= pd.Timedelta(days=1)
        end_timestamp = end_date.strftime('%Y-%m-%d')
        
        if action not in ['buy', 'sell']:
            logger.warning(f"Invalid action '{action}' for ticker {ticker}. Skipping.")
            continue

        logger.info(f"Running {action} inference for ticker: {ticker} inventory {inventory} timeframe {timeframe} end_timestamp {end_timestamp}")
        
        try:
            # Run the model inference
            result = model.infer_model(
                ticker=ticker,
                side=action,
                inventory=inventory,
                timeframe=timeframe,
                end_timestamp=end_timestamp,
                backtest=True
            )
            
            # Check result type and process accordingly
            if isinstance(result, pd.DataFrame):
                if result.empty:
                    logger.warning(f"No result for ticker: {ticker}")
                    result = [{
                        'ticker': ticker,
                        'date': current_time.strftime('%Y-%m-%d'),
                        'inventory': inventory,
                        'status': 'No result',
                        'action': action,
                        'counter': counter
                    }]
                else:
                    result = result.to_dict(orient='records')
                    
            elif isinstance(result, list) and all(isinstance(item, dict) for item in result):
                for trade in result:
                    trade['ticker'] = ticker  # Add ticker to each trade dictionary
                    trade['counter'] = counter
            else:
                logger.error(f"Unexpected result format for ticker: {ticker}")
                result = [{
                    'ticker': ticker,
                    'date': current_time.strftime('%Y-%m-%d'),
                    'inventory': inventory,
                    'status': 'Error',
                    'error_message': "Unexpected result format",
                    'action': action,
                    'counter': counter
                }]
            
            # Ensure all entries in result have the ticker and counter keys
            for trade in result:
                trade['ticker'] = ticker
                trade['counter'] = counter
            
            results.extend(result)
        
        except Exception as e:
            logger.error(f"Error running inference for ticker: {ticker} - {str(e)}", exc_info=True)
            results.append({
                'ticker': ticker,
                'date': current_time.strftime('%Y-%m-%d'),
                'inventory': inventory,
                'status': 'Error',
                'error_message': str(e),
                'action': action,
                'counter': counter
            })

        counter += 1  # Increment the counter for the next row

    # Save predictions to CSV and upload to S3
    results_df = pd.DataFrame(results)
    local_dir = '/tmp'
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    local_csv_file = os.path.join(local_dir, 'predictions.csv')
    results_df.to_csv(local_csv_file, index=False)

    logger.info(f"Saved predictions to {local_csv_file}")

    bucket_name = os.environ.get('S3_BUCKET', 'sagemaker-tradingmodel-us-east-1')
    s3_file_path = 'predictions/predictions.csv'
    upload_csv_to_s3(bucket_name, s3_file_path, local_csv_file)

    return results



def output_fn(predictions, accept):
    # Convert predictions to a DataFrame
    results_df = pd.DataFrame(predictions)
    
    # Define local file paths
    local_csv_file = '/tmp/predictions.csv'
    local_json_file = '/tmp/predictions.json'
    
    # Save CSV and JSON locally
    results_df.to_csv(local_csv_file, index=False)
    results_df.to_json(local_json_file, orient='records', lines=True)  # Using 'records' and 'lines' for JSON format compatibility
    
    # Define S3 bucket and output paths
    bucket_name = os.environ.get('S3_BUCKET', 'sagemaker-tradingmodel-us-east-1')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv_key = f'predictions/predictions_{timestamp}.csv'
    output_json_key = f'predictions/predictions_{timestamp}.json'
    
    # Upload both CSV and JSON files to S3
    upload_csv_to_s3(bucket_name, output_csv_key, local_csv_file)
    upload_csv_to_s3(bucket_name, output_json_key, local_json_file)
    
    # Return both S3 output paths as a JSON response
    return json.dumps({
        'status': 'Success',
        's3_output_csv_path': f"s3://{bucket_name}/{output_csv_key}",
        's3_output_json_path': f"s3://{bucket_name}/{output_json_key}"
    }, indent=4)




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
    # Define the directory where models will be downloaded and stored locally
    model_dir = './'

    # Load the models from S3 and local storage
    model = model_fn(model_dir)

    # Path to the CSV file in S3
    csv_s3_path = 's3://sagemaker-tradingmodel-us-east-1/csv_dump/corrected_dates_output_just_2.csv'

    # Load input data from CSV
    input_data = input_fn(csv_s3_path, 'text/csv')

    # Run inference for all rows in the CSV
    predictions = predict_fn(input_data, model)

    # Serialize and print output
    output = output_fn(predictions, 'application/json')
    print("Prediction Results:", output)
    





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
#     if obj is None or (isinstance(obj, float) and np.isnan(obj)):
#         return None  # Convert None and NaN to None (for JSON compatibility)
#     elif isinstance(obj, pd.Timestamp):
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











# import logging
# import os
# import sys
# import json
# from datetime import datetime, timedelta
# import pytz
# import pandas as pd
# import numpy as np
# import time
# import boto3
# from pandas.tseries.holiday import USFederalHolidayCalendar
# from Adjusted_VWAP.adjusted_VWAP import Model
# # from blockhouse_ml.equities.buy.inference import EquitiesBuyInference
# from io import StringIO

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# logger.addHandler(logging.StreamHandler(sys.stdout))

# s3 = boto3.client('s3', region_name='us-east-1')

# def download_csv_from_s3(bucket_name, s3_key, local_file_path):
#     s3.download_file(bucket_name, s3_key, local_file_path)
#     logger.info(f"Downloaded CSV to {local_file_path}")

# def upload_csv_to_s3(bucket_name, s3_key, local_file_path):
#     s3.upload_file(local_file_path, bucket_name, s3_key)
#     logger.info(f"Uploaded {local_file_path} to s3://{bucket_name}/{s3_key}")


# def model_fn(model_dir):
#     """Load both sell and buy models (macro and micro) when the SageMaker endpoint is initialized."""
#     logger.info("Initializing model")
#     start_t = time.perf_counter()
#     model = Model()
#     logger.info(f"Model initialized in {time.perf_counter() - start_t} seconds!!!")
#     return model


# # Input deserialization function

# def input_fn(input_data, content_type):
#     logger.info(f"Input content_type: {content_type}")
    
#     if content_type == 'text/csv':
#         if input_data.startswith("s3://"):
#             # Parse S3 path to get bucket and key
#             bucket_name, s3_key = input_data.replace("s3://", "").split("/", 1)
#             local_file_path = '/tmp/downloaded_input.csv'
            
#             # Download CSV from S3
#             download_csv_from_s3(bucket_name, s3_key, local_file_path)
            
#             # Load CSV into DataFrame
#             df = pd.read_csv(local_file_path)
#         else:
#             # If input_data is CSV content, read directly from it
#             csv_data = StringIO(input_data)
#             df = pd.read_csv(csv_data)
        
#         logger.info(f"Loaded {len(df)} rows of input data.")
#         return df
#     else:
#         raise ValueError(f"Unsupported content type: {content_type}")

# # Prediction function

# # def predict_fn(input_data, model):
# #     results = []
# #     utc = pytz.UTC
# #     current_time = datetime.now(utc)
    
# #     for _, row in input_data.iterrows():
# #         ticker = row.get('Symbol')
# #         action = row.get('Action', 'buy').lower()
# #         inventory = row.get('Quantity', 10000)
# #         timeframe = row.get('timeframe', 390)
# #         end_timestamp = row.get('Date', datetime.now(utc))
# #         end_timestamp = datetime.strptime(end_timestamp, '%Y-%m-%d')
# #         end_timestamp = (end_timestamp - timedelta(days=1)).strftime('%Y-%m-%d')
        
# #         current_year = datetime.utcnow().year
# #         start_year = current_year - 1
# #         end_year = current_year

# #         us_holidays = USFederalHolidayCalendar().holidays(
# #             start=f"{start_year}-01-01", 
# #             end=f"{end_year}-12-31"
# #         )
        
# #         end_date = pd.Timestamp(end_timestamp)

# #         while end_date in us_holidays or end_date.weekday() >= 5:
# #             end_date -= pd.Timedelta(days=1)
# #         end_timestamp = end_date.strftime('%Y-%m-%d')
        
# #         if action not in ['buy', 'sell']:
# #             logger.warning(f"Invalid action '{action}' for ticker {ticker}. Skipping.")
# #             continue

# #         logger.info(f"Running {action} inference for ticker: {ticker} inventory {inventory} timeframe {timeframe} end_timestamp {end_timestamp}")
        
# #         try:
# #             result = model.infer_model(
# #                 ticker=ticker,
# #                 side=action,
# #                 inventory=inventory,
# #                 timeframe=timeframe,
# #                 end_timestamp=end_timestamp,
# #                 backtest=True
# #             )
            
# #             # Use result.empty to check if the DataFrame has rows
# #             if result.empty:
# #                 logger.warning(f"No result for ticker: {ticker}")
# #                 result = [{
# #                     'ticker': ticker,
# #                     'date': current_time.strftime('%Y-%m-%d'),
# #                     'inventory': inventory,
# #                     'status': 'No result',
# #                     'action': action
# #                 }]
# #             else:
# #                 for trade in result:
# #                     trade['ticker'] = ticker

# #             results.extend(result)
        
# #         except Exception as e:
# #             logger.error(f"Error running inference for ticker: {ticker} - {str(e)}", exc_info=True)
# #             results.append({
# #                 'ticker': ticker,
# #                 'date': current_time.strftime('%Y-%m-%d'),
# #                 'inventory': inventory,
# #                 'status': 'Error',
# #                 'error_message': str(e),
# #                 'action': action
# #             })

# #     results_df = pd.DataFrame(results)
# #     local_dir = '/tmp'
# #     if not os.path.exists(local_dir):
# #         os.makedirs(local_dir)
# #     local_csv_file = os.path.join(local_dir, 'predictions.csv')
# #     results_df.to_csv(local_csv_file, index=False)

# #     logger.info(f"Saved predictions to {local_csv_file}")

# #     bucket_name = os.environ.get('S3_BUCKET', 'sagemaker-tradingmodel-us-east-1')
# #     s3_file_path = 'predictions/predictions.csv'
# #     upload_csv_to_s3(bucket_name, s3_file_path, local_csv_file)

# #     return results


# def predict_fn(input_data, model):
#     results = []
#     utc = pytz.UTC
#     current_time = datetime.now(utc)
#     counter = 1  # Initialize counter
    
#     for _, row in input_data.iterrows():
#         ticker = row.get('Symbol')
#         action = row.get('Action', 'buy').lower()
#         inventory = row.get('Quantity', 10000)
#         timeframe = row.get('timeframe', 390)
#         end_timestamp = row.get('Date', datetime.now(utc))
#         end_timestamp = datetime.strptime(end_timestamp, '%Y-%m-%d')
#         end_timestamp = (end_timestamp - timedelta(days=1)).strftime('%Y-%m-%d')
        
#         current_year = datetime.utcnow().year
#         start_year = current_year - 1
#         end_year = current_year

#         us_holidays = USFederalHolidayCalendar().holidays(
#             start=f"{start_year}-01-01", 
#             end=f"{end_year}-12-31"
#         )
        
#         end_date = pd.Timestamp(end_timestamp)

#         while end_date in us_holidays or end_date.weekday() >= 5:
#             end_date -= pd.Timedelta(days=1)
#         end_timestamp = end_date.strftime('%Y-%m-%d')
        
#         if action not in ['buy', 'sell']:
#             logger.warning(f"Invalid action '{action}' for ticker {ticker}. Skipping.")
#             continue

#         logger.info(f"Running {action} inference for ticker: {ticker} inventory {inventory} timeframe {timeframe} end_timestamp {end_timestamp}")
        
#         try:
#             # Run the model inference
#             result = model.infer_model(
#                 ticker=ticker,
#                 side=action,
#                 inventory=inventory,
#                 timeframe=timeframe,
#                 end_timestamp=end_timestamp,
#                 backtest=True
#             )
            
#             # Check result type and process accordingly
#             if isinstance(result, pd.DataFrame):
#                 if result.empty:
#                     logger.warning(f"No result for ticker: {ticker}")
#                     result = [{
#                         'ticker': ticker,
#                         'date': current_time.strftime('%Y-%m-%d'),
#                         'inventory': inventory,
#                         'status': 'No result',
#                         'action': action,
#                         'counter': counter
#                     }]
#                 else:
#                     result = result.to_dict(orient='records')
                    
#             elif isinstance(result, list) and all(isinstance(item, dict) for item in result):
#                 for trade in result:
#                     trade['ticker'] = ticker  # Add ticker to each trade dictionary
#                     trade['counter'] = counter
#             else:
#                 logger.error(f"Unexpected result format for ticker: {ticker}")
#                 result = [{
#                     'ticker': ticker,
#                     'date': current_time.strftime('%Y-%m-%d'),
#                     'inventory': inventory,
#                     'status': 'Error',
#                     'error_message': "Unexpected result format",
#                     'action': action,
#                     'counter': counter
#                 }]
            
#             # Ensure all entries in result have the ticker and counter keys
#             for trade in result:
#                 trade['ticker'] = ticker
#                 trade['counter'] = counter
            
#             results.extend(result)
        
#         except Exception as e:
#             logger.error(f"Error running inference for ticker: {ticker} - {str(e)}", exc_info=True)
#             results.append({
#                 'ticker': ticker,
#                 'date': current_time.strftime('%Y-%m-%d'),
#                 'inventory': inventory,
#                 'status': 'Error',
#                 'error_message': str(e),
#                 'action': action,
#                 'counter': counter
#             })

#         counter += 1  # Increment the counter for the next row

#     # Save predictions to CSV and upload to S3
#     results_df = pd.DataFrame(results)
#     local_dir = '/tmp'
#     if not os.path.exists(local_dir):
#         os.makedirs(local_dir)
#     local_csv_file = os.path.join(local_dir, 'predictions.csv')
#     results_df.to_csv(local_csv_file, index=False)

#     logger.info(f"Saved predictions to {local_csv_file}")

#     bucket_name = os.environ.get('S3_BUCKET', 'sagemaker-tradingmodel-us-east-1')
#     s3_file_path = 'predictions/predictions.csv'
#     upload_csv_to_s3(bucket_name, s3_file_path, local_csv_file)

#     return results


# # def predict_fn(input_data, model):
# #     results = []
# #     utc = pytz.UTC
# #     current_time = datetime.now(utc)
    
# #     for _, row in input_data.iterrows():
# #         ticker = row.get('Symbol')
# #         action = row.get('Action', 'buy').lower()
# #         inventory = row.get('Quantity', 10000)
# #         timeframe = row.get('timeframe', 390)
# #         end_timestamp = row.get('Date', datetime.now(utc))
# #         end_timestamp = datetime.strptime(end_timestamp, '%Y-%m-%d')
# #         end_timestamp = (end_timestamp - timedelta(days=1)).strftime('%Y-%m-%d')
        
# #         current_year = datetime.utcnow().year
# #         start_year = current_year - 1
# #         end_year = current_year

# #         us_holidays = USFederalHolidayCalendar().holidays(
# #             start=f"{start_year}-01-01", 
# #             end=f"{end_year}-12-31"
# #         )
        
# #         end_date = pd.Timestamp(end_timestamp)

# #         while end_date in us_holidays or end_date.weekday() >= 5:
# #             end_date -= pd.Timedelta(days=1)
# #         end_timestamp = end_date.strftime('%Y-%m-%d')
        
# #         if action not in ['buy', 'sell']:
# #             logger.warning(f"Invalid action '{action}' for ticker {ticker}. Skipping.")
# #             continue

# #         logger.info(f"Running {action} inference for ticker: {ticker} inventory {inventory} timeframe {timeframe} end_timestamp {end_timestamp}")
        
# #         try:
# #             # Run the model inference
# #             result = model.infer_model(
# #                 ticker=ticker,
# #                 side=action,
# #                 inventory=inventory,
# #                 timeframe=timeframe,
# #                 end_timestamp=end_timestamp,
# #                 backtest=True
# #             )
            
# #             # Check result type and process accordingly
# #             if isinstance(result, pd.DataFrame):
# #                 if result.empty:
# #                     logger.warning(f"No result for ticker: {ticker}")
# #                     result = [{
# #                         'ticker': ticker,
# #                         'date': current_time.strftime('%Y-%m-%d'),
# #                         'inventory': inventory,
# #                         'status': 'No result',
# #                         'action': action
# #                     }]
# #                 else:
# #                     result = result.to_dict(orient='records')
                    
# #             elif isinstance(result, list) and all(isinstance(item, dict) for item in result):
# #                 for trade in result:
# #                     trade['ticker'] = ticker  # Add ticker to each trade dictionary
# #             else:
# #                 logger.error(f"Unexpected result format for ticker: {ticker}")
# #                 result = [{
# #                     'ticker': ticker,
# #                     'date': current_time.strftime('%Y-%m-%d'),
# #                     'inventory': inventory,
# #                     'status': 'Error',
# #                     'error_message': "Unexpected result format",
# #                     'action': action
# #                 }]
            
# #             # Ensure all entries in result have the ticker key
# #             for trade in result:
# #                 trade['ticker'] = ticker
            
# #             results.extend(result)
        
# #         except Exception as e:
# #             logger.error(f"Error running inference for ticker: {ticker} - {str(e)}", exc_info=True)
# #             results.append({
# #                 'ticker': ticker,
# #                 'date': current_time.strftime('%Y-%m-%d'),
# #                 'inventory': inventory,
# #                 'status': 'Error',
# #                 'error_message': str(e),
# #                 'action': action
# #             })

# #     # Save predictions to CSV and upload to S3
# #     results_df = pd.DataFrame(results)
# #     local_dir = '/tmp'
# #     if not os.path.exists(local_dir):
# #         os.makedirs(local_dir)
# #     local_csv_file = os.path.join(local_dir, 'predictions.csv')
# #     results_df.to_csv(local_csv_file, index=False)

# #     logger.info(f"Saved predictions to {local_csv_file}")

# #     bucket_name = os.environ.get('S3_BUCKET', 'sagemaker-tradingmodel-us-east-1')
# #     s3_file_path = 'predictions/predictions.csv'
# #     upload_csv_to_s3(bucket_name, s3_file_path, local_csv_file)

# #     return results

# def output_fn(predictions, accept):
#     # Convert predictions to a DataFrame
#     results_df = pd.DataFrame(predictions)
    
#     # Define local file paths
#     local_csv_file = '/tmp/predictions.csv'
#     local_json_file = '/tmp/predictions.json'
    
#     # Save CSV and JSON locally
#     results_df.to_csv(local_csv_file, index=False)
#     results_df.to_json(local_json_file, orient='records', lines=True)  # Using 'records' and 'lines' for JSON format compatibility
    
#     # Define S3 bucket and output paths
#     bucket_name = os.environ.get('S3_BUCKET', 'sagemaker-tradingmodel-us-east-1')
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     output_csv_key = f'predictions/predictions_{timestamp}.csv'
#     output_json_key = f'predictions/predictions_{timestamp}.json'
    
#     # Upload both CSV and JSON files to S3
#     upload_csv_to_s3(bucket_name, output_csv_key, local_csv_file)
#     upload_csv_to_s3(bucket_name, output_json_key, local_json_file)
    
#     # Return both S3 output paths as a JSON response
#     return json.dumps({
#         'status': 'Success',
#         's3_output_csv_path': f"s3://{bucket_name}/{output_csv_key}",
#         's3_output_json_path': f"s3://{bucket_name}/{output_json_key}"
#     }, indent=4)




# # def output_fn(predictions, accept):
# #     # Convert predictions to a DataFrame
# #     results_df = pd.DataFrame(predictions)
    
# #     # Define local file path
# #     local_csv_file = '/tmp/predictions.csv'
# #     results_df.to_csv(local_csv_file, index=False)
    
# #     # Define S3 bucket and output path
# #     bucket_name = os.environ.get('S3_BUCKET', 'sagemaker-tradingmodel-us-east-1')
# #     output_s3_key = f'predictions/predictions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
# #     # Upload the file to S3
# #     upload_csv_to_s3(bucket_name, output_s3_key, local_csv_file)
    
# #     # Return the S3 output path as JSON response
# #     return json.dumps({
# #         'status': 'Success',
# #         's3_output_path': f"s3://{bucket_name}/{output_s3_key}"
# #     }, indent=4)




# # Convert to a serializable format
# def convert_to_serializable(obj):
#     """Convert non-serializable objects to a serializable format."""
#     if obj is None or (isinstance(obj, float) and np.isnan(obj)):
#         return None  # Convert None and NaN to None (for JSON compatibility)
#     elif isinstance(obj, pd.Timestamp):
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
#     # Define the directory where models will be downloaded and stored locally
#     model_dir = './'

#     # Load the models from S3 and local storage
#     model = model_fn(model_dir)

#     # Path to the CSV file in S3
#     csv_s3_path = 's3://sagemaker-tradingmodel-us-east-1/csv_dump/corrected_dates_output_just_2.csv'

#     # Load input data from CSV
#     input_data = input_fn(csv_s3_path, 'text/csv')

#     # Run inference for all rows in the CSV
#     predictions = predict_fn(input_data, model)

#     # Serialize and print output
#     output = output_fn(predictions, 'application/json')
#     print("Prediction Results:", output)
    



    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    


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
#     if obj is None or (isinstance(obj, float) and np.isnan(obj)):
#         return None  # Convert None and NaN to None (for JSON compatibility)
#     elif isinstance(obj, pd.Timestamp):
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