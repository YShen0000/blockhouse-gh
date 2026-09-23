from polygon import RESTClient
from datetime import timedelta
import numpy as np
import pandas as pd

def get_full_day_expected_price(symbol, start_time, end_time):
    # Initialize the client with your API key
    api_key = 'r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc'
    client = RESTClient(api_key)

    minute_bid_ask_quotes = pd.DataFrame()
    current_time = start_time
    while current_time <= end_time:
        # Convert timestamp to nanoseconds
        end_timestamp = int(current_time.timestamp() * 1_000_000_000)
        start_timestamp = end_timestamp - (60 * 1_000_000_000)  # Subtract 1 minute from the timestamp for start time

        # Make the API call
        quotes = client.list_quotes(
            symbol,
            timestamp_gte=start_timestamp,
            timestamp_lte=end_timestamp,
            limit=50000  # Adjust based on your needs
        )

        # Initialize variables to store maximum bid price and sizes
        max_bid_price = float('-inf')
        min_ask_price = float('inf')
        bid_sizes = []
        ask_sizes = []
        bid_prices = []
        ask_prices = []

        # Process the results to find the maximum bid price and collect sizes
        for quote in quotes:
            if quote.bid_price > max_bid_price:
                max_bid_price = quote.bid_price
            if quote.ask_price < min_ask_price:
                min_ask_price = quote.ask_price
            bid_prices.append(quote.bid_price)
            bid_sizes.append(quote.bid_size * 100)
            ask_sizes.append(quote.ask_size * 100)
            ask_prices.append(quote.ask_price)

        # Check if max_bid_price was updated, otherwise handle no data case
        if max_bid_price == float('-inf'):
            print(f"No bid prices found for the given timestamp: {current_time}")

        # Added minimum ask price
        temp_df = pd.DataFrame([{"timestamp": current_time, "max_bid_price": max_bid_price, "bid_prices": bid_prices,\
                                "bid_sizes": bid_sizes,"ask_prices": ask_prices, "ask_sizes": ask_sizes, \
                                "min_ask_price": min(ask_prices)}])
        minute_bid_ask_quotes = pd.concat([minute_bid_ask_quotes, temp_df], ignore_index=True)

        # Increment the time by 1 minute
        current_time += timedelta(minutes=1)

    # Save DataFrame to a CSV file
    start_time_str = start_time.strftime('%Y-%m-%d_%H-%M-%S')
    minute_bid_ask_quotes.to_csv(f'BacktestData/minute_{symbol}_{start_time_str}.csv', index=False)
    return minute_bid_ask_quotes