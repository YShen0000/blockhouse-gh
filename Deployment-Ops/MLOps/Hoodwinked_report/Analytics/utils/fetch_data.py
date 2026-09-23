from Analytics.models import Market_Prices, Trade
from datetime import datetime, timedelta
from django.db.models import Max
from django.http import JsonResponse

def fetch_trade_data(time_filter, file_id):
    last_date = Trade.objects.filter(file_id=file_id).aggregate(
        Max('trade_timestamp'))['trade_timestamp__max']
    if not last_date:
        return JsonResponse({'error': 'No trades found for the given file ID'}, status=404)

    # Time filters relative to the last date
    time_filters = {
        'last_1_day': last_date - timedelta(days=1),
        'last_2_days': last_date - timedelta(days=2),
        'last_3_days': last_date - timedelta(days=3),
        'last_4_days': last_date - timedelta(days=4),
        'last_5_days': last_date - timedelta(days=5),
        'last_6_days': last_date - timedelta(days=6),
        'last_7_days': last_date - timedelta(days=7),
        'last_30_days': last_date - timedelta(days=30),
        'last_90_days': last_date - timedelta(days=90),
        'last_365_days': last_date - timedelta(days=365),
    }

    start_date = time_filters.get(time_filter, last_date - timedelta(days=1))

    trades_data = Trade.objects.filter(
        file_id=file_id, trade_timestamp__gte=start_date).values()

    return trades_data


def fetch_market_data(time_filter, file_id):
    last_date = Trade.objects.filter(file_id=file_id).aggregate(
        Max('trade_timestamp'))['trade_timestamp__max']
    if not last_date:
        return JsonResponse({'error': 'No trades found for the given file ID'}, status=404)

    # Time filters relative to the last date
    time_filters = {
        'last_1_day': last_date - timedelta(days=1),
        'last_2_days': last_date - timedelta(days=2),
        'last_3_days': last_date - timedelta(days=3),
        'last_4_days': last_date - timedelta(days=4),
        'last_5_days': last_date - timedelta(days=5),
        'last_6_days': last_date - timedelta(days=6),
        'last_7_days': last_date - timedelta(days=7),
        'last_30_days': last_date - timedelta(days=30),
        'last_90_days': last_date - timedelta(days=90),
        'last_365_days': last_date - timedelta(days=365),
    }

    start_date = time_filters.get(time_filter, last_date - timedelta(days=1))
    return Market_Prices.objects.filter(
        trade_timestamp__gte=start_date).values()