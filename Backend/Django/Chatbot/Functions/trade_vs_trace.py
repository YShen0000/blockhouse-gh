import pandas as pd
from Analytics.models import Trade
import numpy as np
from .utils import default_start_end_dates, build_table


def trade_vs_trace(file_id, start_date=None, end_date=None):
    start_date, end_date = default_start_end_dates(start_date, end_date)

    trades = Trade.objects.filter(
        file_id=file_id,
        trade_timestamp__gte=start_date,
        trade_timestamp__lte=end_date
    ).values()

    trades_df = pd.DataFrame.from_records(trades)

    # Synthesize TRACE data (simulating yield)
    np.random.seed(42)
    trades_df['trace_price'] = trades_df['trade_price'] * \
        (1 + np.random.uniform(-0.1, 0.1, len(trades_df)))

    # Simulate "Your Trade Yield (%)" and "Average TRACE Yield (%)" directly as we lack formulas
    # For simplicity, we invert the relationship between price and yield for simulation
    trades_df['your_trade_yield'] = 100 * (1 / trades_df['trade_price'])
    trades_df['average_trace_yield'] = 100 * (1 / trades_df['trace_price'])
    # End Synthesizing TRACE data

    trades_df['yield_differential_bps'] = 10000 * \
        (trades_df['your_trade_yield'] - trades_df['average_trace_yield'])

    trades_df['trade_date'] = trades_df['trade_timestamp'].dt.date

    # Aggregate by date
    aggregated_df = trades_df.groupby('trade_date').agg(
        your_trade_yield_avg=('your_trade_yield', 'mean'),
        average_trace_yield_avg=('average_trace_yield', 'mean'),
        yield_differential_bps_avg=('yield_differential_bps', 'mean')
    ).reset_index()

    aggregated_df.columns = [
        'Date', 'Your Trade Yield (%)', 'Average TRACE Yield (%)', 'Yield Differential (bps)']

    results = aggregated_df.to_dict(orient='records')

    table = build_table(results)

    return table

# Note: This function simulates yields and their differentials as a demonstration.
# Actual yield calculations would require detailed bond information and precise pricing data.
