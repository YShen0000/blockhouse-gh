from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np
import os
import datetime
import pytz
import joblib


import pandas as pd
from databento import Historical
import time
from datetime import datetime, time as dt_time, timedelta


def fetch_data(ticker="AAPL", start_date="2023-07-01", end_date="2023-10-31",data_dir="data"):
    # Replace with your actual DataBento API key
    API_KEY = 'db-s8TQsSX8JF539yQSeBWFGPNyDx4m3'
    client = Historical(key=API_KEY)

    output_filepath = os.path.join(data_dir,f'AAPL_{start_date}_{end_date}.csv')
    if os.path.exists(output_filepath):
        print(f"File {output_filepath} already exists, skipping download")
        return output_filepath
     
    print(f"Fetching data for {ticker} from {start_date} to {end_date}")
    # Define trading hours in UTC (Standard Time conversion, adjust as needed for Daylight Saving Time)
    trading_start_utc = dt_time(13, 30)  # 09:30 AM ET is 13:30 UTC during Daylight Saving Time
    trading_end_utc = dt_time(20, 0)     # 04:00 PM ET is 20:00 UTC during Daylight Saving Time

    # Helper function to fetch second-level bid/ask data using Market by Price (MBP) schema
    def fetch_second_level_quotes(ticker, start_time, end_time):
        try:
            # Fetch Market by Price data
            response = client.timeseries.get_range(
                dataset="XNAS.ITCH",  # Correct dataset for NASDAQ equities
                symbols=[ticker],
                start=start_time,
                end=end_time,
                schema="mbp-1",  # Schema for Market by Price, top level only
            )

            # Check if the response is empty
            if not response:
                print(f"No data found for the given date range: {start_time} to {end_time}")
                return pd.DataFrame()

            # Convert the response to a DataFrame
            df_mbp = response.to_df()

            # Check if the DataFrame is empty
            if df_mbp.empty:
                print(f"No data found for the given date range: {start_time} to {end_time}")
                return pd.DataFrame()

            # remove the rows whose action column has C action
            df_mbp = df_mbp[df_mbp['action'] != 'C']

            # Extract the relevant columns and remove NaN rows
            df_mbp_cleaned = df_mbp.dropna(subset=['bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00'])

            # Sort by timestamp to ensure correct order
            df_mbp_cleaned = df_mbp_cleaned.sort_values(by='ts_event')

            # Format the DataFrame to have a consistent structure
            quotes = df_mbp_cleaned[['ts_event', 'bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00']]
            quotes.columns = ['timestamp', 'bid_price', 'ask_price', 'bid_size', 'ask_size']

            # Convert timestamps to datetime
            quotes['timestamp'] = pd.to_datetime(quotes['timestamp'], unit='ns')

            quotes = quotes[(quotes['bid_size'] > 0) & (quotes['ask_size'] > 0)]
            # Filter data within trading hours only (UTC)
            quotes = quotes[quotes['timestamp'].dt.time.between(trading_start_utc, trading_end_utc)]

            return quotes

        except Exception as e:
            print(f"Error fetching quotes: {e}")
            return pd.DataFrame()

    # Function to aggregate data to minute-level, selecting top 5 bid and ask prices
    def aggregate_to_minute(df):
        # Ensure data is sorted by timestamp
        df.sort_values(by='timestamp', inplace=True)

        # Group by each minute
        df['minute'] = df['timestamp'].dt.floor('min')

        aggregated_data = []

        for minute, group in df.groupby('minute'):
            # Sort bid prices descending and ask prices ascending
            group.drop_duplicates(subset=['bid_price', 'ask_price'], keep='last', inplace=True)
            top_bids = group[['bid_price', 'bid_size']].sort_values(by='bid_price', ascending=False)
            top_asks = group[['ask_price', 'ask_size']].sort_values(by='ask_price', ascending=True)

            # Prepare data for the current minute
            minute_data = {
                'timestamp': minute,
                # Extract 5 highest bids and corresponding sizes
                **{f'bid_price_{i+1}': top_bids.iloc[i]['bid_price'] if i < len(top_bids) else None for i in range(5)},
                **{f'bid_size_{i+1}': top_bids.iloc[i]['bid_size'] if i < len(top_bids) else None for i in range(5)},
                # Extract 5 lowest asks and corresponding sizes
                **{f'ask_price_{i+1}': top_asks.iloc[i]['ask_price'] if i < len(top_asks) else None for i in range(5)},
                **{f'ask_size_{i+1}': top_asks.iloc[i]['ask_size'] if i < len(top_asks) else None for i in range(5)},
            }

            aggregated_data.append(minute_data)

        # Convert to DataFrame
        return pd.DataFrame(aggregated_data)

    # Fetch and process data for the entire date range
    all_data = []
    date_range = pd.date_range(start=start_date, end=end_date)

    for date in date_range:
        date_str = date.strftime('%Y-%m-%d')
        print(f"Fetching data for {date_str}...")

        # Define the start and end times for the day
        start_time = int(pd.Timestamp(f"{date_str}T00:00:00Z").timestamp() * 1_000_000_000)  # start time in nanoseconds
        end_time = int(pd.Timestamp(f"{date_str}T23:59:59Z").timestamp() * 1_000_000_000)    # end time in nanoseconds

        # Fetch second-level NBBO data
        df_quotes = fetch_second_level_quotes(ticker, start_time, end_time)
        df_quotes.to_csv("raw_quotes_data.csv")
        time.sleep(1)  # Pause to respect rate limits

        # Aggregate data to minute-level with 5 highest bids and 5 lowest asks
        if not df_quotes.empty:
            df_aggregated = aggregate_to_minute(df_quotes)
            all_data.append(df_aggregated)

    # Combine all data into a single DataFrame
    if all_data:
        final_df = pd.concat(all_data)

        # Display the first few rows
        print(final_df.head())

        # Save to CSV for further analysis
        final_df.to_csv(output_filepath, index=False)
    else:
        print("No data available to concatenate.")
    
    return output_filepath

def process_data(data, name="AAPL", cols=["bid_size", "bid_price", "ask_price", "ask_size"], train=True):
    processor_savepath=f"processor_{name}.pkl"

    if train:
        processor = StandardScaler()
        process_data = processor.fit_transform(data[cols]) 
        
        joblib.dump(processor, processor_savepath)
    else:
        if os.path.exists(processor_savepath):
            processor = joblib.load(processor_savepath)
            process_data = processor.transform(data[cols])
        else:
            raise Exception(f"Processor not found at specified path : {processor_savepath}, please fit the model first")
    processed_columns = [f"processed_{col}" for col in cols]

    df_processed = pd.DataFrame(process_data, columns=processed_columns, index=data.index)
    
    return pd.concat([data, df_processed], axis=1)

if __name__ == '__main__':
    ticker = "aapl"

    start_date = '2024-07-01'
    end_date = '2024-07-05'
    # Replace with your actual DataBento API key
    API_KEY = 'db-s8TQsSX8JF539yQSeBWFGPNyDx4m3'
    client = Historical(key=API_KEY)

    # output_filepath = os.path.join(data_dir,f'AAPL_{start_date}_{end_date}.csv')
    # if os.path.exists(output_filepath):
    #     print(f"File {output_filepath} already exists, skipping download")
    #     return output_filepath

    print(f"Fetching data for {ticker} from {start_date} to {end_date}")
    # Define trading hours in UTC (Standard Time conversion, adjust as needed for Daylight Saving Time)
    trading_start_utc = dt_time(13, 30)  # 09:30 AM ET is 13:30 UTC during Daylight Saving Time
    trading_end_utc = dt_time(20, 0)  # 04:00 PM ET is 20:00 UTC during Daylight Saving Time

    # Helper function to fetch second-level bid/ask data using Market by Price (MBP) schema
    def fetch_second_level_quotes(ticker, start_time, end_time):
        try:
            # Fetch Market by Price data
            response = client.timeseries.get_range(
                dataset="XNAS.ITCH",  # Correct dataset for NASDAQ equities
                symbols=[ticker],
                start=start_time,
                end=end_time,
                schema="mbp-1",  # Schema for Market by Price, top level only
            )

            # Check if the response is empty
            if not response:
                print(f"No data found for the given date range: {start_time} to {end_time}")
                return pd.DataFrame()

            # Convert the response to a DataFrame
            df_mbp = response.to_df()

            # Check if the DataFrame is empty
            if df_mbp.empty:
                print(f"No data found for the given date range: {start_time} to {end_time}")
                return pd.DataFrame()

            # remove the rows whose action column has C action
            df_mbp = df_mbp[df_mbp['action'] != 'C']

            # Extract the relevant columns and remove NaN rows
            df_mbp_cleaned = df_mbp.dropna(subset=['bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00'])

            # Sort by timestamp to ensure correct order
            df_mbp_cleaned = df_mbp_cleaned.sort_values(by='ts_event')

            # Format the DataFrame to have a consistent structure
            quotes = df_mbp_cleaned[['ts_event', 'bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00']]
            quotes.columns = ['timestamp', 'bid_price', 'ask_price', 'bid_size', 'ask_size']

            # Convert timestamps to datetime
            quotes['timestamp'] = pd.to_datetime(quotes['timestamp'], unit='ns')

            quotes = quotes[(quotes['bid_size'] > 0) & (quotes['ask_size'] > 0)]
            # Filter data within trading hours only (UTC)
            quotes = quotes[quotes['timestamp'].dt.time.between(trading_start_utc, trading_end_utc)]

            return quotes

        except Exception as e:
            print(f"Error fetching quotes: {e}")
            return pd.DataFrame()

    # Function to aggregate data to minute-level, selecting top 5 bid and ask prices
    def aggregate_to_minute(df):
        # Ensure data is sorted by timestamp
        df.sort_values(by='timestamp', inplace=True)

        # Group by each minute
        df['minute'] = df['timestamp'].dt.floor('min')

        aggregated_data = []

        for minute, group in df.groupby('minute'):
            # Sort bid prices descending and ask prices ascending
            group.drop_duplicates(subset=['bid_price', 'ask_price'], keep='last', inplace=True)
            top_bids = group[['bid_price', 'bid_size']].sort_values(by='bid_price', ascending=False)
            top_asks = group[['ask_price', 'ask_size']].sort_values(by='ask_price', ascending=True)

            # Prepare data for the current minute
            minute_data = {
                'timestamp': minute,
                # Extract 5 highest bids and corresponding sizes
                **{f'bid_price_{i+1}': top_bids.iloc[i]['bid_price'] if i < len(top_bids) else None for i in range(5)},
                **{f'bid_size_{i+1}': top_bids.iloc[i]['bid_size'] if i < len(top_bids) else None for i in range(5)},
                # Extract 5 lowest asks and corresponding sizes
                **{f'ask_price_{i+1}': top_asks.iloc[i]['ask_price'] if i < len(top_asks) else None for i in range(5)},
                **{f'ask_size_{i+1}': top_asks.iloc[i]['ask_size'] if i < len(top_asks) else None for i in range(5)},
            }

            aggregated_data.append(minute_data)

        # Convert to DataFrame
        return pd.DataFrame(aggregated_data)

    # Fetch and process data for the entire date range
    all_data = []
    date_range = pd.date_range(start=start_date, end=end_date)
    quaoted_data =[]
    for date in date_range:
        date_str = date.strftime('%Y-%m-%d')
        print(f"Fetching data for {date_str}...")

        # Define the start and end times for the day
        start_time = int(pd.Timestamp(f"{date_str}T00:00:00Z").timestamp() * 1_000_000_000)  # start time in nanoseconds
        end_time = int(pd.Timestamp(f"{date_str}T23:59:59Z").timestamp() * 1_000_000_000)  # end time in nanoseconds

        # Fetch second-level NBBO data
        df_quotes = fetch_second_level_quotes(ticker, start_time, end_time)
        df_quotes.to_csv("raw_quotes_data.csv")
        time.sleep(1)  # Pause to respect rate limits

        # Aggregate data to minute-level with 5 highest bids and 5 lowest asks
        if not df_quotes.empty:
            df_aggregated = aggregate_to_minute(df_quotes)
            quaoted_data.append(df_quotes)
            all_data.append(df_aggregated)

    # Combine all data into a single DataFrame
    if all_data:
        final_df = pd.concat(all_data)

        # Display the first few rows
        print(final_df.head())

        # Save to CSV for further analysis
        final_df.to_csv(output_filepath, index=False)
    else:
        print("No data available to concatenate.")

