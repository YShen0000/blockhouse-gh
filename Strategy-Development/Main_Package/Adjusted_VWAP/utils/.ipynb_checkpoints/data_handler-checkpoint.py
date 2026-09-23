import sys
import os
# Define Tech Indicators
import pandas as pd
import numpy as np
import talib as ta
import numpy as np
import math
from collections import defaultdict

from joblib import Parallel, delayed
from statsmodels.tsa.api import ARIMA, ExponentialSmoothing
from arch import arch_model
from tqdm import tqdm  # Import tqdm for progress tracking
import time
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import BDay

from Adjusted_VWAP.utils.fetch_merge_data import fetch_and_merge_data
from more_itertools import chunked

# start_time = '2024-07-07'
# end_time = '2024-08-07'
# ticker = 'AAPL'

# filename = f'merged_data_{ticker}_{start_time}_{end_time}.csv'
# if os.path.exists(filename):
#     data = pd.read_csv(filename)
# else:
#     data = fetch_and_merge_data('AAPL','2024-07-07','2024-08-07')


class TechnicalIndicators:
    def __init__(self, data):
        """
        Initializes the TechnicalIndicators class with the provided data.

        Parameters:
        - data: A pandas DataFrame containing financial data with columns like 'close', 'high', 'low', 'volume', etc.
        """
        self.data = data

    def add_momentum_indicators(self):
        """
        Adds momentum indicators such as RSI, MACD, and Stochastic Oscillator to the data.
        """
        # Relative Strength Index (RSI)
        self.data['RSI'] = ta.RSI(self.data['close'], timeperiod=14)
        
        # Moving Average Convergence Divergence (MACD)
        self.data['MACD'], self.data['MACD_signal'], self.data['MACD_hist'] = ta.MACD(
            self.data['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        
        # Stochastic Oscillator
        self.data['Stoch_k'], self.data['Stoch_d'] = ta.STOCH(
            self.data['high'], self.data['low'], self.data['close'], fastk_period=14, slowk_period=3, slowd_period=3)

    def add_volume_indicators(self):
        """
        Adds volume indicators such as On-Balance Volume (OBV) to the data.
        """
        # On-Balance Volume (OBV)
        self.data['OBV'] = ta.OBV(self.data['close'], self.data['volume'])
        
    def add_TC(self):
        window_size = 5
        self.data['mid_price'] = (self.data['high'] + self.data['low']) / 2
        self.data["mean_vol"] = self.data['mid_price'].pct_change().rolling(window=window_size).mean()
        self.data["mean_liq"] = self.data['volume'].rolling(window=window_size).mean()
        self.data = self.data.iloc[35:,:]


        # AC Calculation -> 
        x0 = 5000  # Initial number of shares to trade
        T = 1.0    # Total time horizon (e.g., 1 day)
        N = min(x0, 2400)  # Number of discrete time intervals
        eta = 0.0000001    # Temporary/permanent impact coefficient
        sigma = 0.02       # Volatility of the asset
        lambda_ = 0.1      # Risk aversion parameter

        # Time interval
        dt = 1

        # Cost function for the Almgren-Chriss model
        def cost_function(x, eta, sigma, x0=10):
            x_cumsum = np.cumsum(x)
            x_half = x / 2

            temp_cost = np.sum(eta * (x**2) / dt)
            perm_cost = np.sum(eta * x * (x0 - x_cumsum + x_half))
            var_cost = np.sum(lambda_ * sigma**2 * (x**2) * dt)

            return (1 / (temp_cost + perm_cost + var_cost) / x0) * 10**(math.log10(x0) * 4 - 6)

        def almgren(row):
            x0 = 5000
            N = min(x0, 2400)

            eta = 1 / row['mean_liq'] if row['mean_liq'] != 0 else 0.0000001
            sigma = row['mean_vol']

            # Initial guess: trade evenly across all intervals
            x_init = np.ones(N) * (x0 / N)

            return cost_function(x_init, eta, sigma, x0) / x0
        
        self.data['transaction_cost'] = self.data.apply(almgren, axis=1)

    def add_volatility_indicators(self):
        """
        Adds volatility indicators such as Bollinger Bands and Average True Range (ATR) to the data.
        """
        # Bollinger Bands
        self.data['Upper_BB'], self.data['Middle_BB'], self.data['Lower_BB'] = ta.BBANDS(self.data['close'], timeperiod=20)
        
        # Average True Range (ATR) for different periods
        self.data['ATR_1'] = ta.ATR(self.data['high'], self.data['low'], self.data['close'], timeperiod=1)
        self.data['ATR_2'] = ta.ATR(self.data['high'], self.data['low'], self.data['close'], timeperiod=2)
        self.data['ATR_5'] = ta.ATR(self.data['high'], self.data['low'], self.data['close'], timeperiod=5)
        self.data['ATR_10'] = ta.ATR(self.data['high'], self.data['low'], self.data['close'], timeperiod=10)
        self.data['ATR_20'] = ta.ATR(self.data['high'], self.data['low'], self.data['close'], timeperiod=20)
        
    def add_volatility(self, window=15):
        """
        Adds dynamic volatility calculation using log returns and a rolling window.

        Parameters:
        - window: The rolling window size for calculating volatility (default is 15).
        """
        # Log returns
        self.data['log_return'] = np.log(self.data['close'] / self.data['close'].shift(1))
        
        # Rolling volatility
        self.data['volatility'] = self.data['log_return'].rolling(window=window).std() * np.sqrt(window)

    def add_trend_indicators(self):
        """
        Adds trend indicators such as ADX, +DI, -DI, and CCI to the data.
        """
        # Average Directional Index (ADX)
        self.data['ADX'] = ta.ADX(self.data['high'], self.data['low'], self.data['close'], timeperiod=14)
        
        # Plus Directional Indicator (+DI)
        self.data['+DI'] = ta.PLUS_DI(self.data['high'], self.data['low'], self.data['close'], timeperiod=14)
        
        # Minus Directional Indicator (-DI)
        self.data['-DI'] = ta.MINUS_DI(self.data['high'], self.data['low'], self.data['close'], timeperiod=14)
        
        # Commodity Channel Index (CCI)
        self.data['CCI'] = ta.CCI(self.data['high'], self.data['low'], self.data['close'], timeperiod=5)
        
    def add_5_min_indicators(self):
        # code to add 5 mins volume, volatility, TC
        self.data['5_min_volatility'] = self.data['volatility'].transform(lambda x: x.rolling(window=5).std())
        self.data['5_min_volume'] = self.data['volume'].transform(lambda x: x.rolling(window=5).sum())
        self.data['5_min_TC'] = self.data['transaction_cost'].shift(5)

    def add_other_indicators(self):
        """
        Adds other indicators such as DLR, TWAP, VWAP, market liquidity, and expected price to the data.
        """
        # Daily Log Returns (DLR)
        self.data['DLR'] = np.log(self.data['close'] / self.data['close'].shift(1))
        
        # Time-Weighted Average Price (TWAP)
        self.data['TWAP'] = self.data['close'].expanding().mean()
        
        # Volume-Weighted Average Price (VWAP)
        self.data['VWAP'] = (self.data['volume'] * (self.data['high'] + self.data['low']) / 2).cumsum() / self.data['volume'].cumsum()
        
        # Market Liquidity
        # self.data['market_liquidity'] = self.data['bid_size'] + self.data['ask_size']
        
        # Expected Price
        # self.data['expected_price'] = self.data['bid_price']
        

    def add_all_indicators(self):
        """
        Adds all the defined indicators to the data.
        
        Returns:
        - The updated DataFrame with all indicators added.
        """
        self.add_momentum_indicators()
        self.add_volume_indicators()
        self.add_volatility_indicators()
        self.add_trend_indicators()
        self.add_other_indicators()
        self.add_volatility()
        self.add_TC()
        self.add_5_min_indicators()
        return self.data

class DataProcessor():
    def __init__(self):
        pass
    def forecast_row(self,idx, data, forecast_steps, columns, window_size):
        row_forecasts = {}
        row_forecasts['timestamp'] = data.index[idx]

        for indicator, column in columns.items():
            for key, (steps, freq) in forecast_steps.items():
                if indicator not in key:
                    continue
                try:
                    # Use a sliding window
                    start_idx = max(0, idx - window_size)
                    series = data[column].iloc[start_idx:idx+1]
                    if len(series) < 2:
                        row_forecasts[f'forecast_{indicator}_{key}'] = None
                        continue

                    if indicator in ['open', 'high', 'low', 'close', 'transaction_cost']:
                        model = ExponentialSmoothing(series, trend='add', seasonal=None)
                    elif indicator == 'volatility':
                        model = ARIMA(series, order=(5, 1, 0))
                    elif indicator == 'volume':
                        shift = 1 if series.min() <= 0 else 0
                        transformed_series = np.log(series + shift + 1)
                        model = ExponentialSmoothing(transformed_series, trend='add', seasonal=None)
                    model_fit = model.fit()

                    forecast_values = model_fit.forecast(steps=steps)
                    row_forecasts[f'forecast_6Hr_{indicator}'] = forecast_values.iloc[-1]

                except Exception as e:
                    row_forecasts[f'forecast_6Hr_{indicator}'] = None

        return row_forecasts

    def train_and_forecast_parallel(self,data, forecast_steps, window_size, n_jobs=-1):
        columns = {
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volatility': 'volatility',
            'volume': 'volume',
            'transaction_cost': 'transaction_cost'
        }
        
        # print('Starting...')
        # Add tqdm progress bar
        # results = Parallel(n_jobs=n_jobs)(delayed(self.forecast_row)(idx, data, forecast_steps, columns, window_size) for idx in tqdm(range(len(data)), desc="Processing rows"))
        # forecast_results = pd.DataFrame(results).set_index('timestamp')
        def call_forecast_row(idx_set, data, forecast_steps, columns, window_size):
            res = []
            for idx in idx_set:
                part = self.forecast_row(idx, data, forecast_steps, columns, window_size)
                res.append(part)
            return pd.DataFrame(res)

        chunk_set = chunked(range(len(data)), int(len(data) / 32))
        results = Parallel(n_jobs=n_jobs)(
            delayed(call_forecast_row)(idx_set, data, forecast_steps, columns, window_size) for idx_set in
            tqdm(chunk_set, desc="Processing rows"))

        forecast_results = pd.concat(results).set_index('timestamp')

        
        return forecast_results

    def add_technical_indicators(self, data):
        # Create an instance of TechnicalIndicators
        indicators = TechnicalIndicators(data)

        # Add all indicators
        data_with_indicators = indicators.add_all_indicators()

        # Discard NaN values 
        data_filtered = data_with_indicators.dropna()

        return data_filtered

    def process_data(self, data, forecast_steps=None, window_size=100, n_jobs=-1):        
        """
        Process data by generating forecasts for various indicators and combining them with the original data.

        Args:
            data (pd.DataFrame): The input data to be processed.
            forecast_steps (dict): A dictionary containing the forecast steps for each indicator.
            window_size (int, optional): The size of the sliding window. Defaults to 100.(last 100 observations)
            n_jobs (int, optional): The number of jobs to run in parallel. Defaults to -1.

        Returns:
            pd.DataFrame: The combined data with forecasted values.
        """

        data_filtered = self.add_technical_indicators(data)

        start_time = time.time()
        if forecast_steps is None:
            forecast_steps = {
                'open': (360, '1T'),
                'high': (360, '1T'),
                'low': (360, '1T'),
                'close': (360, '1T'),
                'volatility': (360, '1T'),
                'volume': (360, '1T'),
                'transaction_cost': (360, '1T')
            }

        forecasted_data = self.train_and_forecast_parallel(data_filtered, forecast_steps, window_size, n_jobs)

        end_time = time.time()
        elapsed_time = end_time - start_time

        # # Fill/drop NaN values
        # forecasted_data = forecasted_data.fillna(method='ffill').fillna(method='bfill')

        # Combine the forecasted data
        combined_data = data_filtered.join(forecasted_data)
        # print(combined_data.head())
        # print(f"Elapsed time: {elapsed_time:.2f} seconds")

        combined_data.drop(['forecast_open_open',
       'forecast_high_high', 'forecast_low_low', 'forecast_close_close',
       'forecast_volatility_volatility', 'forecast_volume_volume',
       'forecast_transaction_cost_transaction_cost'], axis=1, inplace=True)

        data_processed = combined_data.iloc[1:]
        data_processed = data_processed.fillna(method='ffill').fillna(method='bfill')

        return data_processed

class InferenceDataHandler():
    """
    DataHandler class for inference.
    Generates forecasts for various financial indicators using current step data.
    """
    
    def __init__(self):
        pass

    def create_data_w_forecasts(self, data, steps = 390):
        """
        Adds OHLCV forecasts for 390 steps (1 min intervals) to the data with UTC timestamps within trading hours.

        Args:
        - data (pd.DataFrame): The DataFrame with OHLCV data.

        Returns:
        - pd.DataFrame: The DataFrame with additional forecasted values for 390 steps.
        """
        print("LOGGING: Adding 390-step OHLCV Forecasts to data...")

        def forecast_data(data, forecast_steps, columns, window_size):
            forecasts = defaultdict(list)
            last_idx = len(data) - 1
            row_forecasts = {}
            for indicator, column in columns.items():
                steps = forecast_steps[indicator]
                start_idx = max(0, last_idx - window_size)
                print(data.columns)
                series = data[column].iloc[start_idx:last_idx+1]
                
                # Use Exponential Smoothing for all OHLC and Volume
                model = ExponentialSmoothing(series, trend='add', seasonal=None)
                model_fit = model.fit()
                forecast_values = model_fit.forecast(steps=steps)

                forecasts[column] = forecast_values
                
            return pd.DataFrame(forecasts)

        def generate_trading_hours_timestamps(start_timestamp, forecast_steps):
            start_timestamp = pd.Timestamp(start_timestamp, tz='UTC')
            
            # Initialize holiday calendar
            cal = USFederalHolidayCalendar()
            holidays = cal.holidays(start=start_timestamp, end=start_timestamp + pd.Timedelta(days=365))

            # Trading hours in UTC: 13:30 to 20:00 (equivalent to 9:30 AM - 4:00 PM EST)
            trading_start_utc = start_timestamp.replace(hour=13, minute=30, second=0)
            trading_end_utc = start_timestamp.replace(hour=20, minute=0, second=0)
            print(f'Current time: {trading_start_utc}')
            timestamps = []
            current_time = start_timestamp
            
            while len(timestamps) < forecast_steps+1:
                # Check if current day is a holiday or weekend
                if current_time.date() in holidays or current_time.weekday() >= 5:
                    # Move to next business day
                    current_time = (current_time + BDay(1)).replace(hour=13, minute=30, second=0)
                    trading_end_utc = current_time.replace(hour=20, minute=0, second=0)
                elif current_time <= trading_end_utc:
                    timestamps.append(current_time)
                    current_time += pd.Timedelta(minutes=1)
                else:
                    # Move to next business day
                    current_time = (current_time + BDay(1)).replace(hour=13, minute=30, second=0)
                    trading_end_utc = current_time.replace(hour=20, minute=0, second=0)
            
            return timestamps[1:forecast_steps+1]

        # Set forecast to 390 steps for each OHLCV component (1-minute interval)
        forecast_steps = {
            'open': steps,
            'high': steps,
            'low': steps,
            'close': steps,
            'volume': steps
        }

        columns = {col: col for col in forecast_steps}
        new_data = forecast_data(data, forecast_steps, columns, 300)  # Use 300 as the window size
        
        # Generate future timestamps within trading hours (adjusted to UTC)
        last_timestamp = data.datetime.iloc[-1]
        print(f'Last timestamP: {last_timestamp}')
        forecast_timestamps = generate_trading_hours_timestamps(last_timestamp, steps)

        # Assign the generated timestamps to the forecast data
        new_data['datetime'] = forecast_timestamps
        new_data.reset_index(drop=True, inplace=True)
        return new_data

    def add_forecasts(self,data):
        """
        Adds forecasts for various indicators to the data.

        Args:
        - data (pd.DataFrame): The DataFrame with technical indicators.
        - model_type (str, optional): The type of model to use for forecasting. Defaults to "macro".

        Returns:
        - pd.DataFrame: The DataFrame with additional forecasted values.
        """
        print("LOGGING: Adding Forecasts to data...")
        

        def forecast_last_row(data, forecast_steps, columns, window_size):
            last_idx = len(data) - 1
            row_forecasts = {}
            for indicator, column in columns.items():
                steps, freq = forecast_steps[indicator]
                start_idx = max(0, last_idx - window_size)
                series = data[column].iloc[start_idx:last_idx+1]
                if len(series) < 2:
                    row_forecasts[f'forecast_{indicator}'] = None
                    continue
                if indicator in ['open', 'high', 'low', 'close', 'transaction_cost']:
                    model = ExponentialSmoothing(series, trend='add', seasonal=None)
                elif indicator == 'volatility':
                    model = ARIMA(series, order=(5, 1, 0))
                elif indicator == 'volume':
                    shift = 1 if series.min() <= 0 else 0
                    transformed_series = np.log(series + shift + 1)
                    model = ExponentialSmoothing(transformed_series, trend='add', seasonal=None)
                model_fit = model.fit()
                forecast_values = model_fit.forecast(steps=steps)
                if indicator == 'volume':
                    forecast_values = np.exp(forecast_values) - 1 - shift
                    forecast_values[forecast_values < 0] = 0  # Ensure non-negative values
                row_forecasts[f'forecast_6Hr_{indicator}'] = forecast_values.iloc[-1]
            return pd.Series(row_forecasts)

        forecast_steps = {
            'open': (390, '1T'),
            'high': (390, '1T'),
            'low': (390, '1T'),
            'close': (390, '1T'),
            'volume': (390, '1T'),
        }
            
        columns = {col: col for col in forecast_steps}
        last_row_forecast = forecast_last_row(data, forecast_steps, columns, 300)
        
        last_row_df = data.iloc[-1].to_frame().T.reset_index(drop=True)
        last_row_forecast_df = last_row_forecast.to_frame().T.reset_index(drop=True)
        input_row = pd.concat([last_row_df, last_row_forecast_df], axis=1)

        return input_row

    # data_testing.set_index('datetime', inplace=True)


    def add_real_time_forecasts(self, data, step, model_type="macro"):
        """
        Adds real-time forecasts for the next step in the trading process.

        Args:
        - data (pd.DataFrame): The DataFrame with technical indicators.
        - step (int): The forecast step indicating how far into the future to predict.
        - model_type (str, optional): The type of model for forcast to generate. Defaults to "macro", option between "macro" and "micro".

        Returns:
        - pd.DataFrame: The input row with real-time forecasts.
        """
        # print("LOGGING: Adding Real-Time Forecasts to data...")
        
        # from statsmodels.tsa.holtwinters import ExponentialSmoothing
        # from statsmodels.tsa.arima.model import ARIMA

        def dynamic_forecast(data, step, model_type="macro"):
            """
            Generates a dynamic forecast for a set of indicators using historical data.

            Args:
            - data (pd.DataFrame): The historical market data.
            - step (int): The forecast step, indicating how far into the future the prediction should be made.
            - model_type (str, optional): The type of model for forcast to generate. Defaults to "macro", option between "macro" and "micro".

            Returns:
            - pd.DataFrame: A DataFrame containing the forecasted values for the last row in the dataset.
            """

            def forecast_last_row(data, forecast_steps, columns, window_size):
                last_idx = len(data) - 1
                row_forecasts = {'timestamp': data.index[last_idx]}
                state_forecasts = {}

                for indicator, column in columns.items():
                    steps, freq = forecast_steps[indicator]
                    start_idx = max(0, last_idx - window_size)
                    series = data[column].iloc[start_idx:last_idx+1]

                    # If insufficient data, skip forecast for this indicator
                    if len(series) < 2:
                        row_forecasts[f'forecast_{indicator}'] = None
                        continue

                    # Select appropriate model based on the indicator
                    if indicator in ['open', 'high', 'low', 'close', 'RSI', 'MACD',
                                    'MACD_signal', 'MACD_hist', 'Stoch_k', 'Stoch_d', 'OBV', 'Upper_BB',
                                    'Middle_BB', 'Lower_BB', 'ATR_1', 'ATR_2', 'ATR_5', 'ATR_10', 'ATR_20',
                                    'ADX', '+DI', '-DI', 'CCI', 'expected_price']:
                        model = ExponentialSmoothing(series, trend='add', seasonal=None)
                    elif indicator == '5_min_TC' or indicator == 'transaction_cost':
                        model = ARIMA(series, order=(5, 1, 0))
    #                     elif indicator == 'volume' or indicator == '5_min_volume':
    #                         shift = 1 if series.min() <= 0 else 0
    #                         transformed_series = np.log(series + shift + 1)
    #                         model = ExponentialSmoothing(transformed_series, trend='add', seasonal=None)
                        
                    elif indicator == 'volume' or indicator == '5_min_volume':
                        shift = series.min() <= 0
                        transformed_series = np.log(series + shift + 1)
                        model = ExponentialSmoothing(transformed_series, trend='add', seasonal=None)
                    
                    elif indicator == 'volatility' or indicator == '5_min_volatility':
                        model = arch_model(series, mean='Constant', vol='Garch', p=1, q=1)
                        
                    
                    # Fit the model and generate forecast
                    if indicator == 'volatility' or indicator == '5_min_volatility':
                        model_fit = model.fit(disp='off')
                        forecast_values = model_fit.forecast(horizon=steps).variance.values[-1]
                    
                    elif indicator == 'volume' or indicator == '5_min_volume':
                        model_fit = model.fit()
                        forecast_values = model_fit.forecast(steps=steps)
                        forecast_values = np.exp(forecast_values) - 1 - shift
                        forecast_values[forecast_values < 0] = 1e-3  # Ensure small positive minimum
                        
                    else:
                        model_fit = model.fit()
                        forecast_values = model_fit.forecast(steps=steps)
    #                         forecast_values = np.exp(forecast_values) - 1 - shift
    #                         forecast_values[forecast_values < 0] = 0  # Ensure non-negative values
                    
                    if indicator == 'volume' or indicator == '5_min_volume':
                        state_forecasts[f'{indicator}'] = max(forecast_values.iloc[step-1], series.median())
                    elif indicator == 'volatility' or indicator == '5_min_volatility':
                        state_forecasts[f'{indicator}'] = np.sqrt(forecast_values[step-1])
                    else:
                        # Add forecast to state_forecast (for specific future step)
                        state_forecasts[f'{indicator}'] = forecast_values.iloc[step-1]

                    # Add future OHLCV to row_forecasts (e.g., forecast for the last step in 6 hours)
                    if indicator in ['open', 'high', 'low', 'close', 'transaction_cost']:
                        row_forecasts[f'forecast_6Hr_{indicator}'] = forecast_values.iloc[-1]
                    elif indicator in ['volume']:
                        row_forecasts[f'forecast_6Hr_{indicator}'] = max(forecast_values.iloc[-1], series.median())
                    elif indicator in ['volatility']:
                        row_forecasts[f'forecast_6Hr_{indicator}'] = np.sqrt(forecast_values[-1])

                # Create DataFrames for row-level and state forecasts
                row_forecasts_df = pd.DataFrame([row_forecasts]).reset_index(drop=True)
                state_forecasts_df = pd.DataFrame([state_forecasts]).reset_index(drop=True)

                return row_forecasts_df, state_forecasts_df

            forecast_steps = {
                'open': (step + 360, '1T'),
                'high': (step + 360, '1T'),
                'low': (step + 360, '1T'),
                'close': (step + 360, '1T'),
                'volume': (step + 360, '1T'),
                'volatility': (step + 360, '1T'),
                'transaction_cost': (step + 360, '1T'),
                'RSI': (step, '1T'),
                'MACD': (step, '1T'),
                'MACD_signal': (step, '1T'),
                'MACD_hist': (step, '1T'),
                'Stoch_k': (step, '1T'),
                'Stoch_d': (step, '1T'),
                'OBV': (step, '1T'),
                'Upper_BB': (step, '1T'),
                'Middle_BB': (step, '1T'),
                'Lower_BB': (step, '1T'),
                'ATR_1': (step, '1T'),
                'ADX': (step, '1T'),
                '+DI': (step, '1T'),
                '-DI': (step, '1T'),
                'CCI': (step, '1T'),
                '5_min_volatility': (step, '1T'),
                '5_min_volume': (step, '1T'),
                '5_min_TC': (step, '1T') # Add bid ask forecasts as well later
            }
            # if model_type == "micro":
            #     forecast_steps['expected_price'] = (step + 360, '1T')

            columns = {col: col for col in forecast_steps}
            last_row_forecast, data_forecast = forecast_last_row(data, forecast_steps, columns, 300)
            input_row = pd.concat([data_forecast, last_row_forecast], axis=1)
            return input_row

        input_row = dynamic_forecast(data, step, model_type)
        # print(input_row)
        return input_row
        
