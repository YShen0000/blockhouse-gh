"""
BlockHouse ML Production
"""
from datetime import datetime, timedelta
# import pytz
from sklearn.linear_model import Ridge
import pandas as pd
import numpy as np
import os
from stable_baselines3 import SAC
# from test_model.model import Model
from test_model.data_handler import DataProcessor

# from test_model.inference import EquityInference
from stable_baselines3 import PPO
from test_model.macro_model_utils import MacroTraderModel
from test_model.data_handler import InferenceDataHandler
from test_model import fetch_merge_data
# import dataframe_image as dfi
# import blockhouse_ml.equities.sell.benchmark_utils as benchmarks
# from collections import defaultdict

# from sklearn import preprocessing
from sklearn.linear_model import LinearRegression
from test_model.data_handler_v2 import process_data, fetch_data
# ## create data dir and data handler
# data_dir = 'Data'
# os.makedirs(data_dir, exist_ok=True)

# data_handler = DataHandler(data_dir)

# # Create model directory and logging directory
# model_dir = 'Models'
# os.makedirs(model_dir, exist_ok=True)
# logging_dir = 'logs'

# n_env = 1
# sac_model = Model(model_dir=model_dir, logging_dir=logging_dir,n_env=n_env)


# equity_inference = EquityInference(data_dir='Data', model_dir='Model', logging_dir='logs', n_env=1)
def get_data(data_dir, ticker, start_time, end_time):
    data_processor = DataProcessor()
    # Define the forecast steps
    forecast_steps = {
        'open': (360, '1T'),
        'high': (360, '1T'),
        'low': (360, '1T'),
        'close': (360, '1T'),
        'volatility': (360, '1T'),
        'volume': (360, '1T'),
        'transaction_cost': (360, '1T')
    }

    ## Fetch and process the data and save it to the data directory, if it doesn't exist
    filename = f'{data_dir}/merged_data_{ticker}_{start_time}_{end_time}.csv'
    if os.path.exists(filename):
        data = pd.read_csv(filename)
    else:
        data = fetch_merge_data.fetch_and_merge_data(ticker, start_date=start_time, end_date=end_time,
                                                     save_dir=data_dir)

    processed_filename = f'{data_dir}/processed_data_{ticker}_{start_time}_{end_time}.csv'

    if os.path.exists(processed_filename):
        processed_data = pd.read_csv(processed_filename)
    else:
        processed_data = data_processor.process_data(data, forecast_steps, n_jobs=4)
        processed_data.to_csv(processed_filename)

    return processed_data

# Set up your model pipeline here
def get_enchanced_vwap_trades(data, initial_inventory, preferred_timeframe):
    total_steps = len(data)
    remaining_inventory = initial_inventory
    trades = []
    
    # Iterate through each minute of the trading day (or until inventory is zero)
    for step in range(min(total_steps, preferred_timeframe)):
        # Slice the data from the market open to the current step
        current_data = data.iloc[:step + 1]
        
        # Forecasting using Linear Regression for remaining data
        if step < total_steps - 1:  # Only forecast if we are not at the end of data
            # future_steps = total_steps - step - 1
            time_steps = np.arange(step + 1).reshape(-1, 1)  # Time steps for current data
            
            # Prepare volume data for linear regression
            current_volumes = current_data['volume'].values.reshape(-1, 1)
            future_time_steps = np.arange(step + 1, total_steps).reshape(-1, 1)
            
            # Fit a linear regression model on current data and forecast future volumes
            volume_model = Ridge(positive=True) # LinearRegression()
            volume_model.fit(time_steps, current_volumes)
            forecasted_volumes = volume_model.predict(future_time_steps)
            
            # Sum the forecasted volumes to estimate the total volume for the rest of the day
            total_forecasted_volume = np.sum(forecasted_volumes)
            
            # Update total volume to include forecasted future volume
            total_volume = current_volumes.sum() + total_forecasted_volume
        else:
            # No forecast needed at final timestep of day
            total_volume = data['volume'].sum()
        
        # Calculate size of slice for the current step
        volume_at_step = data['volume'].iloc[step]
        size_of_slice = (volume_at_step / total_volume) * initial_inventory
        size_of_slice = min(size_of_slice, remaining_inventory)
        
        # Subtract the traded shares from the remaining inventory
        remaining_inventory -= int(np.ceil(size_of_slice))
        
        # Record the trade
        trade = {
            'step': step,
            'timestamp': data.iloc[step]['datetime'],  # Added time of trade
            'price': data.iloc[step]['close'],
            'shares': size_of_slice,
            'inventory': remaining_inventory,
            'action': (1, 1),  # 1 indicates 1 step taken, another 1 is useless
        }
        trades.append(trade)
        
        # Break the loop if all inventory is sold
        if remaining_inventory <= 0:
            break
    
    return pd.DataFrame(trades)

# def run_equities_sell_inference(ticker, day_of_backtest, timeframe=390, inventory=10000, data=None, trade_set_counter=1):
#     # Assuming input day_of_backtest to be in 'YYYY-MM-DD'
#     end_timestamp = datetime.strptime(day_of_backtest, '%Y-%m-%d')
#     # Set end inference to day before backtest
#     end_timestamp = end_timestamp - timedelta(days=1) 
#     # Set start inference to 3 days before end inference, and convert to string
#     start_timestamp = (end_timestamp - timedelta(days=3)).strftime('%Y-%m-%d') # CHANGED FROM 7 TO 3
#     end_timestamp = end_timestamp.strftime('%Y-%m-%d') # Convert back to string
    
#     return get_enchanced_vwap_trades(data, inventory, timeframe) # equities_sell_inference.run_pipeline(ticker, start_timestamp, end_timestamp, timeframe, inventory, trade_set_counter)

def classify_market_cap(market_cap_value):
    if market_cap_value < 2e9:
        return "small"
    elif market_cap_value < 10e9:
        return "medium"
    else:
        return "large"

def classify_scenario(inventory):
    if inventory < 100:
        return "small"
    elif inventory < 1000:
        return "medium"
    else:
        return "large"

def run_equities_sell_inference(ticker, day_of_backtest, timeframe=390, inventory=10000, bt_data=None, trade_set_counter=1, market_cap_value=None):
    # Initialize MacroTraderModel
    MODEL_DIR = 'test_model'
    macro_trader = MacroTraderModel(MODEL_DIR)
    
    # Set up dates
    start_date = end_date = day_of_backtest
    
    # Classify market cap and scenario
    market_cap = classify_market_cap(market_cap_value) if market_cap_value is not None else "large"
    scenario = classify_scenario(inventory)
    
    # Fetch and process data
    data_dir = "Data"
    data_filepath = fetch_data(ticker=ticker, start_date=start_date, end_date=end_date, data_dir=data_dir)
    
    data = pd.read_csv(data_filepath)
    data.dropna(inplace=True)
    data.set_index("timestamp", inplace=True)
    
    processed_test_data = process_data(data, name=ticker, cols=data.columns, train=False)
    
    # Load the model
    model_path = os.path.join(MODEL_DIR, 'dense_reward_model.zip')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    model = SAC.load(model_path)
    print(f"Loaded model from: {model_path}")
    
    # Get processed data
    processed_data = get_data(data_dir, ticker, start_date, end_date)
    
    # Run the inference
    rew, tenv, _, infos = macro_trader.test_benchmark(
        processed_data,
        processed_data,
        processed_test_data,
        preferred_timeframe=timeframe,
        market_cap=market_cap,
        scenario=scenario,
        get_tab_transformer=False,
        model=model
    )
    
    # Extract trades and format them as required
    if hasattr(tenv, 'trades'):
        trades = pd.DataFrame(tenv.trades)
        
        # Convert step to datetime
        start_time = datetime.strptime(f"{day_of_backtest} 13:30:00", "%Y-%m-%d %H:%M:%S")
        trades['timestamp'] = trades['step'].apply(lambda x: (start_time + timedelta(minutes=x)).strftime("%Y-%m-%d %H:%M:%S"))
        
        # Rename and reorder columns
        trades = trades.rename(columns={'price': 'price', 'shares': 'shares'})
        trades['action'] = [(1, 1)] * len(trades)  # Set all actions to (1, 1)
        
        # Select and order the required columns
        trades = trades[['step', 'timestamp', 'price', 'shares', 'inventory', 'action']]
    else:
        trades = pd.DataFrame(columns=['step', 'timestamp', 'price', 'shares', 'inventory', 'action'])
    
    print(f"Testing on {ticker}")
    print(f"Market Cap: {market_cap}")
    print(f"Scenario: {scenario}")
    print("Cumulative Reward:", rew)
    print("Number of trades:", len(trades))
    
    if len(infos) > 0:
        out = pd.DataFrame(infos)
        if 'IS' in out.columns:
            print("Agent slippage:", out['IS'].sum())
        else:
            print("Warning: 'IS' column not found in infos.")
    
    return trades

# trades = run_equities_sell_inference('AAPL', '2024-10-10', timeframe=390, inventory=10000, market_cap_value=2e12)
# print(trades)
def run_equities_buy_inference(ticker, day_of_backtest, timeframe=390, inventory=10000, data=None, trade_set_counter=1):
    # Assuming input day_of_backtest to be in 'YYYY-MM-DD'
    end_timestamp = datetime.strptime(day_of_backtest, '%Y-%m-%d')
    # Set end inference to day before backtest
    end_timestamp = end_timestamp - timedelta(days=1) 
    # Set start inference to 3 days before end inference, and convert to string
    start_timestamp = (end_timestamp - timedelta(days=3)).strftime('%Y-%m-%d') # CHANGED FROM 7 TO 3
    end_timestamp = end_timestamp.strftime('%Y-%m-%d') # Convert back to string

    return get_enchanced_vwap_trades(data, inventory, timeframe) #equities_buy_inference.run_pipeline(ticker, start_timestamp, end_timestamp, timeframe, inventory, trade_set_counter)

# Example usage:
# trades = run_equities_buy_inference('AAPL', '2024-09-09', timeframe=390, inventory=10000)
# print(trades)