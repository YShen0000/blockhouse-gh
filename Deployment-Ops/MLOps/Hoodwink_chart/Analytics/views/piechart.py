import json
import logging
import pandas as pd

from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from Analytics.models import Market_Prices, Trade, Uploads, User

logger = logging.getLogger(__name__)

@csrf_exempt
@permission_classes([IsAuthenticated])
def piechart(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    file_id = data.get('fileId')
    if not file_id:
        return JsonResponse({'error': 'No file ID provided'}, status=400)

    # Use the default 'last_1_day' if no time_filter is provided
    time_filter = data.get("timeFilter", "last_1_day")

    # Fetching data for the specified file
    trades_data = Trade.objects.filter(file_id=file_id).values()
    df_trades = pd.DataFrame(trades_data)

    # Convert trade_timestamp to datetime for easier manipulation
    df_trades['trade_timestamp'] = pd.to_datetime(df_trades['trade_timestamp'])

    # Find the last date in the trades data
    last_date = df_trades['trade_timestamp'].max()

    # Time filters relative to the last date
    time_filters = {
        'last_1_day': last_date - timedelta(days=1),
        'last_7_days': last_date - timedelta(days=7),
        'last_30_days': last_date - timedelta(days=30),
        'last_90_days': last_date - timedelta(days=90),
        'last_365_days': last_date - timedelta(days=365),
    }

    # Filter the dataframe based on the selected time filter
    # Default to last_1_day if not found
    start_date = time_filters.get(time_filter, last_date - timedelta(days=1))
    df_trades = df_trades[df_trades['trade_timestamp'] >= start_date]

    # Calculate aggregate completed and non-completed notional values
    agg_comp = 0
    agg_noncomp = 0
    for _, row in df_trades.iterrows():
        notional_value = row['face_value'] * row['trade_size']
        if row['fill'] == 1.0:
            agg_comp += notional_value
        else:
            agg_noncomp += notional_value

    total_notional = agg_comp + agg_noncomp

    # Initialize trader and counterparty dictionaries
    unique_traders = df_trades['trader'].unique()
    unique_counterparties = df_trades['counterparty'].unique()

    comp_volume_by_trader = dict.fromkeys(unique_traders, 0)
    noncomp_volume_by_trader = dict.fromkeys(unique_traders, 0)
    comp_volume_by_counterparty = dict.fromkeys(unique_counterparties, 0)
    noncomp_volume_by_counterparty = dict.fromkeys(unique_counterparties, 0)

    # Calculate volumes
    for _, row in df_trades.iterrows():
        trader = row['trader']
        counterparty = row['counterparty']
        volume = row['face_value'] * row['trade_size']

        if row['fill'] == 1.0:
            comp_volume_by_trader[trader] += volume
            comp_volume_by_counterparty[counterparty] += volume
        elif row['fill'] == -1:
            noncomp_volume_by_trader[trader] += volume
            noncomp_volume_by_counterparty[counterparty] += volume

    # Convert volumes to percentages
    total_comp_volume = sum(comp_volume_by_trader.values())
    total_noncomp_volume = sum(noncomp_volume_by_trader.values())

    comp_volume_by_trader = {trader: (volume / total_comp_volume * 100)
                             for trader, volume in comp_volume_by_trader.items()}
    noncomp_volume_by_trader = {trader: (volume / total_noncomp_volume * 100)
                                for trader, volume in noncomp_volume_by_trader.items()}

    comp_volume_by_counterparty = {counterparty: (
        volume / total_comp_volume * 100) for counterparty, volume in comp_volume_by_counterparty.items()}
    noncomp_volume_by_counterparty = {counterparty: (
        volume / total_noncomp_volume * 100) for counterparty, volume in noncomp_volume_by_counterparty.items()}

    return JsonResponse({
        'agg_comp': agg_comp,
        'agg_noncomp': agg_noncomp,
        'total_notional': total_notional,
        'comp_volume_by_trader_percentage': comp_volume_by_trader,
        'noncomp_volume_by_trader_percentage': noncomp_volume_by_trader,
        'comp_volume_by_counterparty_percentage': comp_volume_by_counterparty,
        'noncomp_volume_by_counterparty_percentage': noncomp_volume_by_counterparty
    })