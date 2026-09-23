from datetime import timedelta

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import json
import logging
import pandas as pd

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from Analytics.utils.fetch_data import fetch_trade_data, fetch_market_data

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def executions_over_time(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    file_id = data.get('fileId')
    if not file_id:
        return JsonResponse({'error': 'No file ID provided'}, status=400)

    cusip_from_body = data.get("cusip")
    time_filter = data.get("timeFilter", "last_1_day")

    # Fetching data for the specified file
    trades_data = fetch_trade_data(time_filter, file_id)
    market_data = fetch_market_data(time_filter, file_id)

    df_trades = pd.DataFrame(trades_data)
    df_market = pd.DataFrame(market_data)

    # Convert trade_timestamp to datetime for easier manipulation
    df_trades['trade_timestamp'] = pd.to_datetime(df_trades['trade_timestamp'])
    df_market['trade_timestamp'] = pd.to_datetime(df_market['trade_timestamp'])

    # Determine the last trade timestamp across both trades and market data
    last_trade = df_trades['trade_timestamp'].max()

    # Calculate the start of the last trade date for 'last_1_day' filter
    start_of_last_trade_date = last_trade.normalize()

    # Time filters relative to the last trade date
    time_filters = {
        'last_1_day': start_of_last_trade_date,
        'last_7_days': last_trade - timedelta(days=7),
        'last_30_days': last_trade - timedelta(days=30),
        'last_90_days': last_trade - timedelta(days=90),
        'last_365_days': last_trade - timedelta(days=365),
    }

    # Filter the dataframes based on the selected time filter
    start_date = time_filters.get(time_filter, last_trade - timedelta(days=1))
    df_trades = df_trades[df_trades['trade_timestamp'] >= start_date]
    df_market = df_market[df_market['trade_timestamp'] >= start_date]

    unique_cusips = df_trades['cusip'].unique().tolist()
    cusip = cusip_from_body if cusip_from_body in unique_cusips else unique_cusips[
        0] if unique_cusips else None

    if cusip is None:
        return JsonResponse({'error': 'No data found for the provided CUSIP or no CUSIPs available.'}, status=404)

    trades_df = df_trades[df_trades['cusip'] == cusip].copy()
    market_df = df_market[df_market['cusip'] == cusip].copy()

    markout_period = 5

    trades_df['markout'] = 0.0
    trades_df['pnl'] = 0.0

    for trade in trades_df.itertuples():
        trade_time = trade.trade_timestamp
        reference_time = trade_time + timedelta(minutes=markout_period)

        filtered_market_prices = market_df[market_df['trade_timestamp']
                                           >= reference_time]

        if not filtered_market_prices.empty:
            closest_market_price = filtered_market_prices.iloc[0]
            reference_price = closest_market_price['trade_price']
        else:
            reference_price = trade.trade_price

        markout = float(trade.trade_price - reference_price if trade.trade_direction ==
                        'BUY' else reference_price - trade.trade_price)
        pnl = markout * trade.trade_size

        trades_df.at[trade.Index, 'markout'] = float(markout)
        trades_df.at[trade.Index, 'pnl'] = float(pnl)

    if time_filter == 'last_1_day':
        # Ensure that data is within the same calendar date for 'last_1_day' filter
        trades_df = trades_df[trades_df['trade_timestamp']
                              >= start_of_last_trade_date]
        grouped = trades_df.groupby([pd.Grouper(
            key='trade_timestamp', freq='15min'), 'trader']).agg({'pnl': 'sum'}).reset_index()
    else:
        grouped = trades_df.groupby([pd.Grouper(
            key='trade_timestamp', freq='D'), 'trader']).agg({'pnl': 'sum'}).reset_index()

    response_data = {}
    for trader in grouped['trader'].unique():
        trader_data = grouped[grouped['trader'] == trader]
        response_data[trader] = trader_data[[
            'trade_timestamp', 'pnl']].values.tolist()

    overall_pnl = grouped.groupby(['trade_timestamp']).agg(
        {'pnl': 'sum'}).reset_index()
    response_data['Overall'] = overall_pnl[[
        'trade_timestamp', 'pnl']].values.tolist()

    return JsonResponse({"data": response_data, "unique_cusips": list(unique_cusips)}, safe=False)