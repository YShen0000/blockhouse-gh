import json
import requests
from datetime import datetime, timedelta
from kafka import KafkaProducer

POLYGON_API_KEY = "r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc"  # Replace with your actual API key

def fetch_ohlcv_data(symbol, date):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/minute/{date}/{date}?apiKey={POLYGON_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.status_code}")
    data = response.json()
    print(f"OHLCV data for {symbol}: {json.dumps(data, indent=2)}")  # Debugging: Print the OHLCV data
    return data.get('results', [])

def fetch_quotes(symbol, date):
    url = f"https://api.polygon.io/v3/quotes/{symbol}?startDate={date}&endDate={date}&apiKey={POLYGON_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.status_code}")

    data = response.json()
    print(f"Quotes API response for {symbol}: {json.dumps(data, indent=2)}")  # Debugging: Print the API response
    return data.get('results', [])
def aggregate_quotes(quotes):
    aggregated_quotes = {}
    for quote in quotes:
        if 'sip_timestamp' not in quote or 'bid_price' not in quote or 'ask_price' not in quote:
            print(f"Skipping quote due to missing fields: {quote}")
            continue

        # Convert quote timestamp to minute level by dividing by 60,000,000 (from microseconds to minutes)
        minute = quote['sip_timestamp'] // 60000000
        print(f"Minute-level quote timestamp (adjusted): {minute}")

        if minute not in aggregated_quotes:
            aggregated_quotes[minute] = {
                'bid_price': quote['bid_price'],
                'ask_price': quote['ask_price'],
                'bid_size': quote['bid_size'],
                'ask_size': quote['ask_size']
            }
        else:
            existing_quote = aggregated_quotes[minute]
            bid_size_total = existing_quote['bid_size'] + quote.get('bid_size', 0)
            ask_size_total = existing_quote['ask_size'] + quote.get('ask_size', 0)
            existing_quote['bid_price'] = (
                (existing_quote['bid_price'] * existing_quote['bid_size'] + quote['bid_price'] * quote['bid_size']) / bid_size_total
            )
            existing_quote['ask_price'] = (
                (existing_quote['ask_price'] * existing_quote['ask_size'] + quote['ask_price'] * quote['ask_size']) / ask_size_total
            )
            existing_quote['bid_size'] = bid_size_total
            existing_quote['ask_size'] = ask_size_total

    print(f"Aggregated quotes: {json.dumps(aggregated_quotes, indent=2)}")
    return aggregated_quotes

# Adjusted OHLCV to match the same minute-level timestamp approach
def main():
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    print("Sending historical trading data...")

    symbol = "AAPL"
    date = "2023-09-25"

    try:
        ohlcv_data = fetch_ohlcv_data(symbol, date)
        if not ohlcv_data:
            print(f"No OHLCV data found for {symbol}")
            return

        quotes = fetch_quotes(symbol, date)
        if not quotes:
            print(f"No quotes data found for {symbol}")
            return

        aggregated_quotes = aggregate_quotes(quotes)

        for data in ohlcv_data:
            # Convert OHLCV timestamp to minute level to match the quotes
            minute = data['t'] // 60000  # Assume timestamp is in milliseconds for OHLCV
            print(f"Minute-level OHLCV timestamp: {minute}")

            quote = find_nearest_quote(minute, aggregated_quotes, tolerance=2)

            if not quote:
                print(f"No matching quote for minute {minute}")
                quote = {"bid_price": 0, "ask_price": 0, "bid_size": 0, "ask_size": 0}
            else:
                print(f"Matching quote for minute {minute}: {quote}")

            trade = {
                "symbol": symbol,
                "timestamp": datetime.utcfromtimestamp(data['t'] // 1000).strftime('%Y-%m-%dT%H:%M:%SZ'),
                "open": data['o'],
                "high": data['h'],
                "low": data['l'],
                "close": data['c'],
                "volume": data['v'],
                "bid_price": quote['bid_price'],
                "ask_price": quote['ask_price'],
                "bid_size": quote['bid_size'],
                "ask_size": quote['ask_size']
            }

            producer.send('historical-data', trade)
            print(f"Message sent: {trade}")
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")

    print("Finished sending historical trading data.")

if __name__ == "__main__":
    main()
