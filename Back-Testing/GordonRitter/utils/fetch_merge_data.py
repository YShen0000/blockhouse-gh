import time
import os
from time import sleep
import requests

from pandas import read_csv
import pandas as pd

api_key = 'r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc' 

class PolygonClient:
    def __init__(self, save_dir, api_key=api_key):
        self.api_key = api_key
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

        self.trading_period = ("13:30:00","20:00:00")
    
    def fetch_and_merge_data(self, ticker, start_date, end_date):
        df_poly_ohlcv = self.get_ohlcv(ticker, start_date, end_date)
        df_poly_quote = self.get_quote(ticker, start_date, end_date)
        df_merged  = pd.merge(df_poly_ohlcv, df_poly_quote, on='timestamp', how='inner')
        return df_merged

    def get_ohlcv(self, ticker, start_date, end_date):
        start = time.perf_counter()
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{start_date}/{end_date}"
        params = {"apiKey": api_key, "limit": 50000}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        after =time.perf_counter()
        difference = after -start
        df_poly_ohlcv = pd.DataFrame(data['results'])
        df_poly_ohlcv['timestamp'] = pd.to_datetime(df_poly_ohlcv['t'], unit='ms')
        df_poly_ohlcv.drop(columns=['t', 'vw'], inplace=True)

        df_poly_ohlcv.rename(columns={'o': 'open', 'c': 'close', 'h': 'high', 'l': 'low', 'v': 'volume', 'n': 'transactions'}, inplace=True)
        # Period between 13:30 and 20:00 is the trading period (utc time)
        df_poly_ohlcv.set_index('timestamp', inplace=True)
        df_poly_ohlcv_filtered = df_poly_ohlcv.between_time('13:30', '20:00')
        df_poly_ohlcv.reset_index(inplace=True)
        df_poly_ohlcv.rename(columns={"index": "timestamp"}, inplace=True)
        return df_poly_ohlcv_filtered

    def aggregate_to_minute(self, df: pd.DataFrame):
        # Ensure data is sorted by timestamp
        df.sort_values(by='timestamp', inplace=True)

        # Group by each minute
        df['minute'] = df['timestamp'].dt.floor('min')

        aggregated_data = []

        for minute, group in df.groupby('minute'):
            # Sort bid prices descending and ensure unique bid prices
            top_bids = group[['bid_price', 'bid_size']].drop_duplicates(subset=['bid_price']).sort_values(by='bid_price', ascending=False).head(5)

            # Sort ask prices ascending and ensure unique ask prices
            top_asks = group[['ask_price', 'ask_size']].drop_duplicates(subset=['ask_price']).sort_values(by='ask_price', ascending=True).head(5)

            # Prepare data for the current minute, multiplying sizes by 100
            minute_data = {
                'timestamp': minute,
                # Extract 5 highest bids and corresponding sizes
                **{f'bid_price_{i+1}': top_bids.iloc[i]['bid_price'] if i < len(top_bids) else None for i in range(5)},
                **{f'bid_size_{i+1}': top_bids.iloc[i]['bid_size']  if i < len(top_bids) else None for i in range(5)},
                # Extract 5 lowest asks and corresponding sizes
                **{f'ask_price_{i+1}': top_asks.iloc[i]['ask_price'] if i < len(top_asks) else None for i in range(5)},
                **{f'ask_size_{i+1}': top_asks.iloc[i]['ask_size'] if i < len(top_asks) else None for i in range(5)},
            }

            aggregated_data.append(minute_data)

        # Convert to DataFrame
        return pd.DataFrame(aggregated_data)
    
    
    def get_quote(self, ticker, start_date, end_date):
        def get_all_quotes(ticker, start_time, end_time):
            quotes = []
            next_url = f'https://api.polygon.io/v3/quotes/{ticker}'
            params = {
                "apiKey": self.api_key,
                "timestamp.gte": start_time.value,
                "timestamp.lt": end_time.value,
                "limit": 50000,
                "order": "asc",
                "sort": "timestamp"
            }

            while next_url:
                response = requests.get(next_url, params=params)
                response.raise_for_status()
                data = response.json()
                quotes.extend(data['results'])
                
                next_url = data.get('next_url')
                # if next_url:
                #     params = {"apiKey": self.api_key}  # Reset params as next_url includes other parameters
                
                # Respect rate limits
                sleep(0.2)  # Wait 200ms between requests to avoid hitting rate limits

            return quotes

        all_quotes = []

        for date in pd.date_range(start=start_date, end=pd.to_datetime(end_date), freq='D').strftime('%Y-%m-%d').tolist():
            day = pd.to_datetime(date)

            # Set start after 13:00
            start_time = day + pd.Timedelta(hours=13)

            # Loop through each hour
            for n in range(8):  # 8 hours from 13:00 to 21:00
                hour_start = start_time + pd.Timedelta(hours=n)
                hour_end = hour_start + pd.Timedelta(hours=1)
                
                quotes = get_all_quotes(ticker, hour_start, hour_end)
                all_quotes.extend(quotes)

        # Create DataFrame
        df_quotes = pd.DataFrame(all_quotes)
        df_quotes['timestamp'] = pd.to_datetime(df_quotes['participant_timestamp'], unit='ns')

        # Drop unnecessary columns
        df_quotes.drop(
                columns=["indicators", "ask_exchange", "bid_exchange",  
                            "participant_timestamp", "tape", "sip_timestamp", 
                            "conditions", "sequence_number"],
                inplace=True
        )

        df_quotes_processed = self.aggregate_to_minute(df_quotes)


        return df_quotes_processed

    def get_market_cap(self, ticker):
        # Set default market cap for MSFT if not found
        default_market_cap = 3458211368924.0
        print("defaulting ",default_market_cap)
        # Check for MSFT ticker explicitly
        if ticker == "MSFT":
            return default_market_cap

        # Construct the API URL for the Polygon endpoint
        url = f'https://api.polygon.io/v3/reference/tickers/{ticker}?apiKey={self.api_key}'
        response = requests.get(url)

        # Check for a successful response
        if response.status_code == 200:
            print("Ticker found, fetching market cap...")
            res_data = response.json()

            # Attempt to extract market cap from the results
            if 'results' in res_data and 'market_cap' in res_data['results']:
                market_cap = res_data['results']['market_cap']
                print(f"Market cap for {ticker}: {market_cap}")
                return market_cap
            else:
                print(f"Market cap not found in response for {ticker}, using default for MSFT.")
                return default_market_cap
        else:
            print(f"Error fetching market cap data for {ticker}: {response.status_code} {response.text}")

        # Return default market cap if no valid data found
        return default_market_cap