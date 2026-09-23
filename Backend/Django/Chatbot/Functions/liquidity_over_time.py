import pandas as pd
from django.db.models import Sum, F, Avg

from Analytics.models import Trade, Market_Prices

from .utils import default_start_end_dates, build_table


def liquidity_over_time(file_id, start_date=None, end_date=None):
    start_date, end_date = default_start_end_dates(start_date, end_date)

    trades = Trade.objects.filter(
        file__id=file_id,
        trade_timestamp__gte=start_date,
        trade_timestamp__lte=end_date
    ).annotate(
        date=F('trade_timestamp__date')
    ).values(
        'date', 'cusip'
    ).annotate(
        trading_volume=Sum('trade_size'),
        avg_trade_price=Avg('trade_price')
    ).order_by('date')

    market_prices = Market_Prices.objects.filter(
        cusip__in=trades.values('cusip'),
        trade_timestamp__date__gte=start_date,
        trade_timestamp__date__lte=end_date
    ).annotate(
        date=F('trade_timestamp__date')
    ).values(
        'date', 'cusip'
    ).annotate(
        avg_market_price=Avg('trade_price')
    )

    trades_df = pd.DataFrame.from_records(trades)
    market_prices_df = pd.DataFrame.from_records(market_prices)

    merged_df = pd.merge(trades_df, market_prices_df, on=[
                         'date', 'cusip'], how='inner')
    merged_df['bid_ask_spread'] = (
        merged_df['avg_trade_price'] - merged_df['avg_market_price']).abs()

    final_results = merged_df.groupby('date').agg({
        'trading_volume': 'sum',
        'bid_ask_spread': 'mean'
    }).reset_index()

    final_results = final_results.to_dict(orient='records')

    table = build_table(final_results)

    return table
