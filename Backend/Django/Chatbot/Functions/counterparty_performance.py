import pandas as pd
from django.db.models import F, Avg, Count, Case, When, FloatField
from Analytics.models import Trade, Market_Prices
from .utils import default_start_end_dates, build_table


def counterparty_performance(file_id, start_date=None, end_date=None):
    start_date, end_date = default_start_end_dates(start_date, end_date)

    trades = Trade.objects.filter(
        file_id=file_id,
        trade_timestamp__range=(start_date, end_date)
    ).annotate(
        execution_speed=F('execution_time'),
        trade_completed=Case(
            When(fill= 1, then=True),
            default=False,
            output_field=FloatField()
        )
    ).values(
        'counterparty', 'execution_speed', 'trade_completed', 'cusip', 'trade_timestamp', 'trade_price'
    )

    trades_df = pd.DataFrame.from_records(trades)

    market_prices = Market_Prices.objects.filter(
        cusip__in=trades_df['cusip'].unique(),
        trade_timestamp__range=(start_date, end_date)
    ).values('cusip', 'trade_timestamp', 'trade_price')

    market_prices_df = pd.DataFrame.from_records(market_prices)

    trades_df['trade_timestamp'] = pd.to_datetime(trades_df['trade_timestamp'])
    market_prices_df['trade_timestamp'] = pd.to_datetime(
        market_prices_df['trade_timestamp'])

    market_prices_df.sort_values(by=['cusip', 'trade_timestamp'], inplace=True)

    # Use forward fill to assign each trade the latest market price before its timestamp
    combined_df = pd.merge_asof(trades_df.sort_values('trade_timestamp'), market_prices_df.sort_values('trade_timestamp'),
                              by='cusip', on='trade_timestamp', suffixes=('_trade', '_market'), direction='backward')

    # Calculate price improvement
    combined_df['price_improvement'] = combined_df['trade_price_trade'] - \
        combined_df['trade_price_market']
    combined_df['favorable_trade'] = combined_df['price_improvement'] > 0

    # Aggregate data to calculate metrics for each counterparty
    performance_metrics = combined_df.groupby('counterparty').agg(
        average_execution_time=pd.NamedAgg(
            column='execution_speed', aggfunc='mean'),
        reliability=pd.NamedAgg(column='trade_completed', aggfunc='mean'),
        favorable_price_negotiation_rate=pd.NamedAgg(
            column='favorable_trade', aggfunc='mean')
    ).reset_index()

    # Convert reliability and favorable price negotiation rate to percentages
    performance_metrics['reliability'] = performance_metrics['reliability'] * 100
    performance_metrics['favorable_price_negotiation_rate'] = performance_metrics['favorable_price_negotiation_rate'] * 100

    performance_metrics.rename(columns={
        'average_execution_time': 'Average Execution Time',
        'reliability': 'Reliability (%)',
        'favorable_price_negotiation_rate': 'Favorable Price Negotiation Rate (%)'
    }, inplace=True)

    final_result = build_table(performance_metrics.to_dict('records'))

    return final_result
