import pandas as pd
from django.db.models import F, Avg
from Analytics.models import Trade, Market_Prices
from Chatbot.Functions.utils import default_start_end_dates, build_chart


def bid_ask_spread(file_id, start_date=None, end_date=None):
    start_date, end_date = default_start_end_dates(start_date, end_date)

    trades_qs = Trade.objects.filter(
        file__id=file_id,
        trade_timestamp__gte=start_date,
        trade_timestamp__lte=end_date
    ).annotate(
        date=F('trade_timestamp__date')
    ).values(
        'date', 'cusip'
    ).annotate(
        avg_trade_price=Avg('trade_price')
    ).order_by('date')
    trades_df = pd.DataFrame.from_records(trades_qs)

    market_prices_qs = Market_Prices.objects.filter(
        cusip__in=trades_df['cusip'].unique(),
        trade_timestamp__date__gte=start_date,
        trade_timestamp__date__lte=end_date
    ).annotate(
        date=F('trade_timestamp__date')
    ).values(
        'date', 'cusip'
    ).annotate(
        avg_market_price=Avg('trade_price')
    )
    market_prices_df = pd.DataFrame.from_records(market_prices_qs)

    # Merging trade and market price data
    merged_df = pd.merge(trades_df, market_prices_df, on=[
                         'date', 'cusip'], how='inner')
    merged_df['bid_ask_spread'] = (
        merged_df['avg_trade_price'] - merged_df['avg_market_price']).abs()

    # Group by date to calculate the average bid-ask spread for each day
    final_results = merged_df.groupby('date').agg({
        'bid_ask_spread': 'mean'
    }).reset_index()

    final_results['date'] = pd.to_datetime(final_results['date'])
    final_results['bid_ask_spread'] = final_results['bid_ask_spread'].round(2)

    results = final_results.apply(lambda row: [
        row['date'].strftime('%Y-%m-%d'), row['bid_ask_spread']], axis=1).tolist()

    response_obj = {
        'bid_ask_spread': results
    }

    chart = build_chart(response_obj, "line")

    return chart
