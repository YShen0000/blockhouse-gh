import pandas as pd

# Load the CSV file
input_file_path = "C:/Users/Prasanna/Downloads/test_csv.csv"  # Replace with your actual file path
df = pd.read_csv(input_file_path)

# Convert the 'Date' column to the desired format (YYYY-MM-DD)
df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y').dt.strftime('%Y-%m-%d')

# Save the updated DataFrame back to a new CSV file
output_file_path = 'corrected_dates_output.csv'  # You can specify your desired output file path
df.to_csv(output_file_path, index=False)

print(f"Date format corrected and saved to {output_file_path}")
