import json
import logging
import numpy as np
import pandas as pd

from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from Analytics.models import Market_Prices, Trade, Uploads, User

from Analytics.utils.fetch_data import fetch_trade_data, fetch_market_data

logger = logging.getLogger(__name__)

@csrf_exempt
@permission_classes([IsAuthenticated])
def heatmap(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Fetching data from the request body
    file_id = data.get('fileId')
    if not file_id:
        return JsonResponse({'error': 'No file ID provided'}, status=400)

    time_filter, cusip_from_body = data.get(
        "timeFilter", "last_1_day"), data.get("cusip")

    trades_data = fetch_trade_data(time_filter, file_id)
    market_data = fetch_market_data(time_filter, file_id)

    df_trades = pd.DataFrame(list(trades_data))
    df_market = pd.DataFrame(list(market_data))

    unique_cusips = df_trades['cusip'].unique().tolist()
    unique_traders = df_trades['trader'].unique().tolist()
    time_intervals = [1, 30, 60, 90]  # Default intervals, adjust as needed

    num_traders = len(unique_traders)
    num_intervals = len(time_intervals)
    markout_data = np.zeros((num_traders, num_intervals))

    selected_cusip = cusip_from_body if cusip_from_body else unique_cusips[0]
    selected_cusip_df = df_trades[df_trades['cusip'] == selected_cusip]
    df_market = df_market[df_market['cusip'] == selected_cusip]

    for i, trader in enumerate(unique_traders):
        trader_df = selected_cusip_df[selected_cusip_df['trader'] == trader]
        for j, interval in enumerate(time_intervals):
            markouts = []
            for index, trade in trader_df.iterrows():
                trade_time = pd.to_datetime(trade['trade_timestamp'])
                reference_time = trade_time + timedelta(minutes=interval)
                reference_price = df_market[(
                    df_market['trade_timestamp'] >= reference_time)].iloc[0]['trade_price']

                if reference_price:
                    trade_price = trade['trade_price']
                    markout = trade_price - \
                        reference_price if trade['trade_direction'] == 'BUY' else reference_price - trade_price
                    markouts.append(markout)
                else:
                    markouts.append(0)

            if markouts:
                markout_data[i][j] = np.mean(markouts)
            else:
                markout_data[i][j] = 0

    return JsonResponse({
        'cusip': selected_cusip,
        'markouts': markout_data.tolist(),
        'traders': unique_traders,
        'intervals': time_intervals,
        'unique_cusips': unique_cusips,
    })