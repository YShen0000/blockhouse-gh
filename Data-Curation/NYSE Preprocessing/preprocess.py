import pandas as pd
import os

# List of tickers
tickers = ['aapl']  # Add other tickers as needed

# Create the output directory if it doesn't exist
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Initialize order book
order_book = {
    'bids': [],
    'asks': []
}

# Initialize index pointers
start_index = 0

def update_order_book_from_chunk(chunk, start_idx, end_idx):
    """Update the order book from the specified chunk range."""
    for i in range(start_idx, end_idx):
        row = chunk.iloc[i]
        order = {
            'price': row['price'],
            'size': row['size'],
            'order_id': row['order_id']
        }
        if row['action'] == 'A':
            if row['side'] == 'B':
                order_book['bids'].append(order)
            elif row['side'] == 'A':
                order_book['asks'].append(order)
        elif row['action'] == 'C':
            order_book['bids'] = [order for order in order_book['bids'] if order['order_id'] != row['order_id']]
            order_book['asks'] = [order for order in order_book['asks'] if order['order_id'] != row['order_id']]
        elif row['action'] in ['F', 'T']:
            for order in order_book['bids']:
                if order['order_id'] == row['order_id']:
                    order['size'] -= row['size']
                    if order['size'] <= 0:
                        order_book['bids'].remove(order)
                    break
            for order in order_book['asks']:
                if order['order_id'] == row['order_id']:
                    order['size'] -= row['size']
                    if order['size'] <= 0:
                        order_book['asks'].remove(order)
                    break
    
    #order_book['bids'] = sorted(order_book['bids'], key=lambda x: -x['price'])[:3]  # Top 3 descending order
    #order_book['asks'] = sorted(order_book['asks'], key=lambda x: x['price'])[:3]    # Top 3 ascending order

def assign_side(row):
    """Assign side based on the top 3 values in the order book."""
    sorted_bids = sorted(order_book['bids'], key=lambda x: -x['price'])[:3]  # Top 3 descending order
    sorted_asks = sorted(order_book['asks'], key=lambda x: x['price'])[:3]   # Top 3 ascending order

    # Extract the best prices
    best_bid = sorted_bids[0]['price'] if sorted_bids else 0  # Default 0 if empty
    best_ask = sorted_asks[0]['price'] if sorted_asks else float('inf')  # Default +inf if empty

    # Use weighted average prices for more accuracy 
    weighted_bid, weighted_ask = 0, 0 
    if sorted_bids: 
        weighted_bid = sum(order['price'] * order['size'] for order in sorted_bids) / sum(order['size'] for order in sorted_bids) 
    else: 
        weighted_bid = best_bid 
    if sorted_asks: 
        weighted_ask = sum(order['price'] * order['size'] for order in sorted_asks) / sum(order['size'] for order in sorted_asks) 
    else: 
        weighted_ask = best_ask

    # Assign side based on price comparison
    if row['price'] <= weighted_bid:
        row['side'] = 'B'
    elif row['price'] >= weighted_ask:
        row['side'] = 'A'
    else:  # Between the best bid and ask
        bid_distance = abs(row['price'] - weighted_bid)
        ask_distance = abs(row['price'] - weighted_ask)
        row['side'] = 'B' if bid_distance < ask_distance else 'A'
    return row

def process_chunk(chunk):
    """Process a chunk of MBO data."""
    global start_index
    for i in range(len(chunk)):
        row = chunk.iloc[i]
        if row['action'] == 'T' and row['side'] == 'N':
            update_order_book_from_chunk(chunk, start_index, i)
            chunk.iloc[i] = assign_side(row)
            start_index = i + 1
            #print(start_index)
    return chunk

def mbo_preprocess(input_file, output_file):
    """Preprocess MBO data."""
    global start_index
    dtypes = {
        'side': 'category',
        'size': 'float64',
        'price': 'float64',
        'order_id': 'int64'
    }
    usecols = ['ts_event', 'action', 'side', 'size', 'price', 'order_id']
    chunk_size = 10 ** 6  # Adjust the chunk size as needed
    
    # Read and concatenate all chunks
    chunks = pd.read_csv(input_file, usecols=usecols, dtype=dtypes, parse_dates=['ts_event'], chunksize=chunk_size)
    concatenated_data = pd.concat(chunks, ignore_index=True)
    
    # Process the concatenated data
    #concatenated_data.columns = concatenated_data.columns.str.strip().str.lower()
    concatenated_data = process_chunk(concatenated_data)
    concatenated_data['ts_event'] = concatenated_data['ts_event'].dt.floor('s')
    

    # Filter and aggregate the processed data
    data = concatenated_data[concatenated_data['action'] == 'T']
    aggregated_data = data.groupby('ts_event').agg(
        bid_fill=('size', lambda x: x[data['side'] == 'B'].sum()),  # Summing 'size' where 'side' is 'B'
        ask_fill=('size', lambda x: x[data['side'] == 'A'].sum())   # Summing 'size' where 'side' is 'A'
    ).reset_index()
    aggregated_data['signed_volume'] = aggregated_data['bid_fill'] - aggregated_data['ask_fill']
    aggregated_data.to_csv(output_file, index=False)

def mbp_preprocess(input_file, output_file):
    """Preprocess MBP data."""
    usecols = ['ts_event', 'size', 'side', 'price', 'bid_px_00', 'ask_px_00']
    dtypes = {
        'size': 'float64',
        'side': 'category',
        'price': 'float64',
        'bid_px_00': 'float64',
        'ask_px_00': 'float64'
    }
    data = pd.read_csv(input_file, usecols=usecols, dtype=dtypes, parse_dates=['ts_event'])
    data['ts_event'] = data['ts_event'].dt.floor('s')
    last_rows = data.drop_duplicates('ts_event', keep='last')
    last_rows = last_rows.rename(columns={'bid_px_00': 'best_bid', 'ask_px_00': 'best_ask'})
    last_rows['mid_price'] = (last_rows['best_bid'] + last_rows['best_ask']) / 2
    last_rows.to_csv(output_file, index=False)

def merge_datasets(mbo_file, mbp_file, output_file):
    """Merge processed MBO and MBP datasets."""
    dataset1 = pd.read_csv(mbo_file, parse_dates=['ts_event'])
    dataset2 = pd.read_csv(mbp_file, parse_dates=['ts_event'])
    dataset1['ts_event'] = dataset1['ts_event'].dt.strftime('%Y-%m-%d %H:%M:%S')
    dataset2['ts_event'] = dataset2['ts_event'].dt.strftime('%Y-%m-%d %H:%M:%S')
    merged_data = pd.merge(dataset1, dataset2, on='ts_event', how='inner')
    merged_data = merged_data.drop(columns=['size', 'side'], errors='ignore')
    if 'mid_price' in merged_data.columns:
        merged_data['mid_price'] = merged_data['mid_price'].round(3)
    merged_data.to_csv(output_file, index=False)


# Iterate through each ticker and process the data
for ticker in tickers:
    mbo_input = f"dbeq-basic-20241021-20241120.mbo.csv"
    mbp_input = f"dbeq-basic-20241021-20241120.mbp-1.csv"
    mbo_output = f"{ticker}-mbo-processed.csv"
    mbp_output = f"{ticker}-mbp-processed.csv"
    merged_output = os.path.join(output_dir, f"NYSE {ticker.upper()}-{ticker}-merged.csv")
    print(f"Processing {ticker.upper()}...")
    # Process MBO and MBP datasets
    mbo_preprocess(mbo_input, mbo_output)
    print("Processing MBP dataset...")
    mbp_preprocess(mbp_input, mbp_output)
    # Merge the processed datasets
    merge_datasets(mbo_output, mbp_output, merged_output)

print(f"Processing complete. Merged files are saved in the '{output_dir}' directory.")
bids_df = pd.DataFrame(order_book['bids']) 
#print(bids_df)
bids_df.columns = ['Bid_Price', 'Bid_Size', 'Bid_Order_ID'] 
#print(bids_df)
asks_df = pd.DataFrame(order_book['asks']) 
asks_df.columns = ['Ask_Price', 'Ask_Size', 'Ask_Order_ID']

order_book_df = pd.concat([bids_df.reset_index(drop=True), asks_df.reset_index(drop=True)], axis=1) # Write the order book to a CSV file 
order_book_df.to_csv('order_book.csv', index=False)