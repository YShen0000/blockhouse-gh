import os
import pandas as pd
import numpy as np
from multiprocessing import Pool, cpu_count

def process_file(file_name):
    """Process a single parquet file."""
    print(f"Starting processing for {file_name}...")
    try:
        df_clob_data = pd.read_parquet(file_name, engine="pyarrow", columns=['timestamp_ny', 'side', 'size', 'price'])
        print(f"File {file_name} loaded successfully.")
    except Exception as e:
        print(f"Error loading {file_name}: {e}")
        return pd.DataFrame()  # Return an empty DataFrame if loading fails

    try:
        # Ensure 'timestamp_ny' column is converted to datetime
        df_clob_data['timestamp_ny'] = pd.to_datetime(df_clob_data['timestamp_ny'], errors='coerce')
        
        # Add a signed volume column: +1 for Bid, -1 for Ask
        df_clob_data['signed_size'] = df_clob_data['size'] * np.where(df_clob_data['side'] == 'Bid', 1, -1)

        # Define 10-second bins
        start_time = pd.Timestamp("2024-07-31 19:34:10")
        end_time = df_clob_data["timestamp_ny"].max()
        df_clob_data['time_bin'] = pd.cut(df_clob_data['timestamp_ny'], bins=pd.date_range(start_time, end_time, freq='10S'))

        # Aggregate data by time bin
        grouped = df_clob_data.groupby('time_bin').agg({
            'size': 'sum',                     # Cumulative size
            'price': 'last',                   # Last available price
            'signed_size': 'sum'               # Signed volume
        }).reset_index()

        grouped.rename(columns={'size': 'cumulative_size'}, inplace=True)
        grouped['time_bin'] = grouped['time_bin'].astype(str)  # Convert bins to string for saving
        print(f"Processing of {file_name} completed successfully.")
        return grouped

    except Exception as e:
        print(f"Error processing {file_name}: {e}")
        return pd.DataFrame()

def find_parquet_files(root_folder):
    """Find all parquet files in the given folder and its subdirectories."""
    parquet_files = []
    for root, _, files in os.walk(root_folder):
        for file in files:
            if file.endswith(".parquet"):
                parquet_files.append(os.path.join(root, file))
    return parquet_files

def process_and_save_symbol(symbol_folder, symbol_output_folder):
    """Process all files for a specific symbol and save results."""
    print(f"\nProcessing symbol folder: {symbol_folder}")
    files = find_parquet_files(symbol_folder)
    print(f"Found {len(files)} parquet files in {symbol_folder}.")

    with Pool(processes=cpu_count()) as pool:
        results = pool.map(process_file, files)

    # Combine and save results for the symbol
    all_results = [result for result in results if not result.empty]
    if all_results:
        combined_result = pd.concat(all_results, ignore_index=True)
        output_path = os.path.join(symbol_output_folder, "processed_result.csv")
        combined_result.to_csv(output_path, index=False)
        print(f"Results for symbol saved to {output_path}")
    else:
        print(f"No valid data found for symbol in {symbol_folder}.")

def main():
    # Define root folders for symbols
    root_folders = ['dwas_output', 'match_output']

    # Process all symbols in each root folder
    for root_folder in root_folders:
        print(f"\n--- Scanning root folder: {root_folder} ---")
        for symbol in os.listdir(root_folder):
            symbol_folder = os.path.join(root_folder, symbol)
            symbol_output_folder = symbol_folder  # Save output in the same folder
            if os.path.isdir(symbol_folder):
                process_and_save_symbol(symbol_folder, symbol_output_folder)

    print("\nAll symbol processing completed.")

if __name__ == "__main__":
    main()