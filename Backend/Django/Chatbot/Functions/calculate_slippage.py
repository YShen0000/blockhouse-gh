import pandas as pd
from django.db.models.functions import TruncDay
from Analytics.models import Trade, Market_Prices
from .utils import default_start_end_dates, build_table


def calculate_slippage(file_id, start_date=None, end_date=None):
    start_date, end_date = default_start_end_dates(start_date, end_date)

    trades_qs = Trade.objects.filter(
        file_id=file_id,
        trade_timestamp__gte=start_date,
        trade_timestamp__lte=end_date
    ).annotate(
        trade_date=TruncDay('trade_timestamp')
    ).values('id', 'cusip', 'trade_date', 'trade_price', 'trade_size', 'fill')

    market_prices_qs = Market_Prices.objects.filter(
        trade_timestamp__gte=start_date,
        trade_timestamp__lte=end_date
    ).annotate(
        trade_date=TruncDay('trade_timestamp')
    ).values('cusip', 'trade_date', 'trade_price')

    trades_df = pd.DataFrame(list(trades_qs))
    market_prices_df = pd.DataFrame(list(market_prices_qs))

    market_prices_avg = market_prices_df.groupby(['cusip', 'trade_date'])[
        'trade_price'].mean().reset_index()
    market_prices_avg.rename(
        columns={'trade_price': 'avg_market_price'}, inplace=True)

    merged_df = pd.merge(trades_df, market_prices_avg,
                         on=['cusip', 'trade_date'])

    merged_df['slippage'] = merged_df['trade_price'] - \
        merged_df['avg_market_price']

    daily_metrics = merged_df.groupby('trade_date').agg(
        average_slippage=('slippage', 'mean'),
        trade_price_std=('trade_price', 'std'),
        trade_price_mean=('trade_price', 'mean'),
        trades_filled=('fill', lambda x: (x > 0).mean())
    ).reset_index()

    daily_metrics['price_deviation'] = (
        daily_metrics['trade_price_std'] / daily_metrics['trade_price_mean']) * 100

    daily_metrics['trade_completeness'] = daily_metrics['trades_filled']

    final_metrics = daily_metrics[[
        'trade_date', 'average_slippage', 'price_deviation', 'trade_completeness']]

    final_results = final_metrics.to_dict(orient='records')

    table = build_table(final_results)

    return table
