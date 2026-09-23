"""
BlockHouse ML Production
"""
from datetime import datetime, timedelta
# import pytz
from sklearn.linear_model import Ridge
import pandas as pd
from blockhouse_ml.equities.sell.inference import EquitiesSellInference
from blockhouse_ml.equities.buy.inference import EquitiesBuyInference
import numpy as np

equities_sell_inference = EquitiesSellInference(
    macro_model_dir = 'SellEquityModels',
    micro_model_dir='MicroSellEquityModels',
    data_dir = 'SellEquityData'
)

equities_buy_inference = EquitiesBuyInference(
    macro_model_dir = 'BuyEquityModels',
    micro_model_dir='MicroBuyEquityModels',
    data_dir = 'BuyEquityData'
)

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

def run_equities_sell_inference(ticker, day_of_backtest, timeframe=390, inventory=10000, data=None, trade_set_counter=1):
    # Assuming input day_of_backtest to be in 'YYYY-MM-DD'
    end_timestamp = datetime.strptime(day_of_backtest, '%Y-%m-%d')
    # Set end inference to day before backtest
    end_timestamp = end_timestamp - timedelta(days=1) 
    # Set start inference to 3 days before end inference, and convert to string
    start_timestamp = (end_timestamp - timedelta(days=3)).strftime('%Y-%m-%d') # CHANGED FROM 7 TO 3
    end_timestamp = end_timestamp.strftime('%Y-%m-%d') # Convert back to string
    
    return get_enchanced_vwap_trades(data, inventory, timeframe) # equities_sell_inference.run_pipeline(ticker, start_timestamp, end_timestamp, timeframe, inventory, trade_set_counter)

def run_equities_buy_inference(ticker, day_of_backtest, timeframe=390, inventory=10000, data=None, trade_set_counter=1):
    # Assuming input day_of_backtest to be in 'YYYY-MM-DD'
    end_timestamp = datetime.strptime(day_of_backtest, '%Y-%m-%d')
    # Set end inference to day before backtest
    end_timestamp = end_timestamp - timedelta(days=1) 
    # Set start inference to 3 days before end inference, and convert to string
    start_timestamp = (end_timestamp - timedelta(days=3)).strftime('%Y-%m-%d') # CHANGED FROM 7 TO 3
    end_timestamp = end_timestamp.strftime('%Y-%m-%d') # Convert back to string

    return get_enchanced_vwap_trades(data, inventory, timeframe) #equities_buy_inference.run_pipeline(ticker, start_timestamp, end_timestamp, timeframe, inventory, trade_set_counter)