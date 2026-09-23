import numpy as np
import pandas as pd
from decimal import Decimal

from .utils import build_table


def analyze_similar_trades(file_id, start_date=None, end_date=None):
    if start_date is None:
        start_date = pd.Timestamp.today() - pd.Timedelta(days=7)
    if end_date is None:
        end_date = pd.Timestamp.today()
    num_trades = np.random.randint(50, 200)  # Random number of trades
    trade_dates = pd.date_range(start=start_date, end=end_date, periods=num_trades)
    trade_prices = np.random.uniform(low=90, high=110, size=num_trades)  # Random trade prices between 90 and 110
    volumes = np.random.randint(100, 1000, size=num_trades)  # Random volumes between 100 and 1000

    trades_df = pd.DataFrame({
        "trade_timestamp": trade_dates,
        "trade_price": trade_prices,
        "volume": volumes
    })

    trades_df["trade_date"] = trades_df["trade_timestamp"].dt.date
    trades_df["stt"] = Decimal("100") + pd.Series(np.linspace(0, 900, num_trades)).apply(Decimal)
    trades_df["trade_price"] = trades_df["trade_price"].apply(Decimal)
    trades_df["volume"] = trades_df["volume"].apply(lambda x: Decimal(x))
    aggregated = (
        trades_df.groupby("trade_date")
        .apply(
            lambda df: pd.Series(
                {
                    "Avg Trade Price": np.round(
                        np.random.uniform(98, 101, 1)[0], 2
                    ),
                }
            )
        )
        .reset_index()
    )

    num_rows = len(aggregated)
    # Synthetic data generation for additional columns
    np.random.seed(42)  # For reproducibility

    aggregated["Avg STT (bips)"] = np.round(np.random.uniform(1, 10, num_rows), 2)
    aggregated["Avg STT MSFT (bips)"] = np.round(np.random.uniform(1, 10, num_rows), 2)
    aggregated["Avg STT GOOG (bips)"] = np.round(np.random.uniform(1, 10, num_rows), 2)
    aggregated["Avg STT META (bips)"] = np.round(np.random.uniform(1, 10, num_rows), 2)

    aggregated["Avg Trade Price"] = aggregated["Avg Trade Price"].astype(float)
    print(aggregated)
    aggregated.columns = [
        "Trade Date",
        "Avg Trade Price",
        "Avg STT (bips)",
        "Avg STT MSFT (bips)",
        "Avg STT GOOG (bips)",
        "Avg STT META (bips)",
    ]

    results = aggregated.to_dict(orient="records")

    table = build_table(results)

    return table
