import pandas as pd
import numpy as np
import logging
import streamlit as st
import os
import boto3
import json
import time
import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_model_strategy(ticker, action, inventory, timeframe, timestamp):
    #logger.debug("Entering get_model_strategy function")
    payload = {
        "ticker": ticker,
        "action": action.lower(),
        "inventory": inventory,
        "timeframe": timeframe,
        "Timestamp": timestamp.strftime('%Y-%m-%d')
    }
    logger.debug(f"Payload for SageMaker endpoint: {payload}")

    request_body = json.dumps(payload)

    # Create a low-level client representing Amazon SageMaker Runtime
    try:
        #sagemaker_runtime = boto3.client("sagemaker-runtime", region_name='us-east-1')
        # Create a low-level client representing Amazon SageMaker Runtime
        sagemaker_runtime = boto3.client(
            "sagemaker-runtime",
            region_name='us-east-1',
            # credentials resolved by boto3 from the environment (env vars / ~/.aws / IAM role)
        )
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.error("AWS credentials not found.")
        st.error("AWS credentials not found. Please configure your AWS credentials.")
        return None

    # Endpoint name (replace with your actual endpoint name)
    endpoint_name = "endpoint-real-time-inference24-HW-R"
    #logger.debug(f"Invoking SageMaker endpoint: {endpoint_name}")

    try:
        # Invoke the endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            Body=request_body,
            ContentType='application/json',
            InferenceComponentName="model-real-time-inference24-HW-R-inference-component"
        )
        # Read and decode the response
        result = response['Body'].read().decode('utf-8')
        strategy = json.loads(result)
        logger.debug(f"Received strategy from endpoint: {strategy}")
        return strategy
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.error("AWS credentials not found.")
        st.error("AWS credentials not found. Please configure your AWS credentials.")
        return None
    except Exception as e:
        logger.error(f"Error invoking SageMaker endpoint: {e}", exc_info=True)
        st.error(f"Error invoking SageMaker endpoint: {e}")
        return None



def pull_data(ticker, date):
    logger.debug(f"Pulling data for {ticker} on {date.strftime('%Y-%m-%d')}")
    api_key = 'r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc'  # Replace with your Polygon.io API key
    start_date = date.strftime('%Y-%m-%d')
    end_date = start_date  # Single day data

    try:
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{start_date}/{end_date}"
        params = {"apiKey": api_key, "limit": 50000}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if 'results' not in data or len(data['results']) == 0:
            st.error(f"No OHLCV data found for {ticker} on {start_date}.")
            logger.error(f"No OHLCV data found for {ticker} on {start_date}.")
            return None

        # Convert results to DataFrame
        ohlcv_data = pd.DataFrame(data['results'])
        ohlcv_data['datetime'] = pd.to_datetime(ohlcv_data['t'], unit='ms')
        ohlcv_data.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
        ohlcv_data = ohlcv_data[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        ohlcv_data['mid_price'] = (ohlcv_data['open'] + ohlcv_data['close']) / 2  # Calculate mid-price
        ohlcv_data.sort_values('datetime', inplace=True)
        ohlcv_data.reset_index(drop=True, inplace=True)
        logger.debug(f"Fetched {len(ohlcv_data)} OHLCV data points")
        return ohlcv_data

    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}")
        logger.error(f"HTTP error occurred: {http_err}")
    except Exception as e:
        st.error(f"An error occurred: {e}")
        logger.error(f"An error occurred while fetching data: {e}")

    return None



def generate_twap_strategy(inventory, num_of_orders, ohlcv_data):
    logger.debug("Generating TWAP strategy")
    intervals = num_of_orders
    volume_per_interval = inventory // intervals
    remaining_volume = inventory % intervals

    # Select equally spaced times from the OHLCV data
    total_data_points = len(ohlcv_data)
    step = max(total_data_points // intervals, 1)
    selected_indices = [i * step for i in range(intervals)]
    if selected_indices[-1] >= total_data_points:
        selected_indices[-1] = total_data_points - 1  # Ensure index is within range

    twap_schedule = []
    for idx, i in enumerate(selected_indices):
        volume = volume_per_interval + (1 if idx < remaining_volume else 0)
        order_datetime = ohlcv_data.iloc[i]['datetime']
        twap_schedule.append({
            'step': idx,
            'timestamp': order_datetime,
            'order_type': 'Market',
            'volume': volume
        })
    #logger.debug(f"TWAP schedule: {twap_schedule}")
    return twap_schedule



def generate_vwap_strategy(inventory, ohlcv_data):
    logger.debug("Generating VWAP strategy")
    # Calculate total volume for the day
    total_volume = ohlcv_data['volume'].sum()
    ohlcv_data['proportion'] = ohlcv_data['volume'] / total_volume
    ohlcv_data['order_volume'] = (ohlcv_data['proportion'] * inventory).astype(int)

    vwap_schedule = []
    for i, row in ohlcv_data.iterrows():
        if row['order_volume'] > 0:
            vwap_schedule.append({
                'step': i,
                'timestamp': row['datetime'],
                'order_type': 'Market',
                'volume': row['order_volume']
            })
    #logger.debug(f"VWAP schedule: {vwap_schedule}")
    return vwap_schedule



def calculate_slippage(strategy, ohlcv_data, action, is_model_strategy=False):
    #logger.debug(f"Calculating slippage for {action} orders")
    total_slippage = 0.0
    for order in strategy:
        # Parse the order timestamp
        order_datetime = pd.to_datetime(order['timestamp'])

        # Find the closest price in the data
        idx = ohlcv_data['datetime'].sub(order_datetime).abs().idxmin()
        market_data = ohlcv_data.iloc[idx]
        mid_price = market_data['mid_price']
        open_price = market_data['open']
        close_price = market_data['close']

        # For TWAP and VWAP strategies
        if not is_model_strategy:
            execution_price = open_price  # Execution price is the open price
            actual_price = mid_price       # Actual price is the mid-price
        else:
            # For Model Strategy
            execution_price = order['limit_price']  # Execution price from model endpoint
            actual_price = mid_price
            logger.debug(f" ===== Order prices for model strat: execution price {execution_price}, actual price: {actual_price}, timestep market data {market_data}")

        # Calculate slippage
        slippage_per_share = execution_price - actual_price if action.lower() == 'buy' else actual_price - execution_price
        total_slippage += slippage_per_share * order['volume']

        logger.debug(f"Order: {order}")
        logger.debug(f"Execution price: {execution_price}, Actual price: {actual_price}, Slippage per share: {slippage_per_share}")

    logger.debug(f"Total slippage: {total_slippage}")
    return total_slippage



def plot_slippage(slippages, strategies):
    strategy_names = strategies
    plt.figure(figsize=(8, 6))
    plt.bar(strategy_names, slippages, color=['blue', 'orange', 'green'])
    plt.xlabel('Trading Strategy')
    plt.ylabel('Total Slippage (USD)')
    plt.title('Slippage Comparison of Trading Strategies')
    plt.grid(True)
    st.pyplot(plt)



def main():
    st.title("Transaction Cost Savings Calculator")

    # User Inputs
    user_asset_class = st.selectbox('Asset Class', ['Equities'])  # For now, only 'Equities' is allowed
    ticker = st.text_input('Ticker Symbol', 'AAPL')
    action = st.selectbox('Action', ['Buy', 'Sell'])
    inventory = st.number_input('Inventory (Number of Shares)', min_value=1, value=5000)
    timestamp = st.date_input('Trade Date', datetime.today())
    timeframe = 390  # Fixed for now; you can make this an input if needed
    num_of_orders = st.number_input('Number of Orders', min_value=1, value=8)

    if st.button('Calculate'):
        try:
            logger.debug("Starting calculation")
            # Fetch OHLCV Data
            ohlcv_data = pull_data(ticker, timestamp)
            if ohlcv_data is None:
                logger.error("OHLCV data is None")
                return  # Exit if data is not available

            # Get Model Strategy
            model_strategy = get_model_strategy(ticker, action, inventory, timeframe, timestamp)
            if model_strategy is None:
                logger.error("Model strategy is None")
                return  # Exit if model strategy is not available

            # Generate TWAP Strategy
            twap_strategy = generate_twap_strategy(inventory, num_of_orders, ohlcv_data)

            # Generate VWAP Strategy
            vwap_strategy = generate_vwap_strategy(inventory, ohlcv_data)

            # Calculate Slippage for Each Strategy
            model_slippage = calculate_slippage(model_strategy, ohlcv_data, action, is_model_strategy=True)
            twap_slippage = calculate_slippage(twap_strategy, ohlcv_data, action)
            vwap_slippage = calculate_slippage(vwap_strategy, ohlcv_data, action)

            # Display Results
            st.subheader("Slippage Comparison")
            st.write(f"**Model Strategy Slippage:** ${model_slippage:,.2f}")
            st.write(f"**TWAP Strategy Slippage:** ${twap_slippage:,.2f}")
            st.write(f"**VWAP Strategy Slippage:** ${vwap_slippage:,.2f}")

            # Plot the Results
            slippages = [model_slippage, twap_slippage, vwap_slippage]
            plot_slippage(slippages, ['Model', 'TWAP', 'VWAP'])

        except Exception as e:
            logger.error(f"An error occurred during calculation: {e}", exc_info=True)
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
