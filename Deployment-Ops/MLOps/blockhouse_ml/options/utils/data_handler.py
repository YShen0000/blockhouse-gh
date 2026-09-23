
import pandas as pd
import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm
import os

from more_itertools import chunked
from joblib import Parallel, delayed
from statsmodels.tsa.api import ARIMA, ExponentialSmoothing
from arch import arch_model
from tqdm import tqdm  # Import tqdm for progress tracking
import time

from blockhouse_ml.options.utils.fetch_merge_data import DataClient

class TechnicalIndicators:
    def __init__(self):
        pass
    def simulate_adjusted_price_paths(self, S0, T, dt, n_paths, iv):
        if T <= 0:
            return np.array([])  # Handle the case when T is 0 or negative

        dt = min(dt, T)  # Adjust dt to not exceed T
        N = max(1, int(T / dt))  # Ensure at least one step

        paths = np.zeros((n_paths, N))
        for i in range(n_paths):
            paths[i, 0] = S0
            for t in range(1, N):
                Z = np.random.standard_normal()
                paths[i, t] = paths[i, t-1] * np.exp((0 - 0.5 * iv**2) * dt + iv * np.sqrt(dt) * Z)

        return paths


    def calculate_transaction_costs(self, paths, eta, phi, k):
        transaction_costs = np.zeros(paths.shape[0])
        for i in range(paths.shape[0]):
            for t in range(1, paths.shape[1]):
                rho = paths[i, t] - paths[i, t-1]
                execution_cost = eta * np.abs(rho)**(1 + phi)
                market_impact = k * np.abs(rho)
                transaction_costs[i] += execution_cost + market_impact
        average_transaction_cost = np.mean(transaction_costs)
        return average_transaction_cost
    
    def add_technical_indicators(self,data, option_type="C", strike_price=100):
        #process the data to have the following columns
        data['mid_price'] = (data['ask_price'] + data['bid_price'])/2
        data['rfr'] = 0.03909 # It is always be constant across contracts because it is not related to options fluctuations

        data['implied_vol'] = np.nan
        data['delta'] = 0
        data['theta'] = 0
        data['gamma'] = 0
        data['vega'] = 0

        data['option_type'] = option_type
        data['transaction_cost'] = 0.0  # Initialize the column with 0.0
        
        for idx, row in tqdm(data.iterrows()):
            # iv = row['Implied_Volatility'] / 100  # Convert IV from percentage to decimal
            S = row['adj_close']
            T = row['time_to_maturity'] / 365.0  # Convert time to maturity from days to years
            K = strike_price #self.parse_strike_from_contract(row['contract'], option_type=option_type)
            market_price = row['mid_price']
            rfr = row['rfr']

            # Calculate delta
            # try:
            iv = self.implied_volatility(S, K, T, rfr, market_price)
            delta, gamma, theta, vega = self.calculate_greeks(S, K, T, rfr, iv)
            # except Exception as e:
            #     delta, gamma, theta, vega = np.nan, np.nan, np.nan, np.nan
            #     print(f"Error calculating greeks for row {idx}: {e}")

            data.at[idx, 'implied_vol'] = iv
            data.at[idx, 'delta'] = delta
            data.at[idx, 'gamma'] = gamma
            data.at[idx, 'theta'] = theta
            data.at[idx, 'vega'] = vega

            # Handle missing data or invalid values
            if pd.isnull(S) or pd.isnull(iv) or pd.isnull(T) or T <= 0:
                print(f"Skipping row {idx} due to missing or invalid data.")
                continue
            iv = iv / 100  # Convert IV from percentage to decimal
            paths = self.simulate_adjusted_price_paths(S, T, 1/252, 10, iv)
            transaction_cost = self.calculate_transaction_costs(paths, 0.01, 0.852, 0.001)
            
            data.at[idx, 'transaction_cost'] = transaction_cost
        
        return data
    def parse_strike_from_contract(self, contract, option_type="C"):
        # Assuming the format is always similar to "AAPL 240823C00220000"
        # where the strike price starts after the last non-numeric character before a long number
        part = contract.split(option_type)[-1]  # Splits at 'C' and takes the last part
        strike_price = int(part) / 1000  # Converts to an integer and assumes format needs dividing to match market conventions
        return strike_price

    def black_scholes_call(self, S, K, T, r, sigma):
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

    def calculate_greeks(self, S, K, T, r, sigma):
        if T == 0:  # Handle the T = 0 case
            intrinsic_value = max(0, S - K)
            return np.nan, 1.0 if S > K else 0.0 if S < K else np.nan, 0, 0
        else:
            h = 0.01
            call_price = self.black_scholes_call(S, K, T, r, sigma)
            delta = (self.black_scholes_call(S + h, K, T, r, sigma) - call_price) / h
            gamma = (self.black_scholes_call(S + h, K, T, r, sigma) - 2 * call_price + self.black_scholes_call(S - h, K, T, r, sigma)) / h**2
            theta = (self.black_scholes_call(S, K, T - 1/365, r, sigma) - call_price) / (1/365)
            vega = (self.black_scholes_call(S, K, T, r, sigma + 0.01) - call_price) / 0.01
            return delta, gamma, theta, vega

    def implied_volatility(self, S, K, T, r, market_price):
        if T == 0:
            return np.nan  # Undefined implied volatility for T = 0
        tolerance = 1e-5
        max_iterations = 1000
        sigma_low, sigma_high = 0.01, 4.0
        for i in range(max_iterations):
            sigma_mid = (sigma_low + sigma_high) / 2
            price_mid = self.black_scholes_call(S, K, T, r, sigma_mid)
            if price_mid > market_price:
                sigma_high = sigma_mid
            else:
                sigma_low = sigma_mid
            if abs(price_mid - market_price) < tolerance:
                return sigma_mid
        return sigma_mid  # Return the best estimate after max iterations

class DataProcessor:
    def __init__(self):
        self.r = 0.05
        self.rfr = 0.03909
        self.technical_indicators = TechnicalIndicators()
    

    def process_data(self, data, option_type="C", strike_price=100, window_size=100, n_jobs=-1, forecast_steps=None):
        
        print("Processing data...")

        if forecast_steps is None:
            forecast_steps = {
                'open': (180, '1T'),
                'high': (180, '1T'),
                'low': (180, '1T'),
                'close': (180, '1T'),
                'volatility': (180, '1T'),
                'volume': (180, '1T'),
                'transaction_cost': (180, '1T'),
                'gamma': (180, '1T'),
                'delta': (180, '1T'),
                'theta': (180, '1T'),
                'vega': (180, '1T'),
                'implied_vol': (180, '1T'),
                'time_to_maturity': (180, '1T'),
                'mid_price': (180, '1T'),
            }
        df = self.technical_indicators.add_technical_indicators(data,option_type=option_type,strike_price=strike_price)
        

        forecasted_data = self.train_and_forecast_parallel(df, forecast_steps, window_size, n_jobs)
        combined_data = df.join(forecasted_data)

    #     combined_data.drop(['forecast_open_open',
    #    'forecast_high_high', 'forecast_low_low', 'forecast_close_close', 'forecast_volume_volume',
    #    'forecast_transaction_cost_transaction_cost'], axis=1, inplace=True)
        print("Data processed, Successfully!")
        return combined_data

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
                        # row_forecasts[f'forecast_{indicator}_{key}'] = None
                        continue

                    # if indicator in ['open', 'high', 'low', 'close', 'transaction_cost', 'gamma', 'delta', 'theta', 'vega', 'rho', 'implied_vol', 'time_to_maturity', 'mid_price']:
                    #     pass
                    #     # model = ExponentialSmoothing(series, trend='add', seasonal=None)
                    # # elif indicator == 'volatility':
                    # #     model = ARIMA(series, order=(5, 1, 0))
                    # elif indicator == 'volume':
                    #     shift = 1 if series.min() <= 0 else 0
                    #     transformed_series = np.log(series + shift + 1)
                        # model = ExponentialSmoothing(transformed_series, trend='add', seasonal=None)
                    # model_fit = model.fit()

                    # forecast_values = model_fit.forecast(steps=steps)
                    row_forecasts[f'forecast_3Hr_{indicator}'] = series.mean() # forecast_values.iloc[-1] #series.mean() 

                except Exception as e:
                    row_forecasts[f'forecast_3Hr_{indicator}'] = None

        return row_forecasts

    # def forecast_last_row(data, forecast_steps, columns, window_size):
    #     last_idx = len(data) - 1
    #     row_forecasts = {}
    #     for indicator, column in columns.items():
    #         steps, freq = forecast_steps[indicator]
    #         start_idx = max(0, last_idx - window_size)
    #         series = data[column].iloc[start_idx:last_idx+1]
    #         if len(series) < 2:
    #             row_forecasts[f'forecast_{indicator}'] = None
    #             continue
    #         forecast_value = series.mean()
    #         row_forecasts[f'forecast_3Hr_{indicator}'] = forecast_value
    #     return pd.Series(row_forecasts)

    def train_and_forecast_parallel(self,data, forecast_steps, window_size, n_jobs=-1):
        columns = {
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'transaction_cost': 'transaction_cost',
            'gamma': 'gamma',
            'delta': 'delta',
            'theta': 'theta',
            'vega': 'vega',
            'implied_vol': 'implied_vol',
            'time_to_maturity': 'time_to_maturity',
            'mid_price': 'mid_price',
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

        # results = []
        # for idx_set in tqdm(chunk_set, desc="Processing rows"):
        #     results.append(call_forecast_row(idx_set, data, forecast_steps, columns, window_size))

        forecast_results = pd.concat(results).set_index('timestamp')

        
        return forecast_results

class DataHandler():
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.data_client = DataClient(data_dir)
        self.data_processor = DataProcessor()

    def check_valid_contract(self, companies):
        """
        Checks if the contracts are valid or not.

        Parameters
        ----------
        companies : list of dict
            list of dictionaries containing the contract information
            each dict should have the following keys:
                ticker (str): the ticker of the underlier
                maturity_date (str): the maturity date of the option
                option_type (str): the type of the option, either 'C' or 'P'
                strike_price (float): the strike price of the option

        Returns
        -------
        None
        """
        for contract_info in companies:
            p_contract, databento_contract = self.data_client.get_contract_name(contract_info['ticker'],contract_info['maturity_date'],contract_info['option_type'],contract_info['strike_price'])
            # print(p_contract, databento_contract)
            if not self.data_client.check_valid_option(p_contract, start_time):
                print(f'{p_contract} not valid')

    def get_data(self, option_data, start_time, end_time, n_jobs=-1):
        """
        Get data for a list of companies and dates.

        Parameters
        ----------
        option_data : dictionary containing the contract information
            dict should have the following keys:
                ticker (str): the ticker of the underlier
                maturity_date (str): the maturity date of the option
                option_type (str): the type of the option, either 'C' or 'P'
                strike_price (float): the strike price of the option
        start_time : str
            start time of the data
        end_time : str
            end time of the data

        Returns
        -------
        pd.DataFrame
            dataframe containing the data
        """
        ## Fetch and process the data and save it to the data directory, if it doesn't exist
        quote_dir = os.path.join(self.data_dir, option_data["ticker"]) 
        os.makedirs(quote_dir, exist_ok=True)
        quote_filenames = os.listdir(quote_dir)
        
        processed_data = pd.DataFrame()
        

        processed_filename = f'{self.data_dir}/processed_data_{option_data["ticker"]}_{start_time}_{end_time}.csv'
        if os.path.exists(processed_filename):
            processed_data = pd.read_csv(processed_filename)
        else:

            quote_paths = []

            print("Checking if data exists in local directory : ",quote_dir)
            for filename in quote_filenames:
                quote_paths.append(os.path.join(quote_dir, filename))
            
            if len(quote_paths) == 0:
                print("No data found in local directory : ",quote_dir)
            else:
                print("Data found in local directory : ",quote_paths)
                
        
            filename = f'{self.data_dir}/merged_data_{option_data["ticker"]}_{start_time}_{end_time}.csv'
            if os.path.exists(filename):
                data = pd.read_csv(filename)
            else:
                data = self.data_client.fetch_and_merge_data(option_data["ticker"],start_date=start_time,end_date=end_time,quotes_paths=quote_paths, maturity_date=option_data['maturity_date'],option_type=option_data['option_type'],strike_price=option_data['strike_price'])
                if not data.empty:
                    data.to_csv(filename)
            if not data.empty:
                processed_data = self.data_processor.process_data(data,option_type=option_data['option_type'],strike_price=option_data['strike_price'],n_jobs=n_jobs)
                processed_data.dropna(inplace=True)
                processed_data.to_csv(processed_filename)

        return processed_data

    def get_market_cap(self,ticker):
        return self.data_client.get_market_cap(ticker)


class InferenceDataHandler():
    def __init__(self):
        pass
    
    def add_forecast(self, data):
        """
        Adds forecasts for various indicators to the data.

        Args:
        - data (pd.DataFrame): The DataFrame with technical indicators.

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
                if indicator in ['open', 'high', 'low', 'close', 'transaction_cost', 'delta','gamma', 'theta','vega',
                                'rho','implied_vol','time_to_maturity','mid_price','rfr']:
                    model = ExponentialSmoothing(series, trend='add', seasonal=None)
            
                model_fit = model.fit()
                forecast_values = model_fit.forecast(steps=steps)
            
                row_forecasts[f'forecast_3Hr_{indicator}'] = forecast_values.iloc[-1]
            return pd.Series(row_forecasts)

        forecast_steps = {
            'open': (180, '1T'),
            'high': (180, '1T'),
            'low': (180, '1T'),
            'close': (180, '1T'),
            'transaction_cost': (180, '1T'),
            'delta': (180, '1T'),
            'gamma': (180, '1T'),
            'theta': (180, '1T'),
            'vega': (180, '1T'),
            'implied_vol': (180, '1T'),
            'time_to_maturity': (180, '1T'),
            'mid_price': (180, '1T'),
            'rfr': (180, '1T')
        }
        columns = {col: col for col in forecast_steps}
        last_row_forecast = forecast_last_row(data, forecast_steps, columns, 300)
        
        last_row_df = data.iloc[-1].to_frame().T.reset_index(drop=True)
        last_row_forecast_df = last_row_forecast.to_frame().T.reset_index(drop=True)
        input_row = pd.concat([last_row_df, last_row_forecast_df], axis=1)

        return input_row

    def add_real_time_forecasts(self, data, step, model_type="macro"):
        def dynamic_forecast(data, step):
            """
            Generates a dynamic forecast for a set of indicators using historical data.

            The function forecasts various financial indicators such as OHLC (Open, High, Low, Close),
            volume, volatility, and technical indicators like RSI, MACD, etc., based on the past data.

            The forecasts are generated using either Exponential Smoothing or ARIMA models, depending on the indicator.

            Args:
            - data (pd.DataFrame): The historical market data.
            - step (int): The forecast step, indicating how far into the future the prediction should be made.

            Returns:
            - pd.DataFrame: A DataFrame containing the forecasted values for the last row in the dataset.
            """
            
            def forecast_last_row(data, forecast_steps, columns, window_size):
                """
                Forecasts the last row of data based on the given columns and their forecast steps.

                Args:
                - data (pd.DataFrame): The historical market data.
                - forecast_steps (dict): A dictionary specifying the forecast steps and frequency for each indicator.
                - columns (dict): A dictionary mapping each indicator to its corresponding column name in the data.
                - window_size (int): The number of past observations to consider for forecasting.

                Returns:
                - tuple: Two DataFrames, one for the row-level forecast and another for the state forecast.
                """
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
                    if indicator in ['ask_price', 'ask_size', 'bid_price', 'bid_size', 'open', 'high', 'low',
                    'close', 'volume', 'adj_close', 'time_to_maturity', 'mid_price', 'rfr',
                    'implied_vol', 'option_type', 'delta', 'gamma', 'theta', 'vega', 'rho',
                    'transaction_cost']:
                        model = ExponentialSmoothing(series, trend='add', seasonal=None)
        #             elif indicator == '5_min_TC' or indicator == 'transaction_cost':
        #                 model = ARIMA(series, order=(5, 1, 0))
        #             elif indicator == 'volume' or indicator == '5_min_volume':
        #                 shift = 1 if series.min() <= 0 else 0
        #                 transformed_series = np.log(series + shift + 1)
        #                 model = ExponentialSmoothing(transformed_series, trend='add', seasonal=None)
                    
                    # Fit the model and generate forecast
                    model_fit = model.fit()
                    forecast_values = model_fit.forecast(steps=steps)
                    
                    if indicator == 'volume':
                        shift = 1 if series.min() <= 0 else 0
                        forecast_values = np.exp(forecast_values) - 1 - shift
                        forecast_values[forecast_values < 0] = 0  # Ensure non-negative values
                    # if indicator in ['volume', 'adj_close']:
                    state_forecasts[f'{indicator}'] = series.mean()
                    # else:
                        # Add forecast to state_forecast (for specific future step)
                    # state_forecasts[f'{indicator}'] = forecast_values.iloc[step-1]
                        
                    # Add future OHLCV to row_forecasts (e.g., forecast for the last step in 6 hours)
                    if indicator in ['close', 'transaction_cost', 'delta','gamma', 'theta','vega',
                                        'rho','implied_vol','time_to_maturity','mid_price','rfr', 'open', 'high', 'low']:
                        row_forecasts[f'forecast_3Hr_{indicator}'] = series.mean() #forecast_values.iloc[-1]
                
                # Create DataFrames for row-level and state forecasts
                row_forecasts_df = pd.DataFrame([row_forecasts]).reset_index(drop=True)
                state_forecasts_df = pd.DataFrame([state_forecasts]).reset_index(drop=True)
                
                return row_forecasts_df, state_forecasts_df

            # Define forecast steps and frequency for various indicators
            forecast_steps = {
                'ask_price': (step, '1T'),
                'ask_size': (step, '1T'),
                'bid_price': (step, '1T'),
                'bid_size': (step, '1T'),
                'open': (step, '1T'),
                'high': (step, '1T'),
                'low': (step, '1T'),
                'close': (step + 180, '1T'),
                'volume': (step + 180, '1T'),
                'adj_close': (step + 180, '1T'),
                'transaction_cost': (step + 180, '1T'),
                'delta': (step + 180, '1T'),
                'gamma': (step + 180, '1T'),
                'theta': (step + 180, '1T'),
                'vega': (step + 180, '1T'),
                'implied_vol': (step + 180, '1T'),
                'time_to_maturity': (step + 180, '1T'),
                'mid_price': (step + 180, '1T'),
                'rfr': (step + 180, '1T'),
            }
            
            # Map indicators to corresponding columns in the data
            columns = {col: col for col in forecast_steps}
            
        # Forecast the last row and state for the given data
            last_row_forecast, data_forecast = forecast_last_row(data, forecast_steps, columns, 300)
            
            # Combine the two DataFrames into a single input row
            input_row = pd.concat([data_forecast, last_row_forecast], axis=1)
            
            return input_row

        input_row = dynamic_forecast(data, step)
        # print(input_row)
        return input_row