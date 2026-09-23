import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import databento as db
import pandas as pd
import time

# Define Databento API credentials and parameters
API_KEY = 'db-bh88USitQqKhjDK8yRHtihL5EGQP4'  # Replace with your actual API key
SYMBOLS = ['AAPL', 'TSLA', 'NVDA']  # Symbols to fetch
START_DATE = '2024-10-31T14:00:00'  # Set start date and time to a specific 5-minute window
END_DATE = '2024-10-31T14:05:00'    # End date 5 minutes after start

# Initialize the Databento Historical client
client = db.Historical(key=API_KEY)

def fetch_mbp10_data(symbol):
    """Fetch MBP-10 data for a given symbol and return a DataFrame."""
    start_time = time.time()
    try:
        # Fetch MBP-10 data from Databento
        data = client.timeseries.get_range(
            dataset="XNAS.ITCH",
            symbols=symbol,         # Use 'symbols' instead of 'symbol'
            schema='mbp-10',
            start=START_DATE,
            end=END_DATE,
        )
        df = data.to_df()
        elapsed_time = time.time() - start_time
        return {'symbol': symbol, 'df': df, 'time': elapsed_time}
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return {'symbol': symbol, 'df': None, 'time': None}

def save_to_csv(symbol, df):
    """Save the DataFrame to a CSV file."""
    if df is not None:
        filename = f"{symbol}_mbp10_data_{START_DATE}_to_{END_DATE}.csv"
        df.to_csv(filename, index=False)
        print(f"Saved {symbol} data to {filename}")
    else:
        print(f"No data available for {symbol}")

# Run API calls in parallel and save results
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(fetch_mbp10_data, symbol): symbol for symbol in SYMBOLS}
    for future in as_completed(futures):
        result = future.result()
        symbol = result['symbol']
        df = result['df']
        elapsed_time = result['time']
        if df is not None:
            save_to_csv(symbol, df)
            print(f"Data for {symbol} fetched in {elapsed_time:.2f} seconds")
        else:
            print(f"No data for {symbol}")



# import databento as db
# import asyncio
# import pandas as pd

# async def fetch_mbp10_data(client, symbol, start_date, end_date):
#     try:
#         data = await client.timeseries.get_range_async(
#             dataset='GLBX.MDP3',  # Example dataset
#             symbols=symbol,
#             schema='mbp-10',
#             start=start_date,
#             end=end_date,
#         )
#         df = data.to_df()
#         return symbol, df
#     except Exception as e:
#         print(f"Error fetching data for {symbol}: {e}")
#         return symbol, None

# async def main():
#     API_KEY = 'YOUR_API_KEY'  # Replace with your actual API key
#     symbols = ['ESM2024', 'NQM2024', 'YMM2024']  # List of symbols
#     start_date = '2024-11-01'
#     end_date = '2024-11-14'

#     client = db.Historical(key=API_KEY)

#     tasks = [
#         fetch_mbp10_data(client, symbol, start_date, end_date)
#         for symbol in symbols
#     ]

#     results = await asyncio.gather(*tasks)

#     for symbol, df in results:
#         if df is not None:
#             csv_filename = f"{symbol}_mbp10_data_{start_date}_to_{end_date}.csv"
#             df.to_csv(csv_filename, index=False)
#             print(f"Data for {symbol} saved to {csv_filename}")
#         else:
#             print(f"No data for {symbol}")

# if __name__ == '__main__':
#     asyncio.run(main())





# import requests
# from concurrent.futures import ThreadPoolExecutor, as_completed
# import pandas as pd
# import time

# API_KEY = 'r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc'
# SYMBOLS = ['AAPL', 'GOOGL', 'TSLA']  # list of symbols to fetch
# LIMIT = 50  # Limit of quotes per request (adjust based on API limits and data requirements)

# def fetch_quotes_data(symbol):
#     url = f"https://api.polygon.io/v3/quotes/{symbol}?apiKey={API_KEY}&limit={LIMIT}"
#     start_time = time.time()
#     try:
#         response = requests.get(url)
#         response.raise_for_status()
#         data = response.json().get('results', [])
#         if not data:
#             print(f"No data found for {symbol}")
#             return None
#         elapsed_time = time.time() - start_time
#         return {'symbol': symbol, 'data': data, 'time': elapsed_time}
#     except requests.exceptions.HTTPError as err:
#         print(f"Error fetching data for {symbol}: {err}")
#         return None

# def save_to_csv(symbol, data):
#     # Convert data to DataFrame
#     df = pd.DataFrame(data)
#     # Convert timestamps if available in the quote data
#     if 't' in df.columns:
#         df['t'] = pd.to_datetime(df['t'], unit='ms')
#     # Save each ticker’s data to its own CSV file
#     df.to_csv(f"{symbol}_quotes_data.csv", index=False)
#     print(f"Saved {symbol} quotes data to {symbol}_quotes_data.csv")

# # Run API calls in parallel and save results
# with ThreadPoolExecutor(max_workers=5) as executor:
#     future_to_symbol = {executor.submit(fetch_quotes_data, symbol): symbol for symbol in SYMBOLS}
#     for future in as_completed(future_to_symbol):
#         symbol = future_to_symbol[future]
#         try:
#             result = future.result()
#             if result and result['data']:
#                 # Save data to CSV
#                 save_to_csv(result['symbol'], result['data'])
#                 # Print the completion time
#                 print(f"Quotes data for {result['symbol']} fetched in {result['time']:.2f} seconds")
#             else:
#                 print(f"Failed to get data for {symbol}")
#         except Exception as exc:
#             print(f"{symbol} generated an exception: {exc}")




