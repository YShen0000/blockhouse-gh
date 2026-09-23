import pandas as pd
import yfinance as yf

import boto3
import os
import json

from datetime import datetime, timedelta
from random import randrange
from io import StringIO

# ========================================================= #
#                                                           #  
# Helper Functions                                          #
#                                                           #
# ========================================================= #

def is_fund(symbol_symbol):
    """
    Determine if a given symbol symbol represents a fund.

    Args:
    symbol_symbol (str): The symbol symbol to check.

    Returns:
    bool: True if the symbol represents a fund, False otherwise.
    """
    # Fetch the symbol info
    symbol = yf.Ticker(symbol_symbol)
    info = symbol.info

    # Funds often lack industry and sector info, or might have "Fund" or "ETF" in the long business summary
    industry = info.get('industry', None)
    sector = info.get('sector', None)

    return not industry and not sector



def check_date_threshold(trade_blotter):
    """
    Filter trades that occurred within the last 2 years.

    Args:
    trade_blotter (pd.DataFrame): DataFrame containing trade data. Must have 'Date' column

    Returns:
    pd.DataFrame: Filtered DataFrame with recent trades.
    """

    # Convert the 'Date' to datetime
    trade_blotter['Date'] = pd.to_datetime(trade_blotter['Date'], errors='coerce')

    # Get the date 2 years ago from the current date
    two_years_ago = datetime.now() - timedelta(days=2*365)

    # Return the filtered trades that occurred within the last 2 years
    return trade_blotter[trade_blotter['Date'] >= two_years_ago]

# ========================================================= #
#                                                           #  
# Model Inference                                           #
#                                                           #
# ========================================================= #

def request_async_inference(trade_blotter):
    """
    Requests the async endpoint for an inference on the given DataFrame

    Args:
    trade_blotter (pd.DataFrame): DataFrame containing trade data.

    Returns:
    str: Output file for the async inference
    """
    # Parameters
    bucket_name = 'sagemaker-tradingmodel-us-east-1'
    endpoint_name = 'MainPackage-HW-report-endpoint'

    # Convert Date to %Y-%m-%d as required by the inference
    trade_blotter['Date'] = trade_blotter['Date'].dt.strftime('%Y-%m-%d')

    # Makes a temp csv file to upload
    input_file_name = f'_temp_inference_data.csv'
    trade_blotter.to_csv(f'./{input_file_name}')

    input_file_path = f'./{input_file_name}'
    upload_location = f's3://sagemaker-tradingmodel-us-east-1/csv_dump/{input_file_name}'

    # Create an s3 client and upload to s3 bucket data we need to compute
    s3 = boto3.client('s3',
        region_name=os.getenv('AWS_DEFAULT_REGION'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    s3.upload_file(input_file_path, bucket_name, f'csv_dump/{input_file_name}')

    # Create a low-level Sagemaker client
    sagemaker_runtime = boto3.client(
        "sagemaker-runtime", 
        region_name=os.getenv('AWS_DEFAULT_REGION'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

    # Invoke the endpoint asynchronously to compute the data
    response = sagemaker_runtime.invoke_endpoint_async(
        EndpointName=endpoint_name,
        InputLocation=upload_location,
        ContentType='text/csv'
    )

    return response['OutputLocation'].split('/')[-1] # Return the output_file



def get_async_inference(output_file, file_format='csv', preprocess=True):
    """
    Attempts to retrieve the resulting async inference for the user trade data.

    Args:
    output_file (str): String containing the file output location obtained after request_async_inference()
    file_format (str): Inference provides us both json and csv depending on what we need

    Returns:
    pd.DataFrame: DataFrame with all HW optimal trades (or None if data not ready)
    """
    # Parameters
    bucket_name = "sagemaker-tradingmodel-us-east-1"

    # Create an s3 client for downloading the file
    s3 = boto3.client('s3',
        region_name=os.getenv('AWS_DEFAULT_REGION'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

    # Try to get the file and then convert it to a DataFrame
    # If there is an error (i.e. cannot find file or file not ready)
    # Return None
    try:
        # Retrieve the output file
        output_obj = s3.get_object(Bucket = bucket_name, Key = 'predictions/' + output_file) # Retrieve output from s3
        output_str = output_obj['Body'].read().decode('utf-8') # Decode into a string
        output_str = output_str.replace(' ', '').replace('\n', '') # Clean empty space and newline characters
        output_dict = json.loads(output_str) # Convert to a dictionary

        # Get the inference file (either csv or json)
        if file_format == 'csv':
            inference_file = output_dict['s3_output_csv_path'].split('/')[-1]
        else:
            inference_file = output_dict['s3_output_json_path'].split('/')[-1]

        # Retrieve the inference
        inference_obj = s3.get_object(Bucket = bucket_name, Key = 'predictions/' + inference_file)
        inference_str = inference_obj['Body'].read().decode('utf-8')
        inference = pd.read_csv(StringIO(inference_str))

        if preprocess:
            return preprocess_async_inference(inference)
        else:
            return inference
    
    except Exception as e:
        print('Async Model inference is not ready yet. Please wait...')
        return None
    


def preprocess_async_inference(inference):
    """
    Performs preprocessing on the async inference by keeping dates consistent, renaming columns and 
    collecting all child trades into a parent trade since it comes with all trades in one DataFrame

    Args:
    inference (DataFrame): The DataFrame output from get_async_inference()

    Returns:
    pd.DataFrame: Inference DataFrame that is prepared for metrics computation
    """
    # Rename columns
    inference = inference.rename(columns={'timestamp': 'Date',
                                'action': 'Action',
                                'shares': 'Quantity',
                                'price': 'Price',
                                'order_type': 'Order_Type',
                                'limit_price': 'Limit_Price',
                                'ticker': 'Symbol'})
    
    # Convert Date to DateTime and ensure timezone-naive
    inference['Date'] = pd.to_datetime(inference['Date']).dt.tz_localize(None).copy()

    # Collect child trades into a single parent trade in new DataFrame
    preprocessed_inference = pd.DataFrame(columns=['Date',
                                                   'Action',
                                                   'Quantity',
                                                   'Price',
                                                   'Symbol'])
    
    for trade in range(1, max(inference['counter']) + 1):
        inf_data = inference.loc[inference['counter'] == trade].reset_index()

        # Get volume weighted average execution price
        # Compute market order prices
        market_orders = inf_data.loc[inf_data['Order_Type'] == 'market']
        market_prices_sum = (market_orders['Quantity'] * market_orders['Price']).sum()

        # Compute limit order prices
        limit_orders = inf_data.loc[inf_data['Order_Type'] == 'limit']
        limit_prices_sum = (limit_orders['Quantity'] * limit_orders['Limit_Price']).sum()

        # Combine prices and take the average price per share
        price = (market_prices_sum + limit_prices_sum) / inf_data['Quantity'].sum()
        
        # Add new preprocessed parent entry
        new_entry = pd.DataFrame([[
            inf_data['Date'][0],
            inf_data['Action'][0],
            inf_data['Quantity'].sum(),
            price,
            inf_data['Symbol'][0]
        ]], columns=preprocessed_inference.columns)

        # Concat with check to avoid FutureWarning
        preprocessed_inference = pd.concat(
            [preprocessed_inference if not preprocessed_inference.empty else None, new_entry],
            ignore_index=True)
        preprocessed_inference.to_csv('test.csv')

    return preprocessed_inference



def get_realtime_inference(trade_blotter):
    """
    Retrieve the resulting inference for the user trade data using the realtime endpoint

    Args:
    output_file (str): String containing the file output location obtained after request_async_inference()

    Returns:
    pd.DataFrame: DataFrame with all HW optimal trades prepared for metrics analysis
    """
    # Parameters
    bucket_name = "sagemaker-tradingmodel-us-east-1"

    # Create an s3 client for downloading the file
    sagemaker_runtime = boto3.client(
        'sagemaker-runtime',
        region_name=os.getenv('AWS_DEFAULT_REGION'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

    # Collect all the trade inferences into one DataFrame
    preprocessed_inference = pd.DataFrame(columns=['Date',
                                                   'Action',
                                                   'Quantity',
                                                   'Price',
                                                   'Symbol'])
    for _, row in trade_blotter.iterrows():
        date = row['Date']
        action = row['Action']
        quantity = row['Quantity']
        symbol = row['Symbol']
        date_str = date.strftime('%Y-%m-%d')

        payload = {
            'end_timestamp': date_str,
            'action': action,
            'inventory': quantity,
            'ticker': symbol,
            'timeframe': 390
        }
        request_body = json.dumps(payload)

        # Retrieve the data from the endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName="MainPackage-website-endpoint", 
            Body=request_body, #bytes(request_body, 'utf-8')
            ContentType='application/json',
            )
        
        # Format the response as a dictionary of trades to be made
        response_str = response['Body'].read().decode('utf-8')
        response_dict = json.loads(response_str)
        inference = pd.DataFrame(response_dict)
        print(inference)
        if inference is not None:
            # Get volume weighted average execution price
            # Compute market order prices
            market_orders = inference.loc[inference['order_type'] == 'market']
            market_prices_sum = (market_orders['shares'] * market_orders['price']).sum()

            # Compute limit order prices
            limit_orders = inference.loc[inference['order_type'] == 'limit']
            limit_prices_sum = (limit_orders['shares'] * limit_orders['limit_price']).sum()

            # Combine prices and take the average price per share
            price = (market_prices_sum + limit_prices_sum) / inference['shares'].sum()
        else:
            price = None

        # Add new preprocessed parent entry
        new_entry = pd.DataFrame([[
            date,
            action,
            quantity,
            price,
            symbol
        ]], columns=preprocessed_inference.columns)

        # Concat with check to avoid FutureWarning
        preprocessed_inference = pd.concat(
            [preprocessed_inference if not preprocessed_inference.empty else None, new_entry],
            ignore_index=True)
    preprocessed_inference.to_csv('test.csv')

    return preprocessed_inference

# ========================================================= #
#                                                           #  
# Core Data Preprocessing                                   #
#                                                           #
# ========================================================= #

def adjust_for_splits(trade_blotter):
    """
    Adjust trade data for stock splits that occurred in the past two years.

    Args:
    trade_blotter (pd.DataFrame): DataFrame containing trade data.

    Returns:
    pd.DataFrame: DataFrame with adjusted prices and quantities for splits.
    """
    two_years_ago = datetime.now() - timedelta(days=2*365)
    symbols = trade_blotter['Symbol'].unique()

    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol)
            splits = stock.splits

            if not splits.empty:
                splits.index = splits.index.tz_localize(None)
                recent_splits = (splits[splits.index >= two_years_ago])
                
                for split_date, split_ratio in recent_splits.items():
                    # Ensure split_ratio is a number
                    if isinstance(split_ratio, (int, float)):
                        mask = (trade_blotter['Symbol'] == symbol) & (trade_blotter['Date'] < split_date)
                        
                        # ONLY adjust shares purchased not price
                        # Brokerages do not record old share prices only your purchased quantity
                        # So prices do not need to be adjusted
                        trade_blotter.loc[mask, 'Quantity'] *= split_ratio
        
        except Exception as e:
            print(f"Error adjusting for splits for symbol {symbol}: {e}")
    
    return trade_blotter



def calculate_metrics(trade_blotter, inference, data_dict):
    """
    Calculate various metrics for each trade based on historical data.

    Args:
    trade_blotter (pd.DataFrame): DataFrame containing trade data.
    inference (pd.DataFrame): Preprocessed infernece DataFrame containing model suggested orders for user trades
    data_dict (dict): Dictionary containing historical data for each symbol.

    Returns:
    pd.DataFrame: DataFrame with additional columns for calculated metrics.
    """
    
    metrics = ['Open_Price', 'Close_Price', 'TWAP_Price', 'VWAP_Price', 'HWOE_Price', 'Market Volume',
               'Volume_Rolling_Mean', 'Volatility', 'Volatility_Rolling_Mean', 'High', 'Low', 'HWOE_Day',
               'HWOE_Time', '5d_MA']
    for metric in metrics:
        trade_blotter[metric] = None

    for index, row in trade_blotter.iterrows():
        date = row['Date']
        symbol = row['Symbol']
        date_str = date.strftime('%Y-%m-%d')

        try:
            # Get both historical and inference data on this trade
            hist_data = data_dict[symbol].loc[date_str]
            inf_data = inference.iloc[index]

            # Only process this trade, if we have a historical data
            if not hist_data.empty:
                # Calculate prices for Open, Close, TWAP, and VWAP strategies
                trade_blotter.at[index, 'Open_Price'] = hist_data['Open'].iloc[0]
                trade_blotter.at[index, 'Close_Price'] = hist_data['Close'].iloc[-1]
                trade_blotter.at[index, 'TWAP_Price'] = hist_data['Close'].mean()
                trade_blotter.at[index, 'VWAP_Price'] = (hist_data['Close'] * hist_data['Volume']).sum() / hist_data['Volume'].sum()
            
                # Calculate the HWOE prices
                # Since the inference provides several optimal execution times, we volume weight the prices
                if inf_data is not None:
                    # Set HWOE execution times
                    trade_blotter.at[index, 'HWOE_Price'] = inf_data['Price']
                    trade_blotter.at[index, 'HWOE_Day'] = inf_data['Date'].strftime('%A')
                    trade_blotter.at[index, 'HWOE_Time'] = inf_data['Date'].strftime('%H:%M:%S')
                    
                # Calculate 5-day moving average and other metrics
                past_5_days_data = data_dict[symbol].loc[date - pd.Timedelta(days=5):date]
                if not past_5_days_data.empty:
                    trade_blotter.at[index, '5d_MA'] = past_5_days_data['Close'].rolling(window=5, min_periods=1).mean().iloc[-1]
                    trade_blotter.at[index, 'Volume_Rolling_Mean'] = past_5_days_data['Volume'].rolling(window=5, min_periods=1).mean().iloc[-1]
                    trade_blotter.at[index, 'Volatility'] = past_5_days_data['Close'].rolling(window=5, min_periods=1).std().iloc[-1]
                    trade_blotter.at[index, 'Volatility_Rolling_Mean'] = past_5_days_data['Close'].rolling(window=5, min_periods=1).std().rolling(window=5, min_periods=1).mean().iloc[-1]
                
                # Get the other OHLC data + volume
                trade_blotter.at[index, 'Market Volume'] = hist_data['Volume'].mean()
                trade_blotter.at[index, 'High'] = hist_data['High'].max()
                trade_blotter.at[index, 'Low'] = hist_data['Low'].min()
        
        except KeyError:
            print(f"No data found for symbol {symbol} on date {date_str}")
        except Exception as e:
            print(f"Error calculating metrics for symbol {symbol} on date {date_str}: {e}")
    
    return trade_blotter



def calculate_slippage(trade_blotter):
    """
    Calculate slippage for each trade based on various price metrics.

    Args:
    trade_blotter (pd.DataFrame): DataFrame containing trade data and calculated metrics.

    Returns:
    pd.DataFrame: DataFrame with additional columns for slippage calculations.
    """
    price_types = ['Open', 'Close', 'TWAP', 'VWAP', 'HWOE']
    
    for price_type in price_types:
        trade_blotter[f'Slippage_{price_type}'] = None
        trade_blotter[f'Slippage_PCT_{price_type}'] = None
    
    for index, row in trade_blotter.iterrows():
        action = row['Action']
        trade_price = row['Price']
        
        for price_type in price_types:
            reference_price = row[f'{price_type}_Price']
            
            if pd.notnull(reference_price):
                if action.lower() == 'buy':
                    slippage = reference_price - trade_price
                elif action.lower() == 'sell':
                    slippage = trade_price - reference_price
                else:
                    slippage = None
                
                trade_blotter.at[index, f'Slippage_{price_type}'] = slippage
                trade_blotter.at[index, f'Slippage_PCT_{price_type}'] = slippage / reference_price if reference_price != 0 else None
    
    return trade_blotter



def preprocess_data_merged(trade_blotter, inference):
    """
    Preprocess trade data by fetching historical data, calculating various metrics, and adjusting for splits.

    Args:
    trade_blotter (pd.DataFrame): DataFrame containing trade data.

    Returns:
    tuple:  1. Processed DataFrame merged with metrics and slippage data
            2. Dictionary of historical data.
            3. Error message (if applicable)
    """
    # Error message to be returned if something goes wrong
    error_message = ''

    # Remove leading/trailing spaces in 'Symbol' column
    trade_blotter['Symbol'] = trade_blotter['Symbol'].str.strip().copy()

    # Define the symbols you need to fetch data for
    symbols = trade_blotter['Symbol'].unique()
    data_dict = {}

    # Fetch and store the data for each symbol
    fund_symbols = []
    for symbol in symbols:
        # Track which symbols are funds
        if is_fund(symbol):
            fund_symbols.append(symbol)
            continue
        try:
            data = yf.Ticker(symbol).history(period='2y', interval='1h')
            if not data.empty:
                data.index = data.index.tz_localize(None) # Ensure timezone-naive datetime
                data_dict[symbol] = data
            else:
                print(f"No data found for symbol: {symbol}")
        except Exception as e:
            print(f"Error fetching data for symbol {symbol}: {e}")

    # Check if all symbols are funds
    if len(fund_symbols) == len(symbols):
        error_message = "All symbols in the trade blotter are funds. We cannot process funds at this time."
        return None, None, error_message

    # Filter out trades with symbols that couldn't fetch data
    trade_blotter = trade_blotter[trade_blotter['Symbol'].isin(data_dict.keys())]
    if trade_blotter.empty:
        error_message = "No valid trades found after filtering out funds and symbols without data."
        return None, None, error_message

    # Convert Date to DateTime and ensure timezone-naive
    trade_blotter['Date'] = pd.to_datetime(trade_blotter['Date']).dt.tz_localize(None).copy()
   
    # Adjust for stock splits
    trade_blotter = adjust_for_splits(trade_blotter)

    # Calculate metrics
    trade_blotter = calculate_metrics(trade_blotter, inference, data_dict)

    # Calculate slippage
    trade_blotter = calculate_slippage(trade_blotter)
    
    return trade_blotter, data_dict, error_message

# ========================================================= #
#                                                           #  
# Plotting Preprocessing                                  #
#                                                           #
# ========================================================= #

def preprocess_benchmark_prices(trade_details, plot_data, selected_benchmarks):
    """
    Preprocess benchmark prices for plotting.

    Args:
    trade_details (pd.Series): Series containing details of a single trade.
    plot_data (dict): Dictionary containing plot data.
    selected_benchmarks (list): List of selected benchmark types.

    Returns:
    dict: Dictionary of preprocessed benchmark prices.
    """
    plot_data = pd.DataFrame.from_dict(plot_data, orient='index')
    plot_data.index = pd.to_datetime(plot_data.index)
    
    trade_date = pd.to_datetime(trade_details['Date'])
    daily_data = plot_data[plot_data.index.date == trade_date.date()]

    benchmark_prices = {}
    if not daily_data.empty:
        if 'Open_Price' in selected_benchmarks:
            benchmark_prices['Open_Price'] = daily_data['Open'].iloc[0]
        if 'Close_Price' in selected_benchmarks:
            benchmark_prices['Close_Price'] = daily_data['Close'].iloc[-1]
        if 'TWAP_Price' in selected_benchmarks:
            benchmark_prices['TWAP_Price'] = daily_data['Close'].mean()
        if 'VWAP_Price' in selected_benchmarks:
            benchmark_prices['VWAP_Price'] = (daily_data['Close'] * daily_data['Volume']).sum() / daily_data['Volume'].sum()
        if 'HWOE_Price' in selected_benchmarks:
            if trade_details['Action'].lower() == 'buy':
                benchmark_prices['HWOE_Price'] = daily_data['Close'].min()
            elif trade_details['Action'].lower() == 'sell':
                benchmark_prices['HWOE_Price'] = daily_data['Open'].max()

    return benchmark_prices

# ========================================================= #
#                                                           #  
# Brokerage Specific Preprocessing                          #
#                                                           #
# ========================================================= #

def process_robinhood(trade_blotter):
    """
    Process Robinhood trade data.

    Args:
    trade_blotter (pd.DataFrame): DataFrame containing Robinhood trade data.

    Returns:
    pd.DataFrame: Processed DataFrame.
    """
    trade_blotter = check_date_threshold(trade_blotter)
    trade_blotter.dropna(subset=['Date', 'Action', 'Symbol'], inplace=True)
    return trade_blotter[trade_blotter['Action'].str.contains('buy|sell', case=False, regex=True)]



def process_cs(trade_blotter):
    """
    Process Charles Schwab trade data.

    Args:
    trade_blotter (pd.DataFrame): DataFrame containing Charles Schwab trade data.

    Returns:
    pd.DataFrame: Processed DataFrame.
    """
    trade_blotter.rename(columns={
        'Date': 'Date',
        'Action': 'Action',
        'Symbol': 'Symbol'
    }, inplace=True)
    
    trade_blotter = check_date_threshold(trade_blotter)
    trade_blotter.dropna(subset=['Date', 'Action', 'Symbol'], inplace=True)
    return trade_blotter[trade_blotter['Action'].str.contains('buy|sell', case=False, regex=True)]



def process_webull(trade_blotter):
    """
    Process Webull trade data.

    Args:
    trade_blotter (pd.DataFrame): DataFrame containing Webull trade data.

    Returns:
    pd.DataFrame: Processed DataFrame.
    """
    trade_blotter.rename(columns={
        'Date': 'Date',
        'Action': 'Action',
        'Symbol': 'Symbol'
    }, inplace=True)
    
    trade_blotter = check_date_threshold(trade_blotter)
    trade_blotter.dropna(subset=['Date', 'Action', 'Symbol'], inplace=True)
    return trade_blotter[trade_blotter['Action'].str.contains('buy|sell', case=False, regex=True)]



def process_plaid(trade_blotter):
    """
    Process Plaid trade data.

    Args:
    trade_blotter (pd.DataFrame): DataFrame containing Plaid trade data.

    Returns:
    pd.DataFrame: Processed DataFrame.
    """
    trade_blotter.rename(columns={
        'date': 'Date',
        'type': 'Action',
        'ticker_symbol': 'Symbol',
        'quantity': 'Quantity',
        'price': 'Price'
    }, inplace=True)
    trade_blotter['Quantity'] = pd.to_numeric(trade_blotter['Quantity'], errors='coerce')
    trade_blotter['Quantity'] = trade_blotter['Quantity'].abs()
    trade_blotter = trade_blotter.dropna(subset=['Date', 'Action', 'Symbol'])
    return trade_blotter[trade_blotter['Action'].str.contains('buy|sell', case=False, regex=True)]



def preprocess_by_platform(trade_blotter, platform_type):
    """
    Preprocess trade data based on the platform type.

    Args:
    trade_blotter (pd.DataFrame): DataFrame containing trade data.
    platform_type (str): Type of trading platform.

    Returns:
    pd.DataFrame: Processed DataFrame.

    Raises:
    ValueError: If an invalid platform type is provided.
    """
    # Preprocess by platform
    if platform_type == 'Robinhood':
        trade_blotter = process_robinhood(trade_blotter)
    elif platform_type == 'Charles Schwab':
        trade_blotter = process_cs(trade_blotter)
    elif platform_type == 'Webull':
        trade_blotter = process_webull(trade_blotter)
    elif platform_type == 'Plaid':
        trade_blotter = process_plaid(trade_blotter)
    else:
        raise ValueError("Invalid platform type")
    
    # Remove all irrelevant information that the brokerages add
    trade_blotter = trade_blotter[['Date', 'Action', 'Symbol', 'Quantity', 'Price']]
    
    # Convert Date to DateTime and ensure timezone-naive
    trade_blotter['Date'] = pd.to_datetime(trade_blotter['Date']).dt.tz_localize(None).copy()

    # Keep only data from last 2 years
    two_years_ago = pd.to_datetime('today') - pd.DateOffset(years=2)
    trade_blotter = trade_blotter[trade_blotter['Date'] >= two_years_ago]
    
    return trade_blotter
