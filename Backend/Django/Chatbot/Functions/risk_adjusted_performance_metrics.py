import pandas as pd
from Analytics.models import Trade, Market_Prices
from .utils import default_start_end_dates, build_table


def risk_free_rate():
    return 0.02  # Placeholder for the risk-free rate


def risk_adjusted_performance_metrics(file_id, start_date=None, end_date=None):
    start_date, end_date = default_start_end_dates(start_date, end_date)

    trades = Trade.objects.filter(
        file__id=file_id,
        trade_timestamp__gte=start_date,
        trade_timestamp__lte=end_date
    ).values('cusip', 'trade_timestamp', 'trade_price')

    market_prices = Market_Prices.objects.filter(
        trade_timestamp__gte=start_date,
        trade_timestamp__lte=end_date
    ).values('cusip', 'trade_timestamp', 'trade_price')

    trades_df = pd.DataFrame(list(trades))
    market_prices_df = pd.DataFrame(list(market_prices))

    trades_df['trade_timestamp'] = pd.to_datetime(trades_df['trade_timestamp'])
    market_prices_df['trade_timestamp'] = pd.to_datetime(
        market_prices_df['trade_timestamp'])

    market_prices_df.sort_values(by=['cusip', 'trade_timestamp'], inplace=True)

    # Use forward fill to assign each trade the latest market price before its timestamp
    merged_df = pd.merge_asof(trades_df.sort_values('trade_timestamp'), market_prices_df.sort_values('trade_timestamp'),
                              by='cusip', on='trade_timestamp', suffixes=('', '_market'), direction='backward')

    merged_df['return'] = (merged_df['trade_price'] -
                           merged_df['trade_price_market']) / merged_df['trade_price_market']

    # Drop any rows with NaN returns (i.e., no market price was found)
    merged_df.dropna(subset=['return'], inplace=True)

    # Calculate risk metrics
    avg_return = merged_df['return'].mean()
    excess_returns = avg_return - risk_free_rate()
    std_dev = merged_df['return'].std()
    downside_returns = merged_df[merged_df['return'] < 0]['return']
    downside_dev = downside_returns.std()

    sharpe_ratio = excess_returns / std_dev if std_dev > 0 else 'Undefined'
    sortino_ratio = excess_returns / downside_dev if downside_dev > 0 else 'Undefined'

    results  = [{
        'Sharpe Ratio': sharpe_ratio,
        'Sortino Ratio': sortino_ratio
    }]

    table = build_table(results)

    return table
