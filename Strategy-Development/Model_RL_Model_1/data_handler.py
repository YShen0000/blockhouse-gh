from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np
import os
import datetime
import pytz
import joblib
import logging
import time
import warnings

from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tools.sm_exceptions import ValueWarning
from databento import Historical
from datetime import datetime, time as dt_time, timedelta
from pandas.tseries.holiday import USFederalHolidayCalendar


warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)
warnings.filterwarnings("ignore", category=ValueWarning)

def fetch_data(ticker="AAPL", start_date="2023-07-01", end_date="2023-10-31",data_dir="data"):
    # Replace with your actual DataBento API key
    API_KEY = 'db-s8TQsSX8JF539yQSeBWFGPNyDx4m3'
    client = Historical(key=API_KEY)

    output_filepath = os.path.join(data_dir,f'{ticker}_{start_date}_{end_date}.csv')
    if os.path.exists(output_filepath):
        print(f"File {output_filepath} already exists, skipping download")
        return output_filepath
     
    print(f"Fetching data for {ticker} from {start_date} to {end_date}")
    # Define trading hours in UTC (Standard Time conversion, adjust as needed for Daylight Saving Time)
    trading_start_utc = dt_time(13, 30)  # 09:30 AM ET is 13:30 UTC during Daylight Saving Time
    trading_end_utc = dt_time(20, minute=1)     # 04:00 PM ET is 20:00 UTC during Daylight Saving Time

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
            top_bids = group[['bid_price', 'bid_size']].sort_values(by='bid_price', ascending=False).head(5)
            top_asks = group[['ask_price', 'ask_size']].sort_values(by='ask_price', ascending=True).head(5)

            # Prepare data for the current minute, multiplying sizes by 100
            minute_data = {
                'timestamp': minute,
                # Extract 5 highest bids and corresponding sizes
                **{f'bid_price_{i+1}': top_bids.iloc[i]['bid_price'] if i < len(top_bids) else None for i in range(5)},
                **{f'bid_size_{i+1}': top_bids.iloc[i]['bid_size']  if i < len(top_bids) else None for i in range(5)},
                # Extract 5 lowest asks and corresponding sizes
                **{f'ask_price_{i+1}': top_asks.iloc[i]['ask_price'] if i < len(top_asks) else None for i in range(5)},
                **{f'ask_size_{i+1}': top_asks.iloc[i]['ask_size']  if i < len(top_asks) else None for i in range(5)},
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

def process_data(data, name="AAPL", start_date="2023-07-01", end_date="2023-10-31", cols=["bid_size", "bid_price", "ask_price", "ask_size"], train=True, data_dir="Data"):
    processor_savepath= os.path.join(data_dir, f"processor_{name}_{start_date}_{end_date}.pkl")
    if train:
        processor = StandardScaler()
        # print(cols)
        # print(data.columns)
        # print(data[cols])
        processed_data = processor.fit_transform(data[cols]) 
        
        joblib.dump(processor, processor_savepath)
    else:
        if os.path.exists(processor_savepath):
            processor = joblib.load(processor_savepath)
            processed_data = processor.transform(data[cols])
        else:
            raise Exception(f"Processor not found at specified path : {processor_savepath}, please fit the model first")
    processed_columns = [f"processed_{col}" for col in cols]
  
    df_processed = pd.DataFrame(processed_data, columns=processed_columns, index=data.index)
    df = pd.concat([data, df_processed], axis=1)
    return df

class DataHandler:
    def __init__(self, data_dir):
        self.data_dir = data_dir

    def get_data(self, ticker="AAPL", start_date="2023-07-01", end_date="2023-10-31", split_train_test=False):
        data_filepath = fetch_data(ticker, start_date, end_date, self.data_dir)

        data = pd.read_csv(data_filepath)
        data.dropna(inplace=True)
        data.set_index("timestamp", inplace=True)

        train_data = data[:int(len(data) * 0.8)]
        test_data = data[int(len(data) * 0.8):]

        processed_data = process_data(data, name=ticker, start_date=start_date, end_date=end_date, cols=data.columns, train=True, data_dir=self.data_dir)
        if split_train_test:
            processed_train_data = process_data(train_data, name=ticker, start_date=start_date, end_date=end_date, cols=data.columns, train=True, data_dir=self.data_dir)
            processed_test_data = process_data(test_data, name=ticker, start_date=start_date, end_date=end_date, cols=data.columns, train=False, data_dir=self.data_dir)
            return processed_train_data, processed_test_data

            # processed_test_data.reset_index(inplace=True)
            # processed_train_data.reset_index(inplace=True)
        # processed_train_data
        return (processed_data,None) #processed_train_data, processed_test_data


class InferenceDataHandler:
    def __init__(self, data_dir):
        self.data_dir = data_dir

    def get_data(self, ticker="AAPL", start_date="2023-07-01", end_date="2023-10-31", timeframe = 390):
        """
        timeframe from where the trading time is taken till the end of the day.
        Reason being that forecast is done on whole day basis, so the timeframe should be less than 390, it will be use like this:
            inference_data = forecast_df[-timeframe:]
        """
        day_timeframe = 390
        end_date = self.get_trading_day(end_date)
        start_date = self.get_trading_day(start_date)

        print(f"Fetching data for {ticker} from {start_date} to {end_date}")
        data_filepath = fetch_data(ticker, start_date, end_date, self.data_dir)

        data = pd.read_csv(data_filepath)
        data.dropna(inplace=True)
        data.set_index("timestamp", inplace=True)

        latest_timestamp = pd.to_datetime(data.index[-1])
        forecasted_timeframes = self.generate_forecast_timestamps(day_timeframe, latest_timestamp)

        forecasted_df = self.add_real_time_forecasts(data, forecasted_timeframes)
        # print(forecasted_df.iloc[-5:], forecasted_df.iloc[-1])
        inference_data = forecasted_df.iloc[-timeframe:]
        inference_data.set_index("timestamp", inplace=True)   

        inference_data.dropna(inplace=True)
        assert inference_data.columns.tolist() == data.columns.tolist()

        processed_data = process_data(inference_data, name=ticker, start_date=start_date, end_date=end_date, cols=inference_data.columns, train=True, data_dir=self.data_dir)

        return processed_data
    
    def get_trading_day(self, day_of_backtest):
        """
        Given a backtest day, return the most recent trading day before the current day.
        
        Parameters
        ----------
        day_of_backtest : str
            The day of backtest in 'YYYY-MM-DD' format.
        
        Returns
        -------
        str
            The most recent trading day before the backtest day in 'YYYY-MM-DD' format.
        """
        
        backtest_datatime_obj = datetime.strptime(day_of_backtest, '%Y-%m-%d')
        # print(backtest_datatime_obj)
            
        # Need to get data from trading day before backtest so there are no Nan values due to rolling averages
        cal = USFederalHolidayCalendar() # Get federal holidays
        holidays = cal.holidays(start=backtest_datatime_obj - pd.DateOffset(years=1), end=backtest_datatime_obj + pd.DateOffset(years=1)) # Holidays for year of date
        data = None
        days_prior = 1 # Number of days before backtest day (most recent trading day)
        while True:
            previous_trading_day = (backtest_datatime_obj - timedelta(days=days_prior)).strftime('%Y-%m-%d')
            # print(previous_trading_day)
            previous_trading_day_datetime = pd.to_datetime(previous_trading_day)
            if (previous_trading_day_datetime.weekday() >= 5) or (previous_trading_day_datetime in holidays): # Weekend or federal holiday
                days_prior += 1 
            else:
                # print(previous_trading_day)
                break
        
        return previous_trading_day

    def generate_forecast_timestamps(self,timeframe, latest_timestamp):
        # Initialize an empty list to store valid timestamps
        valid_timestamps = []
        current_timestamp = latest_timestamp
        cal = USFederalHolidayCalendar() 
        holidays = cal.holidays(start=current_timestamp - pd.DateOffset(years=1), end=current_timestamp + pd.DateOffset(years=1))
        # print(holidays)
        # Generate valid timestamps
        while len(valid_timestamps) < timeframe:
            current_timestamp += timedelta(minutes=1)
            
            # Check if it's a weekday and within the specified time range
            if (current_timestamp.weekday() < 5 and 
                dt_time(13, 30) <= current_timestamp.time() <= dt_time(20, 0)):
                valid_timestamps.append(current_timestamp)
            
            # If we've passed 20:00, move to the next day at 13:30
            if current_timestamp.time() > dt_time(20, 0):
                next_day = current_timestamp.date() + timedelta(days=1)
                current_timestamp = pd.Timestamp.combine(next_day, dt_time(13, 30))
                
                # If it's a weekend, move to Monday
                while (current_timestamp.weekday() >= 5) or (current_timestamp in holidays):
                    current_timestamp += timedelta(days=1)

        # # Create a DataFrame with valid timestamps and forecasted values
        # df = pd.DataFrame({
        #     'Timestamp': valid_timestamps[:timeframe],
        #     'Forecast': forecasted_values
        # })

        return valid_timestamps[:timeframe]

    def add_real_time_forecasts(self, original_data, forecast_timestamps):
        """Generates forecasts for the next 'forecast_period' minutes using ARIMA."""
        forecasts = {}

        forecast_period = len(forecast_timestamps)
        for col in original_data.columns:
            if 'bid_' in col or 'ask_' in col:
                logging.info(f"Generating forecast for {col}...")
                try:
                    model = ARIMA(original_data[col], order=(5, 1, 0))
                    model_fit = model.fit()
                    forecast = model_fit.forecast(steps=forecast_period)
                    forecasts[col] = forecast.values
                except Exception as e:
                    logging.error(f"Error forecasting {col}: {e}")
                    forecasts[col] = [None] * forecast_period

        forecasts['timestamp'] = forecast_timestamps
        forecast_df = pd.DataFrame(forecasts)
        logging.info(f"Generated forecasts:\n{forecast_df}")
        return forecast_df
