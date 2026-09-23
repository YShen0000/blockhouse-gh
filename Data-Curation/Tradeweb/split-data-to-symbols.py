import os
import pandas as pd
from pyarrow import parquet as pq
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = "local_data"  # Parent folder containing 'dwas' and 'match'

def list_parquet_files(directory):
    """Recursively list all parquet files in the given directory."""
    result = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".parquet"):
                result.append(os.path.join(root, file))
    print(f"Found {len(result)} parquet files in {directory}")
    return result

def process_parquet_file(file_path):
    """Read parquet file, enforce timestamp_ny as datetime, and append 'label'."""
    print(f"  Processing file: {file_path}")
    parquet_data = pq.read_table(file_path).to_pandas()

    # Ensure 'timestamp_ny' column is converted to datetime format
    if 'timestamp_ny' in parquet_data.columns:
        parquet_data["timestamp_ny"] = pd.to_datetime(
            parquet_data["timestamp_ny"], errors="coerce"
        )  # Enforce datetime, invalid formats set to NaT
    else:
        print(f"Warning: 'timestamp_ny' column not found in {file_path}")
        return pd.DataFrame()  # Return empty dataframe if column missing

    # Extract label (symbol folder) from path
    label = os.path.basename(os.path.dirname(file_path))  # e.g., 'symbol=10 Year'
    parquet_data["label"] = label

    return parquet_data

def merge_and_group_symbols(input_folder, output_folder):
    """Merge all parquet files for each symbol folder across all dates."""
    folder_path = os.path.join(BASE_DIR, input_folder)
    print(f"Processing folder: {folder_path}")
    files = list_parquet_files(folder_path)

    # Collect all dataframes by symbol name
    symbol_data = {}

    # Process files in parallel
    with ThreadPoolExecutor() as executor:
        for file_path, data in zip(files, executor.map(process_parquet_file, files)):
            if not data.empty:
                symbol = data["label"].iloc[0]  # Get symbol name
                if symbol not in symbol_data:
                    symbol_data[symbol] = []
                symbol_data[symbol].append(data)

    # Merge and save each symbol's data
    for symbol, dataframes in symbol_data.items():
        print(f"  Merging {len(dataframes)} files for symbol: {symbol}")
        merged_data = pd.concat(dataframes, ignore_index=True)

        # Sort by timestamp to ensure order
        merged_data = merged_data.sort_values(by="timestamp_ny")

        # Split data into 15-day chunks
        start_date = merged_data["timestamp_ny"].min()
        merged_data["days_from_start"] = (merged_data["timestamp_ny"] - start_date).dt.days
        merged_data["chunk"] = merged_data["days_from_start"] // 15

        # Use a counter to save the chunks
        counter = 1
        symbol_output_folder = os.path.join(output_folder, symbol)
        os.makedirs(symbol_output_folder, exist_ok=True)

        for _, group in merged_data.groupby("chunk"):
            output_path = os.path.join(symbol_output_folder, f"FN{counter}.parquet")
            print(f"    Saving: {output_path}")
            group.drop(columns=["days_from_start", "chunk"], inplace=True)
            group.to_parquet(output_path, index=False)
            counter += 1

def main():
    """Main execution function."""
    print("Starting merging and grouping process.")

    # Process 'dwas' folder first, then 'match' folder
    for folder in ["dwas", "match"]:
        print(f"\n--- Processing {folder} ---")
        output_folder = f"{folder}_output"
        os.makedirs(output_folder, exist_ok=True)
        merge_and_group_symbols(folder, output_folder)

    print("\nMerging and grouping completed.")

if __name__ == "__main__":
    main()