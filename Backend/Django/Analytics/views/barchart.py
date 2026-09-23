import json
import logging
import pandas as pd

from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from Analytics.utils.fetch_data import fetch_trade_data, fetch_market_data

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def barchart(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    file_id = data.get('fileId')
    if not file_id:
        return JsonResponse({'error': 'No file ID provided'}, status=400)

    cusip_from_body = data.get("cusip")
    time_filter = data.get("timeFilter", "last_1_day")

    # Fetching data for the specified file and timeframe
    trades_data = fetch_trade_data(time_filter, file_id)
    market_data = fetch_market_data(time_filter, file_id)

    df_trades = pd.DataFrame(trades_data)
    df_market = pd.DataFrame(market_data)

    # Convert trade_timestamp to datetime for easier manipulation
    df_trades['trade_timestamp'] = pd.to_datetime(df_trades['trade_timestamp'])
    df_market['trade_timestamp'] = pd.to_datetime(df_market['trade_timestamp'])

    # Determine the last trade timestamp across both trades and market data
    last_date = df_trades['trade_timestamp'].max()

    # Time filters relative to the last trade date
    time_filters = {
        'last_1_day': last_date - timedelta(days=1),
        'last_7_days': last_date - timedelta(days=7),
        'last_30_days': last_date - timedelta(days=30),
        'last_90_days': last_date - timedelta(days=90),
        'last_365_days': last_date - timedelta(days=365),
    }

    # Filter the dataframes based on the selected time filter
    # Default to last_1_day if not found
    start_date = time_filters.get(time_filter, last_date - timedelta(days=1))
    df_trades = df_trades[df_trades['trade_timestamp'] >= start_date]
    df_market = df_market[df_market['trade_timestamp'] >= start_date]

    unique_cusips = df_trades['cusip'].unique().tolist()
    cusip = cusip_from_body if cusip_from_body in unique_cusips else unique_cusips[
        0] if unique_cusips else None

    if cusip is None:
        return JsonResponse({'error': 'No data found for the provided CUSIP or no CUSIPs available.'}, status=404)

    trades_df = df_trades[df_trades['cusip'] == cusip].copy()
    market_df = df_market[df_market['cusip'] == cusip].copy()

    trades_df.loc[:, 'Expected TCA'] = 0.0
    trades_df.loc[:, 'Trade Impact'] = 0.0
    trades_df.loc[:, 'Net Trade Impact'] = 0.0

    for index, trade in trades_df.iterrows():
        trade_time = trade['trade_timestamp']
        trade_price = trade['trade_price']
        trade_volume = trade['trade_size']

        # Find corresponding market prices
        price_at_trade_records = market_df[market_df['trade_timestamp'] <= trade_time].nlargest(
            1, 'trade_timestamp')
        price_after_trade_records = market_df[market_df['trade_timestamp']
                                              > trade_time].nsmallest(1, 'trade_timestamp')

        if not price_at_trade_records.empty and not price_after_trade_records.empty:
            price_at_trade = price_at_trade_records['trade_price'].iloc[0]
            price_after_trade = price_after_trade_records['trade_price'].iloc[0]

            if trade['trade_direction'] == 'BUY':
                trades_df.at[index, 'Expected TCA'] = float(
                    trade_volume * (price_at_trade - trade_price))
                trades_df.at[index, 'Trade Impact'] = float(
                    trade_volume * (price_after_trade - price_at_trade))
            elif trade['trade_direction'] == 'SELL':
                trades_df.at[index, 'Expected TCA'] = float(
                    trade_volume * (trade_price - price_at_trade))
                trades_df.at[index, 'Trade Impact'] = float(
                    trade_volume * (price_at_trade - price_after_trade))

            trades_df.at[index, 'Net Trade Impact'] = trades_df.at[index,
                                                                   'Expected TCA'] + trades_df.at[index, 'Trade Impact']

    aggregated_result = trades_df.agg(
        {'Expected TCA': 'sum', 'Trade Impact': 'sum', 'Net Trade Impact': 'sum'}).to_dict()

    return JsonResponse({'aggregated_result': aggregated_result, 'unique_cusips': unique_cusips})