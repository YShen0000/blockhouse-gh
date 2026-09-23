
from datetime import timedelta

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import json
import logging
import pandas as pd

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from Analytics.models import Trade

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def traded_quantities(request):
    '''
    A view to calculate the total traded quantities for a given file ID and time filter

    Args:
        request: The request object

        request.body: The request body containing the file ID and time filter
            fileId: string, required
            timeFilter: string, optional (default: last_30_days)
            category: string, required (asset_class, maturity, trade_size)

    Returns:
        JsonResponse: A JSON response containing the total traded quantities
    '''
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    file_id = data.get('fileId')
    category = data.get('category')
    time_filter = data.get("timeFilter", "last_30_day")

    trades_data = Trade.objects.filter(file_id=file_id).values()

    if not trades_data:
        return JsonResponse({'error': 'No data found for the provided file ID'}, status=404)

    df_trades = pd.DataFrame(trades_data)
    df_trades['trade_timestamp'] = pd.to_datetime(df_trades['trade_timestamp'])

    last_trade = df_trades['trade_timestamp'].max()

    time_filters = {
        'last_1_day': last_trade - timedelta(days=1),
        'last_7_days': last_trade - timedelta(days=7),
        'last_30_days': last_trade - timedelta(days=30),
        'last_90_days': last_trade - timedelta(days=90),
        'last_365_days': last_trade - timedelta(days=365),
    }

    start_date = time_filters.get(
        time_filter, last_trade - timedelta(days=30))
    df_trades = df_trades[df_trades['trade_timestamp'] >= start_date]

    unique_cusips = df_trades['cusip'].unique()

    if category == 'asset_class':
        notional_values = []
        for cusip in unique_cusips:
            cusip_trades = df_trades[df_trades['cusip'] == cusip]
            notional_value = cusip_trades['face_value'] * \
                cusip_trades['trade_size']
            notional_values.append(notional_value.sum())

        cusip_notional_list = list(zip(unique_cusips, notional_values))
        cusip_notional_list_json_ready = [
            (cusip, int(notional_value)) for cusip, notional_value in cusip_notional_list]

        return JsonResponse({'values': cusip_notional_list_json_ready})

    elif category == "maturity":
        # This is manual, in the future we can add a maturity column to the Trades model
        cusip_mappings = {
            '912810SZ41': '30 Year',
            '037833CS7': '10 Year',
            '16119PAS03': '8 Year'
        }

        notional_values = []
        for cusip in unique_cusips:
            if cusip in cusip_mappings:
                cusip_trades = df_trades[df_trades['cusip'] == cusip]

                notional_value = cusip_trades['face_value'] * \
                    cusip_trades['trade_size']
                notional_values.append(int(notional_value.sum()))
        maturity_face_values = list(
            zip(cusip_mappings.values(), notional_values))
        return JsonResponse({'values': maturity_face_values})

    elif category == "trade_size":
        trade_sizes = df_trades['trade_size']
        notional_values = df_trades['face_value'] * trade_sizes

        notional_values = {
            '<1M': 0,
            '1-5M': 0,
            '5-10M': 0,
            '>10M': 0
        }

        for index, trade in df_trades.iterrows():
            notional_value = trade['face_value'] * trade['trade_size']
            if trade['trade_size'] < 1_000_000:
                notional_values['<1M'] += notional_value
            elif 1_000_000 <= trade['trade_size'] < 5_000_000:
                notional_values['1-5M'] += notional_value
            elif 5_000_000 <= trade['trade_size'] < 10_000_000:
                notional_values['5-10M'] += notional_value
            else:
                notional_values['>10M'] += notional_value

        notional_values_list = list([key, value]
                                    for key, value in notional_values.items())

        return JsonResponse({'values': notional_values_list})
    else:
        return JsonResponse({'error': 'Invalid category provided'}, status=400)