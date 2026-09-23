
from django.http import JsonResponse

import json
import logging
import numpy as np
import pandas as pd

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from Analytics.utils.fetch_data import fetch_trade_data, fetch_market_data

logger = logging.getLogger(__name__)

def calculate_benchmarks(market_data, trades_data, benchmark):
    benchmarks = {}
    if benchmark == 'LAST_PRICE':
        last_price = market_data.sort_values('trade_timestamp', ascending=False).iloc[0]
        benchmarks['Last Price'] = float(last_price['trade_price']) if not market_data.empty else None
        benchmarks['Bid'] = float(last_price['bid']) if not market_data.empty else None
        benchmarks['Ask'] = float(last_price['ask']) if not market_data.empty else None
    elif benchmark == 'TWAP':
        twap = trades_data['trade_price'].astype(float).mean()
        bid_twap = market_data['bid'].astype(float).mean()
        ask_twap = market_data['ask'].astype(float).mean()
        benchmarks['TWAP'] = twap
        benchmarks['Bid'] = bid_twap
        benchmarks['Ask'] = ask_twap
    elif benchmark == 'VWAP':
        trades_data['trade_price'] = trades_data['trade_price'].apply(float)
        trades_data['volume'] = trades_data['volume'].apply(float)
        market_data['bid'] = market_data['bid'].apply(float)
        market_data['ask'] = market_data['ask'].apply(float)
        
        vwap = (trades_data['trade_price'] * trades_data['volume']).sum() / trades_data['volume'].sum()
        bid_vwap = (market_data['bid'] * trades_data['volume']).sum() / trades_data['volume'].sum()
        ask_vwap = (market_data['ask'] * trades_data['volume']).sum() / trades_data['volume'].sum()
        
        benchmarks['VWAP'] = vwap
        benchmarks['Bid'] = bid_vwap
        benchmarks['Ask'] = ask_vwap
    return benchmarks

def calculate_notional_values(trades_data):
    trades_data['trade_price'] = trades_data['trade_price'].astype(float)
    trades_data['trade_size'] = trades_data['trade_size'].astype(float)
    
    buy_trades = trades_data[(trades_data['trade_direction'] == 'BUY')]
    sell_trades = trades_data[(trades_data['trade_direction'] == 'SELL')]

    # Calculate notional values
    buy_trades['notional_value'] = buy_trades['trade_price'] * buy_trades['trade_size']
    sell_trades['notional_value'] = sell_trades['trade_price'] * sell_trades['trade_size']

    # Convert to list of [trade_price, notional_value] for each trade
    buy_trades_list = buy_trades[['trade_price', 'notional_value']].values.tolist()
    sell_trades_list = sell_trades[['trade_price', 'notional_value']].values.tolist()

    # Ensure the notional values are numbers
    buy_trades_list = [[float(trade[0]), float(trade[1])] for trade in buy_trades_list]
    sell_trades_list = [[float(trade[0]), float(trade[1])] for trade in sell_trades_list]

    return buy_trades_list, sell_trades_list

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bid_ask_chart(request):
    valid_time_filters = ['last_1_day', 'last_2_days',
                          'last_3_days', 'last_4_days', 'last_5_days']
    valid_benchmarks = ['LAST_PRICE', 'TWAP', 'VWAP']

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    file_id = data.get('fileId')
    # cusip = data.get('cusip')
    time_filter = data.get("timeFilter", "last_1_day")
    benchmark = data.get("benchmark", "Last Price")

    if not file_id:
        return JsonResponse({'error': 'No file ID provided'}, status=400)

    if time_filter not in valid_time_filters:
        return JsonResponse({'error': 'Invalid time filter provided'}, status=400)

    if benchmark not in valid_benchmarks:
        return JsonResponse({'error': 'Invalid benchmark provided'}, status=400)

    # Fetching data for the specified file
    trades_data = fetch_trade_data(time_filter, file_id)
    market_data = fetch_market_data(time_filter, file_id)

    trades_data = pd.DataFrame(trades_data)
    market_data = pd.DataFrame(market_data)

    # Calculating Bid-Ask spread
    spread = 0.03 # Assuming default spread of 0.03
    market_data['bid'] = market_data['trade_price'] - spread / 2
    market_data['ask'] = market_data['trade_price'] + spread / 2

    # Calculate Volume 
    last_date = trades_data['trade_timestamp'].max()

    # Get the last trade price, multiply it by 30x, you get the total volume, now in the dataframe create a new column volume and linearly interpolate the volume for each trade
    last_trade_price = trades_data[trades_data['trade_timestamp']
                                   == last_date]['trade_price'].values[0]
    total_volume = int(last_trade_price * 30)
    trades_data['volume'] = np.linspace(1, total_volume, len(trades_data))

    # Calculate benchmarks
    benchmarks = calculate_benchmarks(market_data, trades_data, benchmark)

    # Aggregate trade data by day for buy and sell transactions
    notional_values_buy, notional_values_sell = calculate_notional_values(trades_data)

    # Generate response data
    response_data = {
        'bid_ask_chart': {
            'benchmarks': benchmarks,
            'notional_values_buy': list(notional_values_buy),
            'notional_values_sell': list(notional_values_sell),
        }
    }

    return JsonResponse(response_data, safe=False)