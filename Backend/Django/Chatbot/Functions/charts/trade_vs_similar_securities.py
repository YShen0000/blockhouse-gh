import numpy as np
import pandas as pd
import json

from Analytics.models import Trade

from Chatbot.Functions.utils import default_start_end_dates, build_chart


def trade_vs_similar_securities(file_id, start_date=None, end_date=None):
    if start_date is None:
        start_date = pd.Timestamp.today() - pd.Timedelta(days=7)
    if end_date is None:
        end_date = pd.Timestamp.today()
    num_trades = np.random.randint(50, 200)  # Random number of trades
    trade_dates = pd.date_range(start=start_date, end=end_date, periods=num_trades)
    # Generate a random downward trend for trade prices from start to end
    trend_slope = np.random.uniform(-0.2, -0.05)  # Slope of the trend, ensuring it's downward
    trend = np.linspace(0, trend_slope * num_trades, num_trades)
    trade_prices = np.random.uniform(low=90, high=110, size=num_trades)  # Random trade prices between 90 and 110 
    trade_prices += trend
    volumes = np.random.randint(100, 1000, size=num_trades)  # Random volumes between 100 and 1000

    trades = pd.DataFrame({
        # "file_id": [file_id] * num_trades,
        "trade_timestamp": trade_dates,
        "trade_price": trade_prices,
        "volume": volumes
    }).to_dict('records')

    trades_df = pd.DataFrame.from_records(trades)

    trades_df["trade_date"] = trades_df["trade_timestamp"].dt.date

    aggregated = (
        trades_df.groupby("trade_date")
        .apply(lambda df: pd.Series({}))
        .reset_index()
    )

    num_rows = len(aggregated)

    result = {
        "Your STT (bips)": [(date, np.round(np.random.uniform(1, 10), 2)) for date in aggregated['trade_date']],
        "STT MSFT (bips)": [(date, np.round(np.random.uniform(1, 10), 2)) for date in aggregated['trade_date']],
        "STT GOOG (bips)": [(date, np.round(np.random.uniform(1, 10), 2)) for date in aggregated['trade_date']],
        "STT META (bips)": [(date, np.round(np.random.uniform(1, 10), 2)) for date in aggregated['trade_date']],
    }

    # # Serialize the result to JSON format
    # result_json = json.dumps(result)

    chart = build_chart(result, "line")

    return chart

