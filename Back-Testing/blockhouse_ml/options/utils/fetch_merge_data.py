

from polygon import RESTClient
import pandas as pd
import os
import requests
from time import sleep
import multiprocessing
import numpy as np

import zstandard as zstd
import databento as db
from tqdm import tqdm
    
API_KEY = 'r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc'

DATABENTO_API_KEY = "db-eKU7cAt4iTryxUbycEY7REuXXkwcU"

def calculate_actual_price(bid_prices, bid_sizes):
    return (bid_prices * bid_sizes).sum() / bid_sizes.sum()

def calculate_spread_cost(bid_prices, ask_prices):
    return ask_prices.mean() - bid_prices.mean()


class PolygonClient:
    def __init__(self, save_dir, api_key=API_KEY):
        self.api_key = api_key
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        self.client = RESTClient(api_key)
    
    def fetch_and_merge_data(self, ticker, start_date, end_date, maturity_date, option_type= "C",strike_price=125):
        """
            Fetch and merge OHLCV and quote data for a given ticker and date range.

            Args:
                ticker (str): The underlying stock ticker.
                start_date (str): The start date of the date range in 'YYYY-MM-DD' format.
                end_date (str): The end date of the date range in 'YYYY-MM-DD' format.
                maturity_date (str): The expiration date of the option contract in 'YYMMDD' format.
                option_type (str, optional): The type of option contract (C for call, P for put). Defaults to "C".

            Returns:
                pd.DataFrame: The merged dataframe with OHLCV and quote data.

            Note:
                Contract format:
                The format is: O:UNDERLYING_TICKER_EXPIRATION_DATE_CALL/PUT_STRIKE_PRICE
                For example: O:AAPL210917C00125000
                Breaking this down:
                O: - Prefix indicating it's an option
                AAPL - Underlying stock ticker
                210917 - Expiration date (YYMMDD format)
                C - Call option (use P for put)
                00125000 - Strike price ($125.00 in this case)
        """
        self.contract = self.get_contract_name(ticker, maturity_date, option_type, strike_price)
        if not self.check_valid_option(self.contract, start_date):
            raise ValueError(f"Invalid option contract: {self.contract}")
        ohlcv = self.get_ohlcv(ticker, start_date, end_date)
        quotes = self.get_quote(start_date, end_date)

        df_merged  = pd.merge(ohlcv, quotes, on="timestamp", how='inner')
        df_merged.rename(columns={
            'Open':'open',
            'High':'high',
            'Low':'low',
            'Close':'close',
            'Volume':'volume',
            'Adj Close':'adj_close'
        }, inplace = True)
        df_merged['time_to_maturity'] = (pd.to_datetime(f'20{maturity_date}', format='%Y%m%d') - df_merged.index).days
        df_merged['contract'] = self.contract
        return df_merged

    def get_ohlcv(self, ticker, start_date, end_date):
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{start_date}/{end_date}"
        params = {
            "apiKey": self.api_key,
            "limit": 50000
        }
        response = requests.get(url, params=params)
        data = response.json()
        if 'results' in data:
            df = pd.DataFrame(data['results'])
            
            df['t'] = pd.to_datetime(df['t'], unit='ms')
            # df['t'] = df['t'].dt.tz_convert('US/Eastern')
            df['t'] = df['t'].dt.floor('min')
            df['timestamp'] = df['t']
            df.set_index('timestamp', inplace=True)
            df = df[['o', 'h', 'l', 'c', 'v']].rename(columns={ 
                'o': 'Open',
                'h': 'High',
                'l': 'Low',
                'c': 'Close',
                'v': 'Volume',
            })
            df['Adj Close'] = df['Close']  # Assuming Adj Close is the same as Close
            print(len(df))
            return df
        else:
            print(f"No OHLCV data found for {ticker}")
            
            return pd.DataFrame()
        
    def get_quote(self, start_date, end_date):
        def get_all_quotes(ticker, start_time, end_time):
            quotes = []
            next_url = f'https://api.polygon.io/v3/quotes/{ticker}'
            params = {
                "apiKey": self.api_key,
                "timestamp.gte": start_time.value,
                "timestamp.lte": end_time.value,
                "limit": 50000,
                "order": "asc",
                "sort": "timestamp"
            }

            while next_url:
                response = requests.get(next_url, params=params)
                response.raise_for_status()
                data = response.json()
                quotes.extend(data['results'])
                # print(len(quotes))
                
                next_url = data.get('next_url')
                if next_url:
                    params = {"apiKey": self.api_key}  # Reset params as next_url includes other parameters
                
                # Respect rate limits
                sleep(0.2)  # Wait 200ms between requests to avoid hitting rate limits

            return quotes
        def make_options_dataframe(start_date:str, end_date:str):
            
            # List Quotes
            # quotes = []
            # quote = self.client.list_quotes(ticker=ticker, timestamp_gte = start_date, timestamp_lt= end_date, sort='timestamp')
            # for value in quote:
            #     quotes.append(value)
            all_quotes = []
            print ("getting quotes --> ", start_date, end_date)

            # for date in tqdm(pd.date_range(start=start_date, end=pd.to_datetime(end_date), freq='D').strftime('%Y-%m-%d').tolist()):
            def get_day_quotes(date):
                day = pd.to_datetime(date)

                # Set start after 13:00
                start_time = day + pd.Timedelta(hours=13)
                day_quotes = []
                # Loop through each hour
                for n in range(8):  # 8 hours from 13:00 to 21:00
                    hour_start = start_time + pd.Timedelta(hours=n)
                    hour_end = hour_start + pd.Timedelta(hours=1)
                    
                    quotes = get_all_quotes(self.contract, hour_start, hour_end)
                    day_quotes.extend(quotes)

                return day_quotes
            # num_cores = multiprocessing.cpu_count()
            # with multiprocessing.Pool(num_cores-1) as p:
            #     all_quotes = p.map(get_day_quotes, pd.date_range(start=start_date, end=pd.to_datetime(end_date), freq='D').strftime('%Y-%m-%d').tolist())


            all_quotes = []

            for date in tqdm(pd.date_range(start=start_date, end=pd.to_datetime(end_date), freq='D').strftime('%Y-%m-%d').tolist()):
                all_quotes.extend(get_day_quotes(date))

            if len(all_quotes) == 0:
                raise ValueError(f"No quotes found for {self.contract} between {start_date} and {end_date}")
            # Create DataFrame
            df_quotes = pd.DataFrame(all_quotes)

            # ask_prices, ask_sizes, bid_prices, bid_sizes, timestamps = [0 for _ in range(len(quotes))], [0 for _ in range(len(quotes))], [0 for _ in range(len(quotes))], [0 for _ in range(len(quotes))], [0 for _ in range(len(quotes))]
            # for i in range(len(quotes)):
            #     ask_prices[i], ask_sizes[i], bid_prices[i], bid_sizes[i], timestamps[i] = quotes[i].ask_price, quotes[i].ask_size, quotes[i].bid_price, quotes[i].bid_size, quotes[i].sip_timestamp
            # ask_prices, ask_sizes, bid_prices, bid_sizes, timestamps = ask_prices[::-1], ask_sizes[::-1], bid_prices[::-1], bid_sizes[::-1], timestamps[::-1]

            # data = [
            #     {
            #         'ask_price': ask_prices,
            #         'ask_size': ask_sizes,
            #         'bid_price': bid_prices,
            #         'bid_size': bid_sizes,
            #         'sip_timestamp': timestamps
            #     },
            # ]

            # df = df.explode(list(df.columns))
            # print(df_quotes.columns)
            df_quotes.reset_index(drop=True, inplace=True)
            df_quotes['timestamp'] = pd.to_datetime(df_quotes['sip_timestamp'], unit='ns')

            # Remove timezone information and keep as datetime with only date, hour, and minute
            # df_quotes['timestamp'] = df_quotes['timestamp'].dt.floor('min')
            df_quotes['datetime'] = df_quotes['timestamp']
            df_quotes = df_quotes[['timestamp', 'ask_price', 'ask_size', 'bid_price', 'bid_size', 'datetime']]
            return df_quotes
        def resample_to_daily(data):
            # If you need to perform more complex calculations, you can use apply
            # Define a custom function to calculate spread cost
            def calculate_costs(group):
                # Calculate the average bid price and ask price for the minute
                bid_price = group['bid_price']
                ask_price = group['ask_price']
                ask_size = group['ask_size']
                bid_size = group['bid_size']

                # print(len(bid_price), len(ask_price), len(bid_size), len(ask_size))

                
                # Calculate the spread cost (difference between ask and bid prices)
                spread_cost = calculate_spread_cost(bid_price, ask_price)
                actual_price = calculate_actual_price(bid_price,bid_sizes=bid_size)
                expected_price = bid_price.max()

                
                # Return a Series with the calculated spread cost
                group['spread_cost'] = spread_cost
                group['actual_price'] = actual_price
                group['expected_price'] = expected_price
                return group
            
            # data.set_index('timestamp', inplace=True)
            # Resample the data by minute and apply the custom calculation
            result = data.resample('T').apply(calculate_costs)
            return result

            

        df = make_options_dataframe(start_date, end_date)
        df.set_index('timestamp', inplace=True)
        df = resample_to_daily(df)
        # df = df.resample('min').agg({
        #         'ask_price': 'mean',
        #         'ask_size': 'sum',
        #         'bid_price': 'mean',
        #         'bid_size': 'sum'
        #     }).dropna()

        return df

    def strike_to_contract(self, strike_price: float) -> str:
        """
        Convert a float strike price to the 8-digit padded string format used in Polygon option symbols.
        
        Args:
        strike_price (float): The strike price of the option.
        
        Returns:
        str: The 8-digit padded string representation of the strike price.
        
        Example:
        >>> strike_to_contract(150.5)
        '00150500'
        >>> strike_to_contract(1234.25)
        '01234250'
        """
        # Multiply by 1000 to capture up to 3 decimal places, then round to nearest integer
        integer_strike = round(strike_price * 1000)
        
        # Convert to string and pad with leading zeros to ensure 8 digits
        return f"{integer_strike:08d}"

    def get_contract_name(self, ticker:str, maturity_date:str, option_type:str, strike_price:float):
        contract = 'O:'+ticker+maturity_date+option_type+self.strike_to_contract(strike_price)
        return contract

    def get_market_cap(self,ticker):
        # Get MarketCap Data
        url = f'https://api.polygon.io/v3/reference/tickers/{ticker}?apiKey={self.api_key}'
        response = requests.get(url)
        if response.status_code == 200:
            res_data = response.json()
            if 'results' in res_data:
                market_cap = res_data['results']['market_cap']
                # print(f"Market cap for {ticker}: {market_cap}")
                return market_cap
        else:
            print(f"Error fetching market cap data for {ticker}: {response.status_code} {response.text}")
        return None

    def check_valid_option(self, contract, start_date):
        url = f"https://api.polygon.io/v3/reference/options/contracts/{contract}?as_of={start_date}&apiKey={self.api_key}"
        response = requests.get(url)
        data = response.json()
        if data['status']=='NOT_FOUND':
            return False
        return True


class DataClient:
    def __init__(self, save_dir, api_key=API_KEY):
        self.api_key = api_key
        self.databento_api_key = DATABENTO_API_KEY
        self.databento_client = db.Historical(self.databento_api_key)
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
    
    def call_batch(self,ticker, start_date, end_date):
            # Call the batch API to submit the job,  download the results from databento download center
            details = self.databento_client.batch.submit_job(
                dataset="OPRA.PILLAR",
                symbols=[self.databento_contract],
                stype_in="raw_symbol",
                schema="mbp-1",
                encoding="csv",
                pretty_px=True,
                split_duration="none",# month
                start=f"{start_date}T13:30:00+00:00",
                end=f"{end_date}T20:00:00+00:00",
            )

            print("Called batch job with details: ", details)
            print(f"""
        Once results are downloaded, paste the files in `{self.save_dir}/{ticker}` and call the fetch_and_merge_data function with new filepath
        fetch_and_merge_data(ticker, start_date, end_date, maturity_date,quotes_paths=[file_path1, file_path2], option_type= "C",strike_price=125)
        example:
            filepath1 = '{self.save_dir}/{ticker}/data.csv.zst'
            """)
            print("Exiting!!")
            return details

    def fetch_and_merge_data(self, ticker, start_date, end_date, maturity_date,quotes_paths=None, option_type= "C",strike_price=125):
        """
            Fetch and merge OHLCV and quote data for a given ticker and date range.

            Args:
                ticker (str): The underlying stock ticker.
                start_date (str): The start date of the date range in 'YYYY-MM-DD' format.
                end_date (str): The end date of the date range in 'YYYY-MM-DD' format.
                maturity_date (str): The expiration date of the option contract in 'YYMMDD' format.
                option_type (str, optional): The type of option contract (C for call, P for put). Defaults to "C".
                quotes_paths (list, optional): A list of file paths to the quote data. Defaults to None.

            Returns:
                pd.DataFrame: The merged dataframe with OHLCV and quote data.

            Note:
                Contract format:
                The format is: O:UNDERLYING_TICKER_EXPIRATION_DATE_CALL/PUT_STRIKE_PRICE
                For example Databento: AAPL  210917C00125000
                Breaking this down:
                O: - Prefix indicating it's an option
                AAPL - Underlying stock ticker
                210917 - Expiration date (YYMMDD format)
                C - Call option (use P for put)
                00125000 - Strike price ($125.00 in this case)
        """
        self.polygon_contract, self.databento_contract = self.get_contract_name(ticker, maturity_date, option_type, strike_price)
        if not self.check_valid_option(self.polygon_contract, start_date):
            raise ValueError(f"Invalid option contract: {self.polygon_contract}")
        
        if quotes_paths is None or len(quotes_paths) == 0:
            self.call_batch(ticker, start_date, end_date)
            return pd.DataFrame()
        print(f"Fetching data for {self.databento_contract}...")
        ohlcv = self.get_ohlcv(ticker, start_date, end_date)
        quotes = []
        print("Getting quotes...")
        for quotes_path in quotes_paths:
            quotes.append(self.get_quote(quotes_path))
        quotes = pd.concat(quotes)
        quotes.sort_index(inplace=True)
        # df_merged = pd.DataFrame()
        df_merged  = pd.merge(ohlcv, quotes, on="timestamp", how='inner')
        df_merged.rename(columns={
            'Open':'open',
            'High':'high',
            'Low':'low',
            'Close':'close',
            'Volume':'volume',
            'Adj Close':'adj_close'
        }, inplace = True)
        df_merged['time_to_maturity'] = (pd.to_datetime(f'20{maturity_date}', format='%Y%m%d') - df_merged.index).days
        df_merged['contract'] = self.databento_contract
        df_merged['strike_price'] = strike_price
        df_merged = df_merged[df_merged['datetime'].dt.dayofweek < 5]
        print(f"Data for {self.databento_contract} fetched and merged successfully!")
        return df_merged

    def get_ohlcv(self, ticker, start_date, end_date):
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{start_date}/{end_date}"
        params = {
            "apiKey": self.api_key,
            "limit": 50000
        }
        response = requests.get(url, params=params)
        data = response.json()
        if 'results' in data:
            df = pd.DataFrame(data['results'])
            
            df['t'] = pd.to_datetime(df['t'], unit='ms')
            # df['t'] = df['t'].dt.tz_convert('US/Eastern')
            df['t'] = df['t'].dt.floor('min')
            df['timestamp'] = df['t']
            df.set_index('timestamp', inplace=True)
            df = df[['o', 'h', 'l', 'c', 'v']].rename(columns={ 
                'o': 'Open',
                'h': 'High',
                'l': 'Low',
                'c': 'Close',
                'v': 'Volume',
            })
            df['Adj Close'] = df['Close']  # Assuming Adj Close is the same as Close
            df = df.between_time('13:30', '20:00')
            return df
        else:
            print(f"No OHLCV data found for {ticker}")
            
            return pd.DataFrame()
        
    def get_quote(self, filepath):
        # def get_pm_quotes(contract, start_time, end_time):
        #     "per minute quotes from databento"

        #     data = self.databento_client.timeseries.get_range(
        #         dataset="OPRA.PILLAR", # for stocks which require MBO
        #         schema="mbp-1",
        #         stype_in="raw_symbol",
        #         symbols=[contract],
        #         start=start_time,
        #         end=end_time,

        #     )
        #     df = data.to_df()
        #     df.dropna(inplace=True)
        #     return df
        # def make_options_dataframe(start_date:str, end_date:str):
            

        #     all_quotes = []
        #     print ("getting quotes --> ", start_date, end_date)

        #     # for date in tqdm(pd.date_range(start=start_date, end=pd.to_datetime(end_date), freq='D').strftime('%Y-%m-%d').tolist()):
        #     def get_day_quotes(date):
        #         day = pd.to_datetime(date)

        #         # Set start after 13:00
        #         start_time = day + pd.Timedelta(hours=13)
        #         day_quotes = []
        #         # Loop through each hour
        #         for n in range(8):  # 8 hours from 13:00 to 21:00
        #             hour_start = start_time + pd.Timedelta(hours=n)
        #             hour_end = hour_start + pd.Timedelta(hours=1)

        #             for m in range(2):  # 60 minutes in an hour
        #                 minute_start = hour_start + pd.Timedelta(minutes=m)
        #                 minute_end = minute_start + pd.Timedelta(minutes=1)

        #                 minute_start = int(minute_start.timestamp() * 1_000_000_000)
        #                 minute_end = int(minute_end.timestamp() * 1_000_000_000)

        #                 quotes = get_pm_quotes(self.databento_contract, minute_start, minute_end)
        #                 day_quotes.extend(quotes)
        #         result = pd.concat(day_quotes,ignore_index=True)
        #         return result
        #     # num_cores = multiprocessing.cpu_count()
        #     # with multiprocessing.Pool(num_cores-1) as p:
        #     #     all_quotes = p.map(get_day_quotes, pd.date_range(start=start_date, end=pd.to_datetime(end_date), freq='D').strftime('%Y-%m-%d').tolist())


        #     all_quotes = []

        #     for date in tqdm(pd.date_range(start=start_date, end=pd.to_datetime(end_date), freq='D').strftime('%Y-%m-%d').tolist()):
        #         all_quotes.extend(get_day_quotes(date))

        #     if len(all_quotes) == 0:
        #         raise ValueError(f"No quotes found for {self.contract} between {start_date} and {end_date}")
        #     # Create DataFrame
        #     df_quotes = pd.concat(all_quotes,ignore_index=True)


        #     df_quotes.reset_index(drop=True, inplace=True)
        #     df_quotes['timestamp'] = pd.to_datetime(df_quotes['ts_event'], unit='ns')

        #     # Remove timezone information and keep as datetime with only date, hour, and minute
        #     # df_quotes['timestamp'] = df_quotes['timestamp'].dt.floor('min')
        #     df_quotes['datetime'] = df_quotes['timestamp']
        #     df_quotes = df_quotes[['timestamp', 'ask_price', 'ask_size', 'bid_price', 'bid_size', 'datetime']]
        #     return df_quotes

        
        def resample_to_daily(data, groupby_col='T', values = {'ask_price' : 'ask_px_00', 'ask_size' : 'ask_sz_00', 'bid_price' : 'bid_px_00', 'bid_size' : 'bid_sz_00'}):
            # If you need to perform more complex calculations, you can use apply
            # Define a custom function to calculate spread cost
            def calculate_costs(group):
                # Calculate the average bid price and ask price for the minute
                bid_price = group[values['bid_price']]
                ask_price = group[values['ask_price']]
                ask_size = group[values['ask_size']]
                bid_size = group[values['bid_size']]

                
                # Calculate the spread cost (difference between ask and bid prices)
                spread_cost = calculate_spread_cost(bid_price, ask_price)
                actual_price = calculate_actual_price(bid_price,bid_sizes=bid_size)
                expected_price_sell = bid_price.max()
                expected_price_buy = ask_price.min()

                data = {}
                # Return a Series with the calculated spread cost
                data['spread_cost'] = spread_cost
                data['actual_price'] = actual_price
                data['expected_price_sell'] = expected_price_sell
                data['expected_price_buy'] = expected_price_buy
                data['ask_price'] = ask_price.mean()
                data['bid_price'] = bid_price.mean()
                data['ask_size'] = ask_size.sum()
                data['bid_size'] = bid_size.sum()
                return pd.Series(data)
            
            # data.set_index('timestamp', inplace=True)
            # Resample the data by minute and apply the custom calculation
            data.set_index('datetime', inplace=True)
            result = data.resample(groupby_col).apply(calculate_costs)
            result.reset_index(inplace=True)
            return result

        def resample_minute(data):
            """
            Resample same minute multiple row to single row
            """
            def calculate_costs(group):
                # Calculate the average bid price and ask price for the minute
                bid_price = group['bid_price']
                ask_price = group['ask_price']
                ask_size = group['ask_size']
                bid_size = group['bid_size']


                # print (bid_price, ask_price, ask_size, bid_size)
                # print(bid_price.max(), ask_price.min(), ask_price.mean(), bid_price.mean(), ask_size.sum(), bid_size.sum())
                # Calculate the spread cost (difference between ask and bid prices)
                # if type(bid_price) == n:
                if isinstance(bid_price, np.float64):
                    spread_cost = group['spread_cost']
                    actual_price = group['actual_price']
                    expected_price_sell = group['expected_price_sell']
                    expected_price_buy = group['expected_price_buy']
                    ask_price = group['ask_price']
                    bid_price = group['bid_price']
                    ask_size = group['ask_size']
                    bid_size = group['bid_size']
                else:
                    spread_cost = group['spread_cost'].mean()
                    actual_price = group['actual_price'].mean()
                    expected_price_sell = group['expected_price_sell'].max()
                    expected_price_buy = group['expected_price_buy'].min()
                    ask_price = group['ask_price'].mean()
                    bid_price = group['bid_price'].mean()
                    ask_size = group['ask_size'].sum()
                    bid_size = group['bid_size'].sum()
                data = {}
                # Return a Series with the calculated spread cost
                data['spread_cost'] = spread_cost
                data['actual_price'] = actual_price
                data['expected_price_sell'] = expected_price_sell
                data['expected_price_buy'] = expected_price_buy
                data['ask_price'] = ask_price
                data['bid_price'] = bid_price
                data['ask_size'] = ask_size
                data['bid_size'] = bid_size
                return pd.Series(data)

            df = data.groupby("datetime").apply(calculate_costs)
            df.reset_index(inplace=True)
            return df
        def get_options_quotes(filepath, chunksize=10000):
            # chunksize : Number of lines to read from the file per chunk.
            # Open and decompress the file
            # with open(filepath, 'rb') as compressed_file:
            #     dctx = zstd.ZstdDecompressor()
            #     with dctx.stream_reader(compressed_file) as reader:
            #         # Read the decompressed data into a pandas DataFrame
            #         df = pd.read_csv(reader)
            #         df.dropna(inplace=True)
            #         df["datetime"] = pd.to_datetime(df['ts_recv'], unit='ns')
            #         df = resample_to_daily(df)
            #         df["timestamp"] = pd.to_datetime(df["datetime"]).dt.floor('min')
            chunks = pd.read_csv(filepath, chunksize = chunksize)
            data = []
            for chunk in tqdm(chunks):
                chunk.dropna(inplace=True)
                # print(chunk.columns)
                try:
                    chunk["datetime"] = pd.to_datetime(chunk['ts_recv'], unit='ns')
                    df = resample_to_daily(chunk)
                    df["timestamp"] = pd.to_datetime(df["datetime"]).dt.floor('min')
                    data.append(df)
                except Exception as e:
                    print(e)
                    print(chunk.columns)
                    print(len(chunk))
                    continue
            df = pd.concat(data, ignore_index=True)
            df = resample_minute(df)
            return df
           

        df = get_options_quotes(filepath)

        df["timestamp"] = pd.to_datetime(df["datetime"]).dt.floor('min')
        df.set_index('timestamp', inplace=True)
        df = df.between_time('13:30', '20:00')

        return df

    def strike_to_contract(self, strike_price: float) -> str:
        """
        Convert a float strike price to the 8-digit padded string format used in Polygon option symbols.
        
        Args:
        strike_price (float): The strike price of the option.
        
        Returns:
        str: The 8-digit padded string representation of the strike price.
        
        Example:
        >>> strike_to_contract(150.5)
        '00150500'
        >>> strike_to_contract(1234.25)
        '01234250'
        """
        # Multiply by 1000 to capture up to 3 decimal places, then round to nearest integer
        integer_strike = round(strike_price * 1000)
        
        # Convert to string and pad with leading zeros to ensure 8 digits
        return f"{integer_strike:08d}"

    def get_contract_name(self, ticker:str, maturity_date:str, option_type:str, strike_price:float):
        polygon_contract = 'O:'+ticker+maturity_date+option_type+self.strike_to_contract(strike_price)
        databento_contract = ticker+" "*(6-len(ticker))+maturity_date+option_type+self.strike_to_contract(strike_price)
        return polygon_contract, databento_contract

    def get_market_cap(self,ticker):
        # Get MarketCap Data
        url = f'https://api.polygon.io/v3/reference/tickers/{ticker}?apiKey={self.api_key}'
        response = requests.get(url)
        if response.status_code == 200:
            res_data = response.json()
            if 'results' in res_data:
                market_cap = res_data['results']['market_cap']
                # print(f"Market cap for {ticker}: {market_cap}")
                return market_cap
        else:
            print(f"Error fetching market cap data for {ticker}: {response.status_code} {response.text}")
        return None

    def check_valid_option(self, contract, start_date):
        url = f"https://api.polygon.io/v3/reference/options/contracts/{contract}?as_of={start_date}&apiKey={self.api_key}"
        response = requests.get(url)
        data = response.json()
        if data['status']=='NOT_FOUND':
            return False
        return True