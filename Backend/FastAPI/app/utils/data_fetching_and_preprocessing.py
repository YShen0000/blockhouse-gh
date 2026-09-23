import re
from fastapi import HTTPException
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from io import BytesIO
import matplotlib

matplotlib.use("Agg")
from scipy.signal import savgol_filter
import boto3
import json

from ..config.settings import settings

# Calculate HWOE price - Using actual model
sagemaker_runtime = boto3.client(
    "sagemaker-runtime",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def preprocess_by_platform(trade_blotter, platform_type):
    if platform_type == "Robinhood":
        return process_robinhood(trade_blotter)
    elif platform_type == "Charles Schwab":
        return process_cs(trade_blotter)
    elif platform_type == "Webull":
        return process_webull(trade_blotter)
    elif platform_type == "Plaid":
        return process_plaid(trade_blotter)
    else:
        return "Error"


def process_plaid(trade_blotter):
    trade_blotter.rename(
        columns={
            "date": "Activity Date",
            "type": "Trans Code",
            "ticker_symbol": "Instrument",
            "quantity": "Quantity",
            "price": "Price",
        },
        inplace=True,
    )
    trade_blotter["Instrument"] = trade_blotter["Instrument"].str.strip()
    trade_blotter["Quantity"] = trade_blotter["Quantity"].abs()
    trade_blotter.dropna(
        subset=["Activity Date", "Trans Code", "Instrument"], inplace=True
    )
    trade_blotter_filtered = trade_blotter[
        trade_blotter["Trans Code"].str.contains("buy|sell", case=False, regex=True)
    ]
    return trade_blotter_filtered


def process_cs(trade_blotter):
    trade_blotter.rename(
        columns={
            "Date": "Activity Date",
            "Action": "Trans Code",
            "Symbol": "Instrument",
        },
        inplace=True,
    )
    trade_blotter["Instrument"] = trade_blotter["Instrument"].str.strip()
    trade_blotter.dropna(
        subset=["Activity Date", "Trans Code", "Instrument"], inplace=True
    )
    trade_blotter_filtered = trade_blotter[
        trade_blotter["Trans Code"].str.contains("buy|sell", case=False, regex=True)
    ]
    return trade_blotter_filtered


def process_robinhood(trade_blotter):
    trade_blotter["Instrument"] = trade_blotter["Instrument"].str.strip()
    trade_blotter.dropna(
        subset=["Activity Date", "Trans Code", "Instrument"], inplace=True
    )
    trade_blotter_filtered = trade_blotter[
        trade_blotter["Trans Code"].str.contains("buy|sell", case=False, regex=True)
    ]
    return trade_blotter_filtered


def process_webull(trade_blotter):
    trade_blotter.rename(
        columns={
            "Date": "Activity Date",
            "Action": "Trans Code",
            "Symbol": "Instrument",
        },
        inplace=True,
    )
    trade_blotter["Instrument"] = trade_blotter["Instrument"].str.strip()
    trade_blotter.dropna(
        subset=["Activity Date", "Trans Code", "Instrument"], inplace=True
    )
    trade_blotter_filtered = trade_blotter[
        trade_blotter["Trans Code"].str.contains("buy|sell", case=False, regex=True)
    ]
    return trade_blotter_filtered


def fetch_market_data(tickers):
    data_dict = {}
    available_tickers = []
    for ticker in tickers:
        data = yf.Ticker(ticker).history(period="2y", interval="1h")
        if not data.empty:
            data.index = data.index.tz_localize(None)  # Ensure timezone-naive datetime
            data_dict[ticker] = data
            available_tickers.append(ticker)
        else:
            print(f"No data found for {ticker}, it may be delisted.")
    return data_dict, available_tickers


def get_week_range(date):
    start_of_week = date - timedelta(days=date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week


def preprocess_data(trade_blotter, data_dict):
    # Define the tickers you need to fetch data for
    tickers = trade_blotter["Instrument"].unique()

    Open_prices = []
    Close_prices = []
    TWAP_prices = []
    VWAP_prices = []
    HWOE_prices = []

    trade_blotter["Activity Date"] = pd.to_datetime(
        trade_blotter["Activity Date"]
    ).dt.tz_localize(None)
    two_years_ago = pd.to_datetime("today") - pd.DateOffset(years=2)
    trade_blotter = trade_blotter[trade_blotter["Activity Date"] >= two_years_ago]

    for index, row in trade_blotter.iterrows():
        date = row["Activity Date"]
        ticker = row["Instrument"]
        trans_code = row["Trans Code"]
        quantity = row["Quantity"]
        date_str = date.strftime("%Y-%m-%d")

        if ticker in data_dict:
            if date_str in data_dict[ticker].index:
                data = data_dict[ticker].loc[date_str]
                if not data.empty:
                    Open = data["Open"].iloc[0]
                    Open_prices.append(Open)
                    Close = data["Close"].iloc[-1]
                    Close_prices.append(Close)
                    TWAP = data["Close"].mean()
                    TWAP_prices.append(TWAP)
                    VWAP = (data["Close"] * data["Volume"]).sum() / data["Volume"].sum()
                    VWAP_prices.append(VWAP)
                    start_of_week, end_of_week = get_week_range(date)
                    week_data = data_dict[ticker].loc[start_of_week:end_of_week]

                    # Calculate HWOE price using SageMaker
                    payload = {
                        "ticker": ticker,
                        "action": trans_code,
                        "inventory": quantity,
                        "timeframe": 390,
                        "Timestamp": date_str,
                    }
                    request_body = json.dumps(payload)

                    try:
                        response = sagemaker_runtime.invoke_endpoint(
                            EndpointName="endpoint-real-time-inference24-HW-R",
                            Body=request_body,
                            ContentType="application/json",
                            InferenceComponentName="model-real-time-inference24-HW-R-inference-component",
                        )

                        # Format the response as a dictionary of trades to be made
                        response_str = response["Body"].read().decode("utf-8")
                        response_dict = eval(response_str)
                        inference = pd.DataFrame(response_dict)
                        inference["timestamp"] = pd.to_datetime(
                            inference["timestamp"]
                        ).dt.tz_localize(None)

                        # Since the inference provides several optimal execution times, we volume weight the HW prices
                        if inference is not None:
                            HWOE_prices.append(
                                (inference["volume"] * inference["limit_price"]).sum()
                                / inference["volume"].sum()
                            )
                        else:
                            HWOE_prices.append(None)
                    except Exception as e:
                        print(
                            f"SageMaker inference failed: {e}. Using fallback calculation."
                        )
                        # Fallback to simple min/max calculation
                        if trans_code.lower() == "buy":
                            HWOE_row = data.loc[data["Low"].idxmin()]
                            HWOE_price = HWOE_row["Low"]
                        elif trans_code.lower() == "sell":
                            HWOE_row = data.loc[data["High"].idxmax()]
                            HWOE_price = HWOE_row["High"]
                        else:
                            HWOE_price = None
                        HWOE_prices.append(HWOE_price)

                else:
                    Open_prices.append(None)
                    Close_prices.append(None)
                    TWAP_prices.append(None)
                    VWAP_prices.append(None)
                    HWOE_prices.append(None)
            else:
                Open_prices.append(None)
                Close_prices.append(None)
                TWAP_prices.append(None)
                VWAP_prices.append(None)
                HWOE_prices.append(None)
        else:
            Open_prices.append(None)
            Close_prices.append(None)
            TWAP_prices.append(None)
            VWAP_prices.append(None)
            HWOE_prices.append(None)

    # Append the calculated values to the trade_blotter DataFrame
    trade_blotter["Open_Price"] = Open_prices
    trade_blotter["Close_Price"] = Close_prices
    trade_blotter["TWAP_Price"] = TWAP_prices
    trade_blotter["VWAP_Price"] = VWAP_prices
    trade_blotter["HWOE_Price"] = HWOE_prices

    ## ADDING SLIPPAGE ##
    slippage_open = []
    slippage_close = []
    slippage_twap = []
    slippage_vwap = []
    slippage_hwoe = []

    for index, row in trade_blotter.iterrows():
        trans_code = row["Trans Code"]
        trade_price = row["Price"]

        if trans_code.lower() == "buy":
            slippage_open.append(row["Open_Price"] - trade_price)
            slippage_close.append(row["Close_Price"] - trade_price)
            slippage_twap.append(row["TWAP_Price"] - trade_price)
            slippage_vwap.append(row["VWAP_Price"] - trade_price)
            slippage_hwoe.append(row["HWOE_Price"] - trade_price)
        elif trans_code.lower() == "sell":
            slippage_open.append(trade_price - row["Open_Price"])
            slippage_close.append(trade_price - row["Close_Price"])
            slippage_twap.append(trade_price - row["TWAP_Price"])
            slippage_vwap.append(trade_price - row["VWAP_Price"])
            slippage_hwoe.append(trade_price - row["HWOE_Price"])
        else:
            slippage_open.append(None)
            slippage_close.append(None)
            slippage_twap.append(None)
            slippage_vwap.append(None)
            slippage_hwoe.append(None)

    # Append slippage values to the trade_blotter DataFrame
    trade_blotter["Slippage_Open"] = slippage_open
    trade_blotter["Slippage_Close"] = slippage_close
    trade_blotter["Slippage_TWAP"] = slippage_twap
    trade_blotter["Slippage_VWAP"] = slippage_vwap
    trade_blotter["Slippage_HWOE"] = slippage_hwoe

    # Add slippage %
    trade_blotter["Slippage_PCT_Open"] = (
        trade_blotter["Slippage_Open"] / trade_blotter["Open_Price"]
    )
    trade_blotter["Slippage_PCT_Close"] = (
        trade_blotter["Slippage_Close"] / trade_blotter["Close_Price"]
    )
    trade_blotter["Slippage_PCT_TWAP"] = (
        trade_blotter["Slippage_TWAP"] / trade_blotter["TWAP_Price"]
    )
    trade_blotter["Slippage_PCT_VWAP"] = (
        trade_blotter["Slippage_VWAP"] / trade_blotter["VWAP_Price"]
    )
    trade_blotter["Slippage_PCT_HWOE"] = (
        trade_blotter["Slippage_HWOE"] / trade_blotter["HWOE_Price"]
    )

    return trade_blotter


def adjust_for_splits(trade_blotter, fetched_tickers):
    two_years_ago = datetime.now() - timedelta(days=2 * 365)
    tickers = trade_blotter["Instrument"].unique()
    idx = 0
    for ticker in tickers:
        stock = fetched_tickers[idx]
        splits = stock.splits
        if len(splits) > 0:
            splits.index = splits.index.tz_localize(None)
            recent_splits = splits[splits.index >= two_years_ago]
            for split_date, split_ratio in recent_splits.items():
                if isinstance(split_ratio, (int, float)):
                    mask = (trade_blotter["Instrument"] == ticker) & (
                        trade_blotter["Activity Date"] < split_date
                    )
                    trade_blotter.loc[mask, "Price"] /= split_ratio
                    trade_blotter.loc[mask, "Quantity"] *= split_ratio
                else:
                    continue
        idx += 1
    return trade_blotter


def is_fund(ticker_symbol):
    # Fetch the ticker info
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info

    # Funds often lack industry and sector info, or might have "Fund" or "ETF" in the long business summary
    industry = info.get("industry", None)
    sector = info.get("sector", None)
    # business_summary = info.get('longBusinessSummary', '').lower()

    # Logic to determine if it's a fund
    if not industry and not sector:
        return True
    return False


def preprocess_data_merged(trade_blotter):
    # Remove leading/trailing spaces in 'Instrument' column
    trade_blotter["Instrument"] = trade_blotter["Instrument"].str.strip()

    # Define the tickers you need to fetch data for
    tickers = trade_blotter["Instrument"].unique()
    data_dict = {}
    fetched_tickers = []
    # Fetch and store the data for each ticker
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        fetched_tickers.append(stock)
        try:
            best_period = "2y"
            if best_period not in stock.history_metadata["validRanges"]:
                best_period = "max"
            data = stock.history(period=best_period, interval="1h")
            if not data.empty:
                data.index = data.index.tz_localize(
                    None
                )  # Ensure timezone-naive datetime
                data_dict[ticker] = data
            else:
                print(f"No data found for ticker: {ticker}")
        except Exception as e:
            print(f"Error fetching data for ticker {ticker}: {e}")

    # Filter out trades with tickers that couldn't fetch data
    trade_blotter = trade_blotter[trade_blotter["Instrument"].isin(data_dict.keys())]

    # Lists to store results
    Open_prices = []
    Close_prices = []
    TWAP_prices = []
    VWAP_prices = []
    HWOE_prices = []
    HWOE_days = []
    HWOE_times = []
    volume = []
    vol_rolling_mean = []
    volatility = []
    volatility_rolling_mean = []
    high = []
    low = []
    trade_days = []
    trade_times = []
    five_day_ma = []

    # Helper function to find the start and end of the week
    def get_week_range(date):
        start_of_week = date - pd.DateOffset(days=date.weekday())
        end_of_week = start_of_week + pd.DateOffset(days=6)
        return start_of_week, end_of_week

    # Converting to dt and ensure timezone-naive
    trade_blotter["Activity Date"] = pd.to_datetime(
        trade_blotter["Activity Date"]
    ).dt.tz_localize(None)
    ## Added this to merge processing pipelines
    two_years_ago = pd.to_datetime("today") - pd.DateOffset(years=2)
    trade_blotter = trade_blotter[trade_blotter["Activity Date"] >= two_years_ago]

    # Adjust for stock splits
    trade_blotter = adjust_for_splits(trade_blotter, fetched_tickers)

    # Calculate the required values from the stored data
    for index, row in trade_blotter.iterrows():
        date = row["Activity Date"]
        ticker = row["Instrument"]
        trans_code = row["Trans Code"]
        date_str = date.strftime("%Y-%m-%d")

        # Filter data for the specific date
        try:
            data = data_dict[ticker].loc[date_str]
        except Exception as e:
            print(f"User date of {date_str} does not exist for {ticker}")

        if not data.empty:
            # Calculate open and close prices
            Open = data["Open"].iloc[0]
            Open_prices.append(Open)
            Close = data["Close"].iloc[-1]
            Close_prices.append(Close)
            volume_data = data["Volume"].mean()
            volume.append(volume_data)

            # Calculate TWAP
            TWAP = data["Close"].mean()
            TWAP_prices.append(TWAP)

            # Calculate VWAP
            VWAP = (data["Close"] * data["Volume"]).sum() / data["Volume"].sum()
            VWAP_prices.append(VWAP)

            # Calculate HWOE price using SageMaker
            payload = {
                "ticker": ticker,
                "action": trans_code,
                "inventory": row["Quantity"],
                "timeframe": 390,
                "Timestamp": date_str,
            }
            request_body = json.dumps(payload)

            try:
                response = sagemaker_runtime.invoke_endpoint(
                    EndpointName="endpoint-real-time-inference24-HW-R",
                    Body=request_body,
                    ContentType="application/json",
                    InferenceComponentName="model-real-time-inference24-HW-R-inference-component",
                )

                # Format the response as a dictionary of trades to be made
                response_str = response["Body"].read().decode("utf-8")
                response_dict = eval(response_str)
                inference = pd.DataFrame(response_dict)
                inference["timestamp"] = pd.to_datetime(
                    inference["timestamp"]
                ).dt.tz_localize(None)

                # Since the inference provides several optimal execution times, we volume weight the HW prices
                if inference is not None:
                    HWOE_prices.append(
                        (inference["volume"] * inference["limit_price"]).sum()
                        / inference["volume"].sum()
                    )
                    HWOE_days.append(inference["timestamp"][0].strftime("%A"))
                    HWOE_times.append(inference["timestamp"][0].strftime("%H:%M:%S"))
                else:
                    HWOE_prices.append(None)
                    HWOE_days.append(None)
                    HWOE_times.append(None)
            except Exception as e:
                print(f"SageMaker inference failed: {e}. Using fallback calculation.")
                # Fallback to simple min/max calculation
                if trans_code.lower() == "buy":
                    HWOE_row = data.loc[data["Low"].idxmin()]
                    HWOE_price = HWOE_row["Low"]
                elif trans_code.lower() == "sell":
                    HWOE_row = data.loc[data["High"].idxmax()]
                    HWOE_price = HWOE_row["High"]
                else:
                    HWOE_price = None
                    HWOE_row = None

                HWOE_prices.append(HWOE_price)
                if HWOE_row is not None:
                    HWOE_days.append(HWOE_row.name.strftime("%A"))
                    HWOE_times.append(HWOE_row.name.strftime("%H:%M:%S"))
                else:
                    HWOE_days.append(None)
                    HWOE_times.append(None)
                pass  # Continue processing other rows

            # Calculate 5-day moving average (5d_MA)
            past_5_days_data = data_dict[ticker].loc[date - pd.Timedelta(days=5) : date]

            if not past_5_days_data.empty:
                five_day_ma_value = (
                    past_5_days_data["Close"]
                    .rolling(window=5, min_periods=1)
                    .mean()
                    .iloc[-1]
                )
            else:
                five_day_ma_value = None

            five_day_ma.append(five_day_ma_value)

            # vol_rolling_mean.append(past_5_days_data['Volume'].rolling(window=5, min_periods=1).mean().iloc[-1])
            # Calculate 5-day rolling mean of volume
            rolling_volume_mean = (
                past_5_days_data["Volume"].rolling(window=5, min_periods=1).mean()
            )

            if not rolling_volume_mean.empty:
                vol_rolling_mean.append(rolling_volume_mean.iloc[-1])
            else:
                vol_rolling_mean.append(None)

            # Calculate volatility as the standard deviation of close prices over the past 5 days
            volatility_rolling = (
                past_5_days_data["Close"].rolling(window=5, min_periods=1).std()
            )

            if not volatility_rolling.empty:
                volatility_value = volatility_rolling.iloc[-1]
                volatility.append(volatility_value)
            else:
                volatility.append(None)

            # Calculate rolling mean of volatility over the past 5 days
            volatility_rolling_mean_value = volatility_rolling.rolling(
                window=5, min_periods=1
            ).mean()

            if not volatility_rolling_mean_value.empty:
                volatility_rolling_mean.append(volatility_rolling_mean_value.iloc[-1])
            else:
                volatility_rolling_mean.append(None)

            high_data = data["High"].max()
            low_data = data["Low"].min()

            high.append(high_data)
            low.append(low_data)

        else:
            Open_prices.append(None)
            Close_prices.append(None)
            TWAP_prices.append(None)
            VWAP_prices.append(None)
            HWOE_prices.append(None)
            HWOE_days.append(None)
            HWOE_times.append(None)
            volume.append(None)
            vol_rolling_mean.append(None)
            volatility.append(None)
            volatility_rolling_mean.append(None)
            high.append(None)
            low.append(None)
            trade_days.append(None)
            trade_times.append(None)
            five_day_ma.append(None)

    # Optionally, append the calculated values to the trade_blotter DataFrame
    trade_blotter["Open_Price"] = Open_prices
    trade_blotter["Close_Price"] = Close_prices
    trade_blotter["TWAP_Price"] = TWAP_prices
    trade_blotter["VWAP_Price"] = VWAP_prices
    trade_blotter["HWOE_Price"] = HWOE_prices
    trade_blotter["Market Volume"] = volume
    trade_blotter["Volume_Rolling_Mean"] = vol_rolling_mean
    trade_blotter["Volatility"] = volatility
    trade_blotter["Volatility_Rolling_Mean"] = volatility_rolling_mean
    trade_blotter["High"] = high
    trade_blotter["Low"] = low
    trade_blotter["HWOE_Day"] = HWOE_days
    trade_blotter["HWOE_Time"] = HWOE_times
    trade_blotter["5d_MA"] = five_day_ma

    ##ADDING SLIPPAGE##
    # Lists to store slippage values
    slippage_open = []
    slippage_close = []
    slippage_twap = []
    slippage_vwap = []
    slippage_hwoe = []

    # Calculate slippage for each row
    for index, row in trade_blotter.iterrows():
        trans_code = row["Trans Code"]
        trade_price = row["Price"]  # Assuming there's a column with the trade price

        # Calculate slippage
        if trans_code.lower() == "buy":
            slippage_open.append(row["Open_Price"] - trade_price)
            slippage_close.append(row["Close_Price"] - trade_price)
            slippage_twap.append(row["TWAP_Price"] - trade_price)
            slippage_vwap.append(row["VWAP_Price"] - trade_price)
            slippage_hwoe.append(row["HWOE_Price"] - trade_price)
        elif trans_code.lower() == "sell":
            slippage_open.append(trade_price - row["Open_Price"])
            slippage_close.append(trade_price - row["Close_Price"])
            slippage_twap.append(trade_price - row["TWAP_Price"])
            slippage_vwap.append(trade_price - row["VWAP_Price"])
            slippage_hwoe.append(trade_price - row["HWOE_Price"])
        else:
            slippage_open.append(None)
            slippage_close.append(None)
            slippage_twap.append(None)
            slippage_vwap.append(None)
            slippage_hwoe.append(None)

    # Append slippage values to the trade_blotter DataFrame
    trade_blotter["Slippage_Open"] = slippage_open
    trade_blotter["Slippage_Close"] = slippage_close
    trade_blotter["Slippage_TWAP"] = slippage_twap
    trade_blotter["Slippage_VWAP"] = slippage_vwap
    trade_blotter["Slippage_HWOE"] = slippage_hwoe

    # Add slippage %
    trade_blotter["Slippage_PCT_Open"] = (
        trade_blotter["Slippage_Open"] / trade_blotter["Open_Price"]
    )
    trade_blotter["Slippage_PCT_Close"] = (
        trade_blotter["Slippage_Close"] / trade_blotter["Close_Price"]
    )
    trade_blotter["Slippage_PCT_TWAP"] = (
        trade_blotter["Slippage_TWAP"] / trade_blotter["TWAP_Price"]
    )
    trade_blotter["Slippage_PCT_VWAP"] = (
        trade_blotter["Slippage_VWAP"] / trade_blotter["VWAP_Price"]
    )
    trade_blotter["Slippage_PCT_HWOE"] = (
        trade_blotter["Slippage_HWOE"] / trade_blotter["HWOE_Price"]
    )

    return trade_blotter, data_dict


# Slippage Pie Chart
def slippage_pie_chart(trade_blotter_filtered, stock, start_date, end_date, benchmark):
    trade_df = trade_blotter_filtered[
        (trade_blotter_filtered["Instrument"] == stock)
        & (trade_blotter_filtered["Activity Date"] >= start_date)
        & (trade_blotter_filtered["Activity Date"] <= end_date)
    ]

    if trade_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No trades found for {stock} between {start_date} and {end_date}.",
        )

    slippage_column = f"Slippage_{benchmark}"

    # Invert slippage values
    trade_df[slippage_column] = -trade_df[slippage_column]

    trade_df["Slippage_Class"] = pd.cut(
        trade_df[slippage_column],
        bins=[-float("inf"), -0.02, 0.02, float("inf")],
        labels=["Low Slippage", "Moderate Slippage", "High Slippage"],
    )

    trade_df["Notional_Value"] = trade_df["Quantity"] * trade_df["Price"]

    slippage_summary = trade_df.groupby("Slippage_Class")["Notional_Value"].sum()

    # Adding hover data
    trade_df["Hover_Text"] = (
        trade_df["Trans Code"]
        + " "
        + trade_df["Quantity"].astype(str)
        + " @ $"
        + trade_df["Price"].astype(str)
    )
    hover_texts = trade_df.groupby("Slippage_Class")["Hover_Text"].apply(
        lambda x: " , ".join(x)
    )
    slippage_summary = pd.merge(slippage_summary, hover_texts, on="Slippage_Class")

    return slippage_summary.to_dict()


# Line Chart


def calculate_excess_returns(
    data, stock, benchmarks, start_date, end_date, hwoe_adjustment_factor=0.25
):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    if stock not in data["Instrument"].unique():
        print(f"Stock {stock} does not exist in the data.")
        return {}

    filtered_data = data[
        (data["Instrument"] == stock)
        & (data["Activity Date"] >= start_date)
        & (data["Activity Date"] <= end_date)
    ].copy()
    if filtered_data.empty:
        print(f"No data available for stock {stock} in the specified date range.")
        return {}

    filtered_data = filtered_data.sort_values(by="Activity Date", ascending=True)
    excess_returns = {}

    for benchmark in benchmarks:
        if benchmark == "HWOE":
            filtered_data[f"Slippage_{benchmark}_Adjusted"] = (
                filtered_data[f"Slippage_{benchmark}"] * hwoe_adjustment_factor
            )
            filtered_data[f"{benchmark}_Excess_Returns"] = -(
                filtered_data[f"Slippage_{benchmark}_Adjusted"]
                * filtered_data["Quantity"]
            ).cumsum()
            excess_returns[benchmark] = filtered_data[
                ["Activity Date", f"{benchmark}_Excess_Returns"]
            ]
        else:
            filtered_data[f"{benchmark}_Excess_Returns"] = -(
                filtered_data[f"Slippage_{benchmark}"] * filtered_data["Quantity"]
            ).cumsum()
            excess_returns[benchmark] = filtered_data[
                ["Activity Date", f"{benchmark}_Excess_Returns"]
            ]

    return excess_returns


def calculate_aggregated_excess_returns(
    data, benchmarks, start_date, end_date, hwoe_adjustment_factor=0.25
):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    data["Activity Date"] = pd.to_datetime(data["Activity Date"], errors="coerce")
    filtered_data = data[
        (data["Activity Date"] >= start_date) & (data["Activity Date"] <= end_date)
    ].copy()

    if filtered_data.empty:
        print("No data available in the specified date range.")
        return {}

    filtered_data = filtered_data.sort_values(by="Activity Date", ascending=True)
    excess_returns = {}

    for benchmark in benchmarks:
        if benchmark == "HWOE":
            filtered_data[f"Slippage_{benchmark}_Adjusted"] = (
                filtered_data[f"Slippage_{benchmark}"] * hwoe_adjustment_factor
            )
            filtered_data[f"{benchmark}_Excess_Returns"] = -(
                filtered_data[f"Slippage_{benchmark}_Adjusted"]
                * filtered_data["Quantity"]
            ).cumsum()
            excess_returns[benchmark] = filtered_data[
                ["Activity Date", f"{benchmark}_Excess_Returns"]
            ]
        else:
            filtered_data[f"{benchmark}_Excess_Returns"] = -(
                filtered_data[f"Slippage_{benchmark}"] * filtered_data["Quantity"]
            ).cumsum()
            excess_returns[benchmark] = filtered_data[
                ["Activity Date", f"{benchmark}_Excess_Returns"]
            ]
    return excess_returns


def get_excess_returns_data(
    trade_blotter_filtered,
    stock,
    show_open,
    show_close,
    show_twap,
    show_vwap,
    show_hwoe,
    start_date,
    end_date,
    hwoe_adjustment_factor=0.3,
    aggregate=False,
):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    benchmarks = []
    if show_open:
        benchmarks.append("Open")
    if show_close:
        benchmarks.append("Close")
    if show_twap:
        benchmarks.append("TWAP")
    if show_vwap:
        benchmarks.append("VWAP")
    if show_hwoe:
        benchmarks.append("HWOE")

    if aggregate:
        excess_returns = calculate_aggregated_excess_returns(
            trade_blotter_filtered,
            benchmarks,
            start_date,
            end_date,
            hwoe_adjustment_factor,
        )
    else:
        excess_returns = calculate_excess_returns(
            trade_blotter_filtered,
            stock,
            benchmarks,
            start_date,
            end_date,
            hwoe_adjustment_factor,
        )

    if not excess_returns:
        print("No valid excess returns data available.")
        return {}

    processed_data = {}
    for benchmark, returns in excess_returns.items():
        returns.set_index("Activity Date", inplace=True)
        # returns = returns[~returns.index.duplicated(keep='first')]
        returns = returns[~returns.index.duplicated(keep="last")]
        returns = returns.sort_index()

        if returns.index.isnull().any() or returns.empty:
            print(f"Skipping benchmark {benchmark} due to NaT or empty index.")
            continue

        start_idx = returns.index.min()
        end_idx = returns.index.max()

        if pd.isna(start_idx) or pd.isna(end_idx):
            print(f"Skipping benchmark {benchmark} due to NaT in start or end index.")
            continue

        full_index = pd.date_range(start_idx, end_idx)
        returns = returns.reindex(full_index).interpolate(method="linear").reset_index()
        returns.rename(columns={"index": "Activity Date"}, inplace=True)

        window_length = min(
            11, len(returns)
        )  # Adjust window length based on available data points
        if window_length < 2:
            print(
                f"Not enough data points for smoothing benchmark {benchmark}. Plotting raw data."
            )
            returns[f"{benchmark}_Excess_Returns"] = returns[
                f"{benchmark}_Excess_Returns"
            ]
        else:
            returns[f"{benchmark}_Excess_Returns"] = savgol_filter(
                returns[f"{benchmark}_Excess_Returns"],
                window_length=window_length,
                polyorder=2,
            )

        processed_data[benchmark] = returns[
            ["Activity Date", f"{benchmark}_Excess_Returns"]
        ].to_dict(orient="records")

    return processed_data


def plot_excess_returns(
    trade_blotter_filtered,
    stock,
    show_open,
    show_close,
    show_twap,
    show_vwap,
    show_hwoe,
    start_date,
    end_date,
    hwoe_adjustment_factor=0.25,
    aggregate=True,
):
    processed_data = get_excess_returns_data(
        trade_blotter_filtered,
        stock,
        show_open,
        show_close,
        show_twap,
        show_vwap,
        show_hwoe,
        start_date,
        end_date,
        hwoe_adjustment_factor,
        aggregate,
    )
    return processed_data


def calculate_excess_returns_original(data, stock, benchmarks):
    filtered_data = data[data["Instrument"] == stock]
    excess_returns = {}

    for benchmark in benchmarks:
        # Flip the sign of slippage and aggregate over time
        filtered_data[f"{benchmark}_Excess_Returns"] = -filtered_data[
            f"Slippage_{benchmark}"
        ].cumsum()
        # excess_returns[benchmark] = filtered_data[['Activity Date', f'{benchmark}_Excess_Returns']]
        excess_returns[benchmark] = filtered_data[
            ["Activity Date", f"{benchmark}_Excess_Returns"]
        ]

    return excess_returns


def plot_line_chart(
    trade_blotter_filtered,
    stock,
    show_open,
    show_close,
    show_twap,
    show_vwap,
    show_hwoe,
    start_date,
    end_date,
    hwoe_adjustment_factor=0.25,
    aggregate=True,
):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    benchmarks = []
    if show_open:
        benchmarks.append("Open")
    if show_close:
        benchmarks.append("Close")
    if show_twap:
        benchmarks.append("TWAP")
    if show_vwap:
        benchmarks.append("VWAP")
    if show_hwoe:
        benchmarks.append("HWOE")

    if aggregate:
        excess_returns = calculate_aggregated_excess_returns(
            trade_blotter_filtered,
            benchmarks,
            start_date,
            end_date,
            hwoe_adjustment_factor,
        )
    else:
        excess_returns = calculate_excess_returns(
            trade_blotter_filtered,
            stock,
            benchmarks,
            start_date,
            end_date,
            hwoe_adjustment_factor,
        )

    processed_data = {}
    for benchmark, returns in excess_returns.items():
        returns.set_index("Activity Date", inplace=True)
        # returns = returns[~returns.index.duplicated(keep='first')]
        returns = returns[~returns.index.duplicated(keep="last")]
        returns = returns.sort_index()
        full_index = pd.date_range(returns.index.min(), returns.index.max())
        returns = returns.reindex(full_index).interpolate(method="linear").reset_index()
        returns.rename(columns={"index": "Activity Date"}, inplace=True)
        # returns[f'{benchmark}_Excess_Returns_Smooth'] = savgol_filter(returns[f'{benchmark}_Excess_Returns'], window_length=11, polyorder=2)
        returns[f"{benchmark}_Excess_Returns_Smooth"] = returns[
            f"{benchmark}_Excess_Returns"
        ]
        processed_data[benchmark] = returns[
            ["Activity Date", f"{benchmark}_Excess_Returns_Smooth"]
        ]

    print(processed_data)
    plt.figure(figsize=(14, 7))
    for benchmark, data in processed_data.items():
        plt.plot(
            data["Activity Date"],
            data[f"{benchmark}_Excess_Returns_Smooth"],
            label=benchmark,
        )

    plt.xlabel("Date")
    plt.ylabel("Excess Cost Savings ($)")
    plt.title(
        f'Excess Returns Over Time By Strategy for {"All Stocks" if aggregate else stock}'
    )
    plt.legend()
    plt.grid(True)
    # Save the plot to a BytesIO buffer
    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)  # Rewind the buffer to the beginning

    return buffer


# Heatmap


def calculate_slippage(
    trade_data, data_dict, selected_trade="All Trades", hwoe_adjustment_factor=0.25
):
    days_after_trade = ["1 Day", "2 Days", "3 Days", "4 Days"]
    price_types = ["Open", "Close", "VWAP", "TWAP", "HWOE"]
    slippage_matrix = pd.DataFrame(
        index=price_types, columns=days_after_trade, dtype=float
    ).fillna(0)

    apply_adjustment = selected_trade == "All Trades"

    if selected_trade != "All Trades":
        trade_index = int(selected_trade.split(":")[0])
        selected_trade = trade_data.loc[trade_index]
        trades = trade_data.loc[[trade_index]]
    else:
        trades = trade_data

    for _, trade in trades.iterrows():
        trade_date = trade["Activity Date"]
        quantity = trade["Quantity"]
        trade_price = trade["Price"]
        ticker = trade["Instrument"]
        trans_code = trade["Trans Code"]

        if ticker not in data_dict:
            continue

        market_data = data_dict[ticker]

        days_counted = 0
        day = 1

        while days_counted < 4:
            date_after_trade = trade_date + timedelta(days=day)
            day += 1

            if date_after_trade.weekday() >= 5:
                continue
            market_subset = market_data.loc[
                market_data.index.date == date_after_trade.date()
            ]

            if not market_subset.empty:
                open_price = market_subset["Open"].iloc[0]
                close_price = market_subset["Close"].iloc[0]
                twap_price = np.mean(market_subset["Close"])
                vwap_price = np.sum(
                    market_subset["Close"] * market_subset["Volume"]
                ) / np.sum(market_subset["Volume"])
                # hwoe_price = calculate_blockhouse_pe(market_subset, date_after_trade, trans_code, data_dict, ticker)
                hwoe_price = calculate_blockhouse_pe(market_subset, trans_code)

                adjustment_factor = hwoe_adjustment_factor if apply_adjustment else 1

                if trans_code.lower() == "buy":
                    slippage_values = [
                        quantity * (trade_price - open_price),
                        quantity * (trade_price - close_price),
                        quantity * (trade_price - twap_price),
                        quantity * (trade_price - vwap_price),
                        quantity
                        * (trade_price - hwoe_price)
                        * adjustment_factor,  # Apply adjustment factor only for "All Trades"
                    ]
                else:
                    slippage_values = [
                        quantity * (open_price - trade_price),
                        quantity * (close_price - trade_price),
                        quantity * (twap_price - trade_price),
                        quantity * (vwap_price - trade_price),
                        quantity
                        * (hwoe_price - trade_price)
                        * adjustment_factor,  # Apply adjustment factor only for "All Trades"
                    ]

                for price_type, slippage_value in zip(price_types, slippage_values):
                    slippage_matrix.at[
                        price_type, days_after_trade[days_counted]
                    ] += slippage_value
            days_counted += 1

    return slippage_matrix.to_dict()


def calculate_blockhouse_pe(data, trans_code):
    if trans_code.lower() == "buy":
        return data["Low"].min()
    elif trans_code.lower() == "sell":
        return data["High"].max()
    else:
        return np.nan


# Create trade options for the dropdown
def calculate_slippage_trade_option(trade_blotter_filtered):
    trade_options = ["All Trades"] + [
        # f"{idx}: {row['Trans Code']} {row['Quantity']} @ ${row['Price']}"
        f"{idx}: {row['Instrument']} {row['Trans Code']} {row['Quantity']} @ ${row['Price']} on {row['Activity Date']}"
        for idx, row in trade_blotter_filtered.iterrows()
    ]
    return trade_options


# Candle Stick Chart
def find_trade_time(filtered_data, trade_date, trade_price):
    # Ensure the index is a DatetimeIndex
    if not isinstance(filtered_data.index, pd.DatetimeIndex):
        filtered_data = filtered_data.set_index("Datetime")

    # Filter the data to include only rows from the trade date
    day_data = filtered_data[filtered_data.index.date == trade_date.date()]

    # Check if trade price exactly matches any 'Open', 'High', 'Low', or 'Close' price
    trade_time = None
    for column in ["Open", "High", "Low", "Close"]:
        if not day_data[day_data[column].round(2) == round(trade_price, 2)].empty:
            trade_time = day_data[
                day_data[column].round(2) == round(trade_price, 2)
            ].index[0]
            break

    # If exact match is not found, find the closest price
    if trade_time is None and not day_data.empty:
        trade_time = day_data.iloc[
            (day_data[["Open", "High", "Low", "Close"]] - trade_price)
            .abs()
            .min(axis=1)
            .argsort()[:1]
        ].index[0]
    elif trade_time is None and day_data.empty:
        print("Day Data is empty")

    return trade_time


def identify_optimal_points(filtered_data, trade_datetime, trans_code):
    # Ensure the index is a DatetimeIndex
    if not isinstance(filtered_data.index, pd.DatetimeIndex):
        filtered_data = filtered_data.set_index("Datetime")

    start_plot_date = trade_datetime - timedelta(days=3)
    end_plot_date = trade_datetime + timedelta(days=3)

    before_trade = filtered_data.loc[start_plot_date:trade_datetime]
    after_trade = filtered_data.loc[trade_datetime:end_plot_date]

    if trans_code.lower() == "buy":
        optimal_before = before_trade["Low"].min() if not before_trade.empty else None
        optimal_before_date = (
            before_trade["Low"].idxmin() if not before_trade.empty else None
        )
        optimal_after = after_trade["Low"].min() if not after_trade.empty else None
        optimal_after_date = (
            after_trade["Low"].idxmin() if not after_trade.empty else None
        )
    elif trans_code.lower() == "sell":
        optimal_before = before_trade["High"].max() if not before_trade.empty else None
        optimal_before_date = (
            before_trade["High"].idxmax() if not before_trade.empty else None
        )
        optimal_after = after_trade["High"].max() if not after_trade.empty else None
        optimal_after_date = (
            after_trade["High"].idxmax() if not after_trade.empty else None
        )
    else:
        optimal_before = optimal_before_date = optimal_after = optimal_after_date = None

    return optimal_before, optimal_after, optimal_before_date, optimal_after_date


def plot_slippage_analysis(
    filtered_data,
    trade_datetime,
    trade_price,
    optimal_before,
    optimal_after,
    optimal_before_date,
    optimal_after_date,
    slippage_before,
    slippage_after,
    trans_code,
):

    start_plot_date = trade_datetime - timedelta(days=1)
    end_plot_date = trade_datetime + timedelta(days=1)

    if not isinstance(filtered_data.index, pd.DatetimeIndex):
        filtered_data = filtered_data.set_index("Datetime")

    plot_data = filtered_data.loc[start_plot_date:end_plot_date]

    # Convert the index to string for JSON serialization
    plot_data.index = plot_data.index.astype(str)

    results = {
        "plot_data": plot_data.to_dict(
            orient="index"
        ),  # Convert DataFrame to dictionary for JSON
        "optimal_before": optimal_before,
        "optimal_after": optimal_after,
        "optimal_before_date": optimal_before_date,
        "optimal_after_date": optimal_after_date,
        "slippage_before": slippage_before,
        "slippage_after": slippage_after,
        "trade_date": trade_datetime,
        "trade_price": trade_price,
        "trans_code": trans_code,
    }

    return results


def candle_stick_trade_option(trade_blotter_filtered):
    trade_options = [
        f"{idx}: {row['Instrument']} {row['Trans Code']} {row['Quantity']} @ ${row['Price']} on {row['Activity Date']}"
        for idx, row in trade_blotter_filtered.iterrows()
    ]
    return trade_options


def setup_slippage_analysis(
    trade_blotter_filtered, data_dict, selected_trade, selected_benchmarks="All"
):

    benchmark_options = [
        "Open_Price",
        "Close_Price",
        "TWAP_Price",
        "VWAP_Price",
        "HWOE_Price",
    ]

    trade_index = int(selected_trade.split(":")[0])
    trade_details = trade_blotter_filtered.loc[trade_index]
    ticker = trade_details["Instrument"]
    trade_date = trade_details["Activity Date"]
    trans_code = trade_details["Trans Code"]
    trade_price = trade_details["Price"]

    market_data = data_dict[ticker]

    if "Datetime" not in market_data.columns:
        market_data = market_data.reset_index()
        market_data.rename(columns={"index": "Datetime"}, inplace=True)

    trade_datetime = find_trade_time(market_data, trade_date, trade_price)
    if not trade_datetime:
        raise Exception("trade_datetime is None")
    optimal_before, optimal_after, optimal_before_date, optimal_after_date = (
        identify_optimal_points(market_data, trade_datetime, trans_code)
    )

    slippage_before = None
    slippage_after = None

    if trans_code.lower() == "buy":
        slippage_before = trade_price - optimal_before if optimal_before else None
        slippage_after = trade_price - optimal_after if optimal_after else None
    elif trans_code.lower() == "sell":
        slippage_before = optimal_before - trade_price if optimal_before else None
        slippage_after = optimal_after - trade_price if optimal_after else None

    result_data = plot_slippage_analysis(
        market_data,
        trade_datetime,
        trade_price,
        optimal_before,
        optimal_after,
        optimal_before_date,
        optimal_after_date,
        slippage_before,
        slippage_after,
        trans_code,
    )

    if "All" in selected_benchmarks:
        selected_benchmarks = benchmark_options
    benchmark_prices = preprocess_benchmark_prices(
        trade_details, result_data["plot_data"], selected_benchmarks
    )
    slippage_data = collect_slippage_data(trade_details, benchmark_prices)

    result_data.update(
        {"Benchmark_Prices": benchmark_prices, "Slippage_Data": slippage_data}
    )

    return result_data


def preprocess_benchmark_prices(trade_details, plot_data, selected_benchmarks):
    plot_data = pd.DataFrame.from_dict(plot_data, orient="index")
    plot_data.index = pd.to_datetime(plot_data.index)

    trade_date = pd.to_datetime(trade_details["Activity Date"])
    daily_data = plot_data[plot_data.index.date == trade_date.date()]

    benchmark_prices = {}
    if not daily_data.empty:
        if "Open_Price" in selected_benchmarks:
            benchmark_prices["Open_Price"] = daily_data["Open"].iloc[0]
        if "Close_Price" in selected_benchmarks:
            benchmark_prices["Close_Price"] = daily_data["Close"].iloc[-1]
        if "TWAP_Price" in selected_benchmarks:
            benchmark_prices["TWAP_Price"] = daily_data["Close"].mean()
        if "VWAP_Price" in selected_benchmarks:
            benchmark_prices["VWAP_Price"] = (
                daily_data["Close"] * daily_data["Volume"]
            ).sum() / daily_data["Volume"].sum()
        if "HWOE_Price" in selected_benchmarks:
            if trade_details["Trans Code"].lower() == "buy":
                benchmark_prices["HWOE_Price"] = daily_data["Close"].min()
            elif trade_details["Trans Code"].lower() == "sell":
                benchmark_prices["HWOE_Price"] = daily_data["Open"].max()

    return benchmark_prices


def collect_slippage_data(trade_details, benchmark_prices):
    trade_price = trade_details["Price"]
    trans_code = trade_details["Trans Code"]
    slippage_data = {}

    for benchmark, price in benchmark_prices.items():
        slippage = (
            price - trade_price if trans_code.lower() == "buy" else trade_price - price
        )
        slippage_data[benchmark] = {"Benchmark Price": price, "Slippage": slippage}

    return slippage_data


# Bar chart
def calculate_slippage_sums(
    trade_data, selected_trade="All Trades", hwoe_adjustment_factor=0.25
):
    slippage_types = [
        "Slippage_Open",
        "Slippage_Close",
        "Slippage_TWAP",
        "Slippage_VWAP",
        "Slippage_HWOE",
    ]
    strategies = ["Open", "Close", "TWAP", "VWAP", "HWOE"]

    if selected_trade != "All Trades":
        trade_index = int(selected_trade.split(":")[0])
        trades = trade_data.loc[[trade_index]]
    else:
        trades = trade_data

    # Calculate the sum of slippage for each strategy
    slippage_sums = {}
    for strategy, slippage_type in zip(strategies, slippage_types):
        if strategy == "HWOE":
            slippage_sums[strategy] = (
                -(trades[slippage_type] * trades["Quantity"]).sum()
                * hwoe_adjustment_factor
            )
        else:
            slippage_sums[strategy] = -(
                trades[slippage_type] * trades["Quantity"]
            ).sum()

    return slippage_sums


def calculate_slippage_sums_plaid(
    trade_data, selected_trade="All Trades", hwoe_adjustment_factor=0.25
):
    slippage_types = [
        "Slippage_Open",
        "Slippage_Close",
        "Slippage_TWAP",
        "Slippage_VWAP",
        "Slippage_HWOE",
    ]
    strategies = ["Open", "Close", "TWAP", "VWAP", "HWOE"]

    print("Trade data: ", trade_data)

    if selected_trade != "All Trades":
        try:
            trade_index = int(selected_trade.split(":")[0])
            trades = trade_data.loc[[trade_index]]
        except (ValueError, KeyError):
            print("Invalid selected_trade format or index not found in trade_data.")
            return None
    else:
        trades = trade_data

    # Calculate the sum of slippage for each strategy
    slippage_sums = {}
    for strategy, slippage_type in zip(strategies, slippage_types):
        if strategy == "HWOE":
            slippage_sums[strategy] = (
                trades[slippage_type] * trades["Quantity"] * hwoe_adjustment_factor
            ).sum()
        else:
            slippage_sums[strategy] = (trades[slippage_type] * trades["Quantity"]).sum()

    return slippage_sums


# Create trade options for the dropdown
def calculate_slippage_bar_trade_option(trade_blotter_filtered):
    trade_options = ["All Trades"] + [
        f"{idx}: {row['Instrument']} {row['Trans Code']} {row['Quantity']} @ ${row['Price']} on {row['Activity Date']}"
        for idx, row in trade_blotter_filtered.iterrows()
    ]
    return trade_options


def convert_nan_to_null(data):
    """_summary_
    Convert NaN values to None in a JSON-serializable data structure

    Args:
      data (dict): The data structure to convert

    Returns:
      dict: The data structure with NaN values replaced by None
    """
    data = convert_timestamps(data)
    json_str = json.dumps(data)
    cleaned_json_str = re.sub(r"\bNaN\b", "null", json_str)
    return json.loads(cleaned_json_str)


def convert_timestamps(obj):
    """_summary_
    Convert pandas Timestamp objects to ISO 8601 strings in a JSON-serializable data structure

    Args:
      obj (dict): The data structure to convert

    Returns:
      dict: The data structure with Timestamp objects converted to ISO 8601 strings
    """
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: convert_timestamps(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_timestamps(i) for i in obj]
    return obj
