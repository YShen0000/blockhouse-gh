
from pandas import read_csv
import requests
import csv
import pandas as pd
import time
import numpy as np
import os
from time import sleep
from datetime import datetime, timedelta
import pytz



api_key = 'r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc' 

def fetch_and_merge_data(ticker, start_date, end_date,save_dir = 'data', limit =50000, save_data = True):

    def get_ticker_agg_data(start_date, end_date, ticker, api_key):
        try:
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{start_date}/{end_date}"
            params = {"apiKey": api_key, "limit": limit}
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if 'results' not in data:
                raise ValueError("No results found in the API response.")

            # Save OHLCV data to CSV
            with open(f'{save_dir}/data_{ticker}_{start_date}_{end_date}.csv', 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'datetime', 'open', 'high', 'low', 'close', 'volume']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for item in data['results']:
                    human_readable_time = pd.to_datetime(item['t'], unit='ms')
                    writer.writerow({
                        'timestamp': item['t'],
                        'datetime': human_readable_time,
                        'open': item['o'],
                        'high': item['h'],
                        'low': item['l'],
                        'close': item['c'],
                        'volume': item['v']
                    })
            return data

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"An error occurred while making the request: {req_err}")
        except ValueError as val_err:
            print(f"Value error: {val_err}")
        except Exception as e:
            print(f"An error occurred: {e}")

        return None

    def get_hourly_quotes(date, ticker, api_key):
        try:
            today = pd.to_datetime(date)
            quotes = []
            for n in range(23):
                gt = (today + pd.DateOffset(hours=n)).value
                lt = (today + pd.DateOffset(hours=n+1)).value

                response = requests.get(
                    f'https://api.polygon.io/v3/quotes/{ticker}', 
                    params={"apiKey": api_key, "timestamp.gt": gt, "timestamp.lt": lt, "limit": 1000}
                )
                response.raise_for_status()
                data = response.json()

                if response.status_code == 200 and 'results' in data:
                    quotes.extend(data['results'])
                else:
                    print(f"No quotes found for {date}, hour {n}")

            return quotes

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"An error occurred while making the request: {req_err}")
        except Exception as e:
            print(f"An error occurred: {e}")

        return []

    def get_ticker_quote_data(start_date, end_date, ticker, api_key):
        try:
            start = pd.Timestamp(start_date)
            end = pd.Timestamp(end_date)
            date_range = pd.date_range(start=start, end=end, freq='D')
            frames = []

            for date in date_range.strftime('%Y-%m-%d').tolist():
                quotes = get_hourly_quotes(date, ticker, api_key)
                if quotes:
                    df = pd.DataFrame(quotes)
                    frames.append(df)

            if frames:
                df = pd.concat(frames)
                df["datetime"] = pd.to_datetime(df["participant_timestamp"], unit="ns")
                df = df.set_index('datetime')
                df.drop(
                    columns=["indicators", "ask_exchange", "bid_exchange",  
                                "participant_timestamp", "tape", "sip_timestamp", 
                                "conditions", "sequence_number"],
                    inplace=True
                )

                quotes = df.resample('min').agg({
                    'ask_price': 'last',
                    'ask_size': 'sum',
                    'bid_price': 'last',
                    'bid_size': 'sum',
                }).fillna(method='ffill')

                return quotes

            else:
                print(f"No data frames available for the given date range: {start_date} to {end_date}")
                return pd.DataFrame()

        except Exception as e:
            print(f"An error occurred while fetching quote data: {e}")
            return pd.DataFrame()

    # Fetch OHLCV Agg Data
    ohlcv_file = f"{save_dir}/data_{ticker}_{start_date}_{end_date}.csv"
    if os.path.exists(ohlcv_file):
        ohlcv = pd.read_csv(ohlcv_file)
    else:
        ohlcv = get_ticker_agg_data(start_date, end_date, ticker, api_key=api_key)
        if ohlcv is None:
            print("Failed to retrieve OHLCV data.")
            return pd.DataFrame()
        # Load OHLCV data
        try:
            ohlcv = pd.read_csv(f"{save_dir}/data_{ticker}_{start_date}_{end_date}.csv")
        except Exception as e:
            print(f"Error loading OHLCV data from CSV: {e}")
            return pd.DataFrame()
    # Fetch Bid Ask Data over the same period
    quotes = get_ticker_quote_data(start_date, end_date, ticker, api_key=api_key)
    if quotes.empty:
        print("Failed to retrieve Bid-Ask quote data.")
        return pd.DataFrame()

    try:
        quotes["timestamp"] = quotes.index.astype('int64') // (10**6)  # convert to ms

        # Merge and process output
        result = pd.merge(ohlcv, quotes, left_on="timestamp", right_on="timestamp", how="inner")

        if save_data:
            # Write combined file
            result.to_csv(f"{save_dir}/merged_data_{ticker}_{start_date}_{end_date}.csv")
            print(f"Merged data saved to merged_data_{ticker}_{start_date}_{end_date}.csv")

        return result

    except Exception as e:
        print(f"An error occurred during merging or saving the data: {e}")
        return pd.DataFrame()


def fetch_all_tickers():
    """
    It fetches all tickers from the Polygon API and saves them to a CSV file.
    """

    pass

def get_market_cap(ticker):
    # Get MarketCap Data
    url = f'https://api.polygon.io/v3/reference/tickers/{ticker}?apiKey={api_key}'
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


class DatabentoClient:
    def __init__(self, api_key, save_dir):
        import databento as db
        self.api_key = api_key
        self.save_dir = save_dir
        self.client = db.Historical(self.api_key)

    def fetch_and_merge_data(self, ticker, start_date, end_date):
        df_mbo = self.get_quote(ticker, start_date, end_date)
        df_ohlcv = self.get_agg(ticker, start_date, end_date)

        df_merged  = pd.merge(df_ohlcv, df_mbo, left_on='ts_recv', right_on='ts_recv', how='inner')
        # df_merged["datetime"] = df["ts_recv"]
        df_merged = df_merged.rename(columns={'ts_recv': 'datetime', 'ts_event': 'timestamp'})
        df_merged.drop(
                        columns=["rtype","publisher_id","instrument_id", "price", "size", "side", "symbol"],
                        inplace=True
                        )
        # Remove the first row as it is before the market open
        df_merged = df_merged.iloc[1:]

        return df_merged

    def get_quote(self, ticker, start_date, end_date):
        data = self.client.timeseries.get_range(
            dataset="XNAS.ITCH", # for stocks which require MBO
            schema="mbo",
            stype_in="raw_symbol",
            symbols=[ticker],
            start=start_date,
            end=end_date,
        )
        df_mbo = data.to_df()
        df_mbo = df_mbo.reset_index(names=["ts_recv"])
        df_mbo = df_mbo.set_index('ts_recv', drop=False)
        df_processed = self.process_mbo_data(df_mbo,start_date)
        return df_processed
    
    def get_agg(self, ticker, start_date, end_date):
        data_ohlcv = self.client.timeseries.get_range(
            dataset="XNAS.ITCH", # for stocks which require MBO
            schema="ohlcv-1m",
            stype_in="raw_symbol",
            symbols=[ticker],
            start=start_date,
            end=end_date,
        )
        df_ohlcv = data_ohlcv.to_df()
        return df_ohlcv

    def process_mbo_data(self, df_mbo, start_date):

        df_mbo = df_mbo[df_mbo['ts_recv']>=f'{start_date} 13:30:00'].copy()
        df = df_mbo[df_mbo['action']!='C'].copy()
        
        # Set the datetime column as the index
        df['ask_size'] = df.apply(lambda row: row['size'] if row['side'] == 'A' else 0, axis=1)
        df['bid_size'] = df.apply(lambda row: row['size'] if row['side'] == 'B' else 0, axis=1)
        df['ask_price'] = df.apply(lambda row: row['price'] if row['side'] == 'A' else 0, axis=1)
        df['bid_price'] = df.apply(lambda row: row['price'] if row['side'] == 'B' else 0, axis=1)

        
        agg_functions = {
            'price': 'last',  # Last, high, and low price in the minute
            'size': 'sum',    # Total size in the minute
            'side': 'last',  # Last bid/ask flag in the minute
            'ask_size': 'sum',
            'bid_size': 'sum',
            'ask_price': 'max',
            'bid_price': 'max',
        }

        # Resample and apply aggregation
        result = df.resample('1T').agg(agg_functions)
        
        return result


class PolygonClient:
    def __init__(self, save_dir, api_key=api_key):
        self.api_key = api_key
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

        self.trading_period = ("13:30:00","20:00:00")
    
    def fetch_and_merge_data(self, ticker, end_date, backtest=False):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        start_date = (end_date - timedelta(days=1)).strftime('%Y-%m-%d')

        # Pull data for one day before actual back test date
        if backtest:
            end_date = (end_date - timedelta(days=1))
            if end_date.weekday() >= 5:
                if end_date.weekday() == 6: #saturday
                    end_date = (end_date - timedelta(days=1))
                else:   #sunday
                    end_date = (end_date - timedelta(days=2))

            start_date = (end_date - timedelta(days=1)).strftime('%Y-%m-%d')

        # Convert end_timestamp to UTC string
        end_date = end_date.astimezone(pytz.UTC).strftime('%Y-%m-%d')

        # print(f'Start date: {start_date}')
        # print(f'End date: {end_date}')

        df_poly_ohlcv = self.get_ohlcv(ticker, start_date, end_date)
        # df_poly_quote = self.get_quote(ticker, start_date, end_date)
        df_merged = df_poly_ohlcv.copy()
        # df_merged  = pd.merge(df_poly_ohlcv, df_poly_quote, left_index=True, right_index=True, how='inner')
        df_merged["timestamp"] = df_merged.index.astype('int64') // (10**6) 
        df_merged.reset_index(inplace=True)
        df_merged.rename(columns={"index": "datetime"}, inplace=True)
        df_merged.reset_index(drop=True, inplace=True) # remove datetime index and reset it to range from 0 to n
        return df_merged

    def get_ohlcv(self, ticker, start_date, end_date):
        print("inside ohlcv")
        start = time.perf_counter()
        print(f'Start date in OHLCV: {start_date}')
        print(f'End date for OHLCV: {end_date}')
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{start_date}/{end_date}"
        params = {"apiKey": api_key, "limit": 50000}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        # print(f'Data from OHLCV: {data}')
        after =time.perf_counter()
        difference = after -start
        print(difference)
        print("Got the response")
        df_poly_ohlcv = pd.DataFrame(data['results'])
        df_poly_ohlcv['datetime'] = pd.to_datetime(df_poly_ohlcv['t'], unit='ms')
        df_poly_ohlcv.set_index('datetime', inplace=True)
        df_poly_ohlcv.drop(columns=['t', 'vw'], inplace=True)

        df_poly_ohlcv.rename(columns={'o': 'open', 'c': 'close', 'h': 'high', 'l': 'low', 'v': 'volume', 'n': 'transactions'}, inplace=True)
        # Period between 13:30 and 20:00 is the trading period (utc time)
        df_poly_ohlcv_filtered = df_poly_ohlcv.between_time('13:30', '20:00')
        return df_poly_ohlcv_filtered

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

        def process_quotes(df_quotes):
            df = df_quotes.copy()
            agg_functions = {
                'ask_size': 'sum',
                'bid_size': 'sum',
                'ask_price': 'max',
                'bid_price': 'min',
            }

            # Resample and apply aggregation
            result = df.resample('1T').agg(agg_functions)

            df_quotes_processed = result
            df_quotes_processed = df_quotes_processed.between_time(self.trading_period[0], self.trading_period[1])
            df_quotes_processed["bid_size"] = df_quotes_processed.apply(lambda row: row["bid_size"]*100, axis=1)
            df_quotes_processed["ask_size"] = df_quotes_processed.apply(lambda row: row["ask_size"]*100, axis=1)
            
            return df_quotes_processed

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
        df_quotes['datetime'] = pd.to_datetime(df_quotes['participant_timestamp'], unit='ns')
        df_quotes.set_index('datetime', inplace=True)

        # Drop unnecessary columns
        df_quotes.drop(
                columns=["indicators", "ask_exchange", "bid_exchange",  
                            "participant_timestamp", "tape", "sip_timestamp", 
                            "conditions", "sequence_number"],
                inplace=True
        )

        df_quotes_processed = process_quotes(df_quotes)


        return df_quotes_processed
    
#     def get_market_cap(self,ticker):
#         # Get MarketCap Data
#         if ticker == "MSFT":
#             market_cap = 3458211368924.0
#             return market_cap
#         url = f'https://api.polygon.io/v3/reference/tickers/{ticker}?apiKey={self.api_key}'
#         response = requests.get(url)
#         if response.status_code == 200:
#             print("tickerererer")
#             res_data = response.json()
            
#             if 'results' in res_data:
#                 market_cap = res_data['results']['market_cap']
#                 # print(f"Market cap for {ticker}: {market_cap}")
#                 return market_cap
#         else:
#             print(f"Error fetching market cap data for {ticker}: {response.status_code} {response.text}")
#         return None

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