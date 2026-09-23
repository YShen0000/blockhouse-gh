"""
BlockHouse ML Production
"""
from datetime import datetime, timedelta
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


def run_equities_sell_inference(ticker, start_timestamp = (datetime.today() - timedelta(days=2)).strftime('%Y-%m-%d'), end_timestamp=datetime.today().strftime('%Y-%m-%d'), timeframe=390, inventory=10000, trade_set_counter=1):
    return equities_sell_inference.run_pipeline(ticker, start_timestamp = start_timestamp, end_timestamp=end_timestamp, timeframe=timeframe, inventory=inventory, trade_set_counter=trade_set_counter)


def run_equities_buy_inference(ticker, start_timestamp = (datetime.today() - timedelta(days=20)).strftime('%Y-%m-%d'), end_timestamp=(datetime.today() - timedelta(days=15)).strftime('%Y-%m-%d'), timeframe=390, inventory=10000, trade_set_counter=1):
    return equities_buy_inference.run_pipeline(ticker, start_timestamp = (datetime.today() - timedelta(days=5)).strftime('%Y-%m-%d'), end_timestamp=(datetime.today() - timedelta(days=3)).strftime('%Y-%m-%d'), timeframe=390, inventory=10000, trade_set_counter=1)