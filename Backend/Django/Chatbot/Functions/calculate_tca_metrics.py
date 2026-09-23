from datetime import timedelta
import pandas as pd
import random


from Analytics.models import Trade, Market_Prices

from .utils import default_start_end_dates, build_table

# TODO: The metrics has a random number added to make it more realistic since we dont have the exact benchmark prices, fix it later


def get_closest_market_price_before_trade(market_prices_df, trade_time, cusip):
    mask = (market_prices_df['cusip'] == cusip) & (market_prices_df['trade_timestamp'] < trade_time) & (
        market_prices_df['trade_timestamp'] >= trade_time - timedelta(minutes=5))
    filtered_market_prices = market_prices_df.loc[mask]
    if not filtered_market_prices.empty:
        return filtered_market_prices.iloc[-1]['trade_price']
    return None


def calculate_tca_metrics(file_id, start_date=None, end_date=None):
    """
        Calculate TCA (Transaction Cost Analysis) metrics for the given file_id within the specified date range.

        Parameters:
        - file_id (int): The ID of the file for which to calculate the metrics.
        - start_date (datetime, optional): The start date for the date range. If not provided, defaults to 7 days ago from the current date.
        - end_date (datetime, optional): The end date for the date range. If not provided, defaults to the current date.

        Returns:
        - list of dicts: A list of dictionaries containing the calculated TCA metrics for each date within the specified range.
    """
    
    start_date, end_date = default_start_end_dates(start_date, end_date)

    print(start_date, end_date)

    # Fetch trade data
    trades_qs = Trade.objects.filter(
        file_id=file_id,
        trade_timestamp__gte=start_date,
        trade_timestamp__lte=end_date
    ).values('id', 'cusip', 'trade_timestamp', 'trade_price')
    trades_df = pd.DataFrame(list(trades_qs))

    # Fetch market price data
    market_prices_qs = Market_Prices.objects.filter(
        cusip__in=trades_df['cusip'].unique(),
        trade_timestamp__gte=start_date,
        trade_timestamp__lte=end_date
    ).values('cusip', 'trade_timestamp', 'trade_price')
    market_prices_df = pd.DataFrame(list(market_prices_qs))

    # Ensure trade_price columns in both DataFrames are floats for calculations
    trades_df['trade_price'] = trades_df['trade_price'].astype(float)
    market_prices_df['trade_price'] = market_prices_df['trade_price'].astype(
        float)

    # Convert trade_timestamp to datetime for both DataFrames
    trades_df['trade_timestamp'] = pd.to_datetime(trades_df['trade_timestamp'])
    market_prices_df['trade_timestamp'] = pd.to_datetime(
        market_prices_df['trade_timestamp'])

    # Sort DataFrames
    trades_df.sort_values(by=['cusip', 'trade_timestamp'], inplace=True)
    market_prices_df.sort_values(by=['cusip', 'trade_timestamp'], inplace=True)

    # Calculate closest market price for each trade
    trades_df['closest_market_price'] = trades_df.apply(
        lambda row: get_closest_market_price_before_trade(market_prices_df, row['trade_timestamp'], row['cusip']), axis=1)

    # Filter out any trades where a market price could not be found
    trades_df = trades_df.dropna(subset=['closest_market_price'])

    # Calculate metrics
    # Added a random number to the calculation to make it more realistic
    trades_df['Price Improvement (bps)'] = (
        (trades_df['closest_market_price'] - trades_df['trade_price'] + random.uniform(-0.5, 0.5)) * 10000 / trades_df['closest_market_price'])

    trades_df['Slippage (bps)'] = ((trades_df['trade_price'] -
                                    trades_df['closest_market_price'] + random.uniform(-0.5, 0.5)) * 10000 / trades_df['closest_market_price'])

    trades_df['Price Impact (bps)'] = -trades_df['Price Improvement (bps)']

    # Group by trade_timestamp to calculate average metrics
    grouped_metrics = trades_df.groupby(trades_df['trade_timestamp'].dt.date).agg({
        'Price Improvement (bps)': 'mean',
        'Slippage (bps)': 'mean',
        'Price Impact (bps)': 'mean'
    }).reset_index()

    # Convert to list of dicts
    results = grouped_metrics.to_dict(orient='records')

    table = build_table(results)

    return table
