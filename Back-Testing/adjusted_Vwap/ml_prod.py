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

from test_model.model import infer_model

def run_equities_sell_inference(ticker, day_of_backtest, timeframe=390, inventory=10000, data=None, trade_set_counter=1):

    trades = infer_model(side="sell", timeframe=timeframe, inventory=inventory, ticker=ticker, end_timestamp=day_of_backtest, backtest=True) # equities_sell_inference.run_pipeline(ticker, start_timestamp, end_timestamp, timeframe, inventory, trade_set_counter)
    trades['timestamp'] = trades['timestamp'].dt.tz_convert(None) # Remove timezone from timestamp data
    return trades

def run_equities_buy_inference(ticker, day_of_backtest, timeframe=390, inventory=10000, data=None, trade_set_counter=1):
    # # Assuming input day_of_backtest to be in 'YYYY-MM-DD'
    # end_timestamp = datetime.strptime(day_of_backtest, '%Y-%m-%d')
    # # Set end inference to day before backtest
    # end_timestamp = end_timestamp - timedelta(days=1) 
    # # Set start inference to 3 days before end inference, and convert to string
    # start_timestamp = (end_timestamp - timedelta(days=3)).strftime('%Y-%m-%d') # CHANGED FROM 7 TO 3
    # end_timestamp = end_timestamp.strftime('%Y-%m-%d') # Convert back to string
    trades = infer_model(side="buy", timeframe=timeframe, inventory=inventory, ticker=ticker, end_timestamp=day_of_backtest, backtest=True) #equities_buy_inference.run_pipeline(ticker, start_timestamp, end_timestamp, timeframe, inventory, trade_set_counter)
    trades['timestamp'] = trades['timestamp'].dt.tz_convert(None) # Remove timezone from timestamp data
    return trades