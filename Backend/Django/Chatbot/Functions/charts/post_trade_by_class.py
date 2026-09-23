import pandas as pd
from Analytics.models import Trade, Market_Prices
from Chatbot.Functions.utils import default_start_end_dates, build_chart


def post_trade_by_class(file_id, start_date=None, end_date=None):
    start_date, end_date = default_start_end_dates(start_date, end_date)

    trades = Trade.objects.filter(
        file_id=file_id,
        trade_timestamp__gte=start_date,
        trade_timestamp__lte=end_date
    ).values('cusip', 'trade_size', 'trade_price', 'trade_timestamp')

    market_prices = Market_Prices.objects.filter(
        trade_timestamp__lte=end_date
    ).values('cusip', 'trade_price', 'trade_timestamp')

    trades_df = pd.DataFrame.from_records(trades)
    market_prices_df = pd.DataFrame.from_records(market_prices)

    trades_df['trade_timestamp'] = pd.to_datetime(
        trades_df['trade_timestamp']).astype(int) / 10**9
    market_prices_df['trade_timestamp'] = pd.to_datetime(
        market_prices_df['trade_timestamp']).astype(int) / 10**9

    trades_df.sort_values('trade_timestamp', inplace=True)
    market_prices_df.sort_values('trade_timestamp', inplace=True)

    merged_df = pd.merge_asof(trades_df, market_prices_df, by='cusip',
                              on='trade_timestamp', suffixes=('', '_market'), direction='backward')

    merged_df['Price Impact (bps)'] = 10000 * (merged_df['trade_price'] - merged_df.get(
        'trade_price_market', 0)) / merged_df.get('trade_price_market', 1)

    merged_df['Average Execution Price'] = merged_df['trade_price']

    completeness_threshold = 0.88  # 88%
    merged_df['Trade Completeness (%)'] = 100 * (
        abs(merged_df['Price Impact (bps)']) <= 100 * completeness_threshold)

    results_df = merged_df.groupby(['cusip']).agg(
        Average_Execution_Price=('Average Execution Price', 'mean'),
        Price_Impact_bps=('Price Impact (bps)', 'mean'),
        Trade_Completeness=('Trade Completeness (%)', 'mean')
    ).reset_index()

    results = results_df.to_dict(orient='records')

    final_result = []

    for result in results:
        final_result.append([
            result['cusip'],
            # 'Average Execution Price': result['Average_Execution_Price'],
            result['Price_Impact_bps'],
            # 'Trade Completeness (%)': result['Trade_Completeness']
        ])

    chart = build_chart(final_result, "bar")

    return chart
