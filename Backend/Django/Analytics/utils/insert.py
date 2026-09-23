from Analytics.models import Trade, Market_Prices
from Analytics.utils.timestamp_converter import convert_to_datetime
from datetime import datetime
import pandas as pd

def insert_trade():
    trade = Trade(
        cusip='912810SZ41',
        trade_date=datetime.strptime('2024-01-02', '%Y-%m-%d').date(),
        trade_time=datetime.strptime('09:44', '%H:%M').time(),
        trade_size=855670,
        face_value=100,
        asset_inventory=99144330,
        fill=1,
        execution_time=3,
        trade_price=941.857262828174,
        trade_direction='BUY',
        counterparty='Benjie',
        trader='Benjie Trader 2'
    )
    trade.save()

def insert_market_data(path):
    market_df = pd.read_csv(path)

    market_prices_list = [
        Market_Prices(
            cusip=row['CUSIP'],
            trade_timestamp=convert_to_datetime(row['Date'], row['Time']),
            trade_price=row['Price']
        ) for index, row in market_df.iterrows()
    ]

    Market_Prices.objects.bulk_create(market_prices_list)

def clear_all_market_prices():
    Market_Prices.objects.all().delete()