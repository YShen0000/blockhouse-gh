"""
BlockHouse ML Production
"""
from datetime import datetime, timedelta
import pytz

from blockhouse_ml.equities.sell.inference import EquitiesSellInference
from blockhouse_ml.equities.buy.inference import EquitiesBuyInference

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


def run_equities_sell_inference(ticker, start_timestamp = (datetime.now(pytz.UTC) - timedelta(days=2)).strftime('%Y-%m-%d'), end_timestamp=datetime.now(pytz.UTC).strftime('%Y-%m-%d'), timeframe=90, inventory=10000, trade_set_counter=1):
    return equities_sell_inference.run_pipeline(ticker, start_timestamp = start_timestamp, end_timestamp=end_timestamp, timeframe=timeframe, inventory=inventory, trade_set_counter=trade_set_counter)


def run_equities_buy_inference(ticker, start_timestamp = (datetime.now(pytz.UTC) - timedelta(days=2)).strftime('%Y-%m-%d'), end_timestamp=datetime.now(pytz.UTC).strftime('%Y-%m-%d'), timeframe=390, inventory=10000, trade_set_counter=1):
    return equities_buy_inference.run_pipeline(ticker, start_timestamp =start_timestamp, end_timestamp=end_timestamp, timeframe=timeframe, inventory = inventory, trade_set_counter=1)


def run_equities_inference(ticker, start_timestamp = (datetime.now(pytz.UTC) - timedelta(days=2)).strftime('%Y-%m-%d'), end_timestamp=datetime.now(pytz.UTC).strftime('%Y-%m-%d'), timeframe=390, inventory=10000, trade_set_counter=1, action = 'buy'):
    if action == 'sell':
        return equities_sell_inference.run_pipeline(ticker, start_timestamp = start_timestamp, end_timestamp=end_timestamp, timeframe=timeframe, inventory=inventory, trade_set_counter=trade_set_counter)
    
    if action == 'buy':
        return equities_buy_inference.run_pipeline(ticker, start_timestamp =start_timestamp, end_timestamp=end_timestamp, timeframe=timeframe, inventory = inventory, trade_set_counter=1)