import numpy as np
import pandas as pd
from decimal import Decimal

from Analytics.models import Trade

from .utils import default_start_end_dates, build_table

def analyze_trades_vwap(file_id, start_date=None, end_date=None):
    start_date, end_date = default_start_end_dates(start_date, end_date)

    trades = Trade.objects.filter(
        file_id=file_id, trade_timestamp__gte=start_date, trade_timestamp__lte=end_date).values()

    trades_df = pd.DataFrame.from_records(trades)

    trades_df['trade_date'] = trades_df['trade_timestamp'].dt.date

    # Synthesize volume 
    trades_df['volume'] = [Decimal('100') + Decimal(i) for i in np.linspace(0, 900, len(trades_df))]

    # Ensure trade_price is Decimal
    trades_df['trade_price'] = trades_df['trade_price'].apply(Decimal)

    # Group by trade_date and calculate aggregated volume and weighted price
    aggregated = trades_df.groupby('trade_date').apply(
        lambda df: pd.Series({
            'Aggregated Trade Price': (df['trade_price'] * df['volume']).sum() / df['volume'].sum(),
            'Total Volume': df['volume'].sum()
        })
    ).reset_index()

    # Calculate VWAP for each day
    total_volume = aggregated['Total Volume'].sum()
    total_value = (aggregated['Aggregated Trade Price'] * aggregated['Total Volume']).sum()
    vwap_overall = total_value / total_volume

    # Compare aggregated daily trade price to overall VWAP and calculate difference in bps
    aggregated['Price vs. VWAP (bps)'] = ((aggregated['Aggregated Trade Price'] - vwap_overall) / vwap_overall) * Decimal('10000')
    aggregated['VWAP'] = vwap_overall

    # Formatting the DataFrame for a more readable output
    aggregated = aggregated.round({'Aggregated Trade Price': 2, 'VWAP': 2, 'Price vs. VWAP (bps)': 0})
    aggregated.columns = ['Trade Date', 'Your Aggregated Trade Price', 'Total Volume', 'Price vs. VWAP (bps)', 'VWAP']

    aggregated['Your Aggregated Trade Price'] = aggregated['Your Aggregated Trade Price'].astype(float)
    aggregated['VWAP'] = aggregated['VWAP'].astype(float)
    aggregated['Total Volume'] = aggregated['Total Volume'].astype(float)
    aggregated['Price vs. VWAP (bps)'] = aggregated['Price vs. VWAP (bps)'].astype(float)

    results = aggregated.to_dict(orient='records')

    table = build_table(results)

    return table
