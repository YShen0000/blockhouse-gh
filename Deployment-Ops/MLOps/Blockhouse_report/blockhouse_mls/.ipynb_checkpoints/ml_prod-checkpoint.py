"""
BlockHouse ML Production
"""
from datetime import datetime, timedelta
import pytz
from pandas.tseries.holiday import USFederalHolidayCalendar
from blockhouse_mls.equities.sell.inference import EquitiesSellInference
from blockhouse_mls.equities.buy.inference import EquitiesBuyInference

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


# def run_equities_sell_inference(ticker, start_timestamp = (datetime.now(pytz.UTC) - timedelta(days=2)).strftime('%Y-%m-%d'), end_timestamp=datetime.now(pytz.UTC).strftime('%Y-%m-%d'), timeframe=90, inventory=10000, trade_set_counter=1):
#     return equities_sell_inference.run_pipeline(ticker, start_timestamp = start_timestamp, end_timestamp=end_timestamp, timeframe=timeframe, inventory=inventory, trade_set_counter=trade_set_counter)


# def run_equities_buy_inference(ticker, start_timestamp = (datetime.now(pytz.UTC) - timedelta(days=2)).strftime('%Y-%m-%d'), end_timestamp=datetime.now(pytz.UTC).strftime('%Y-%m-%d').strftime('%Y-%m-%d'), timeframe=90, inventory=10000, trade_set_counter=1):
#     return equities_buy_inference.run_pipeline(ticker, start_timestamp =start_timestamp, end_timestamp=end_timestamp, timeframe=timeframe, inventory = inventory, trade_set_counter=trade_set_counter)


def adjust_for_weekends_and_holidays(date):
    """
    Adjust the given date if it falls on a weekend (Saturday or Sunday)
    or a U.S. federal holiday. Moves it back to the previous business day.
    """
    # Check if the date is Saturday (5) or Sunday (6)
    while date.weekday() > 4:  # Saturday (5) or Sunday (6)
        date -= timedelta(days=1)  # Move to the previous day

    # Check if the date is a U.S. federal holiday
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start=date - timedelta(days=365), end=date + timedelta(days=365))

    # If the date is a holiday, move to the previous business day
    while date in holidays:
        date -= timedelta(days=1)

    return date

def run_equities_inference(ticker,  action = 'buy'):
    
    utc = pytz.UTC
    timeframe=390
    inventory=1

    end_timestamp = datetime.now(utc) - timedelta(days=2)
    end_timestamp = adjust_for_weekends_and_holidays(end_timestamp)  # Adjust for weekends and holidays

    # Ensure a 2-day gap between start and end timestamps
    start_timestamp = end_timestamp - timedelta(days=2)
    start_timestamp = adjust_for_weekends_and_holidays(start_timestamp)  # Adjust for weekends and holidays

    # Format timestamps as strings
    start_timestamp_str = start_timestamp.strftime('%Y-%m-%d')
    end_timestamp_str = end_timestamp.strftime('%Y-%m-%d')
    print(start_timestamp_str)
    print(end_timestamp_str)
    if action == 'sell':
        return equities_sell_inference.run_pipeline(ticker, start_timestamp = start_timestamp_str, end_timestamp=end_timestamp_str, timeframe=timeframe, inventory=inventory, trade_set_counter=1)
    
    if action == 'buy':
        return equities_buy_inference.run_pipeline(ticker, start_timestamp = start_timestamp_str , end_timestamp=end_timestamp_str, timeframe=timeframe, inventory=inventory, trade_set_counter=1)