import numpy as np
import pandas as pd

from Analytics.models import Trade

from Chatbot.Functions.utils import default_start_end_dates, build_chart


def trade_prices_vs_vwap(file_id, start_date=None, end_date=None):
    start_date, end_date = default_start_end_dates(start_date, end_date)

    trades = Trade.objects.filter(
        file_id=file_id, trade_timestamp__gte=start_date, trade_timestamp__lte=end_date
    ).values()

    trades_df = pd.DataFrame.from_records(trades)

    trades_df['trade_date'] = trades_df['trade_timestamp'].dt.date

    trades_df['volume'] = [100 + i
                           for i in np.linspace(0, 900, len(trades_df))]
    trades_df['trade_price'] = trades_df['trade_price']

    aggregated = trades_df.groupby('trade_date').apply(
        lambda df: pd.Series({
            'Aggregated Trade Price': (df['trade_price'] * df['volume']).sum() / df['volume'].sum(),
            'Total Volume': df['volume'].sum()
        })
    ).reset_index()

    total_volume = aggregated['Total Volume'].sum()
    total_value = (aggregated['Aggregated Trade Price']
                   * aggregated['Total Volume']).sum()
    vwap_overall = total_value / total_volume

    aggregated['VWAP'] = vwap_overall

    first_10_days = aggregated.head(10)

    trade_prices = first_10_days.apply(lambda row: [
                                       row['trade_date'].strftime('%Y-%m-%d'), row['Aggregated Trade Price']], axis=1).tolist()
    vwap_values = [[row['trade_date'].strftime(
        '%Y-%m-%d'), vwap_overall] for index, row in first_10_days.iterrows()]

    response_obj = {
        'trade_prices': trade_prices,
        'vwap_values': vwap_values
    }

    chart = build_chart(response_obj, "line")

    return chart
