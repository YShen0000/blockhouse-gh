import pandas as pd
import boto3
from io import StringIO
# Initialize a session using Amazon S3
s3 = boto3.client('s3')
# Define the bucket and prefix for the S3 path
bucket_name = 'tradeweb-unzipped-data'
prefix = 'dwas_output/'
# List all objects (folders) in the specified directory on S3
response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix, Delimiter='/')
# Iterate over each folder inside 'match_output'
for prefix_dir in response.get('CommonPimport pandas as pd
import boto3
from io import StringIO
# Initialize a session using Amazon S3
s3 = boto3.client('s3')
# Define the bucket and prefix for the S3 path
bucket_name = 'tradeweb-unzipped-data'
prefix = 'dwas_output/'
# List all objects (folders) in the specified directory on S3
response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix, Delimiter='/')
# Iterate over each folder inside 'match_output'
for prefix_dir in response.get('CommonPrefixes', []):
    folder = prefix_dir.get('Prefix')
    # List all files in the current folder (including subfolders)
    file_response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder)
    # Check if processed_result.csv exists in the subfolder
    for obj in file_response.get('Contents', []):
        file_key = obj.get('Key')
        if file_key.endswith('processed_result.csv'):
            try:
                # Fetch the CSV file from S3
                obj = s3.get_object(Bucket=bucket_name, Key=file_key)
                csv_data = obj['Body'].read().decode('utf-8')
                # Read the CSV file into a pandas DataFrame
                df = pd.read_csv(StringIO(csv_data))
                # Remove duplicates based on the time_bin column while keeping the highest price for each bin
                df = df.sort_values(by='price', ascending=False).drop_duplicates(subset='time_bin', keep='first')
                # Split 'time_bin' column into 'start_time' and 'end_time' columns
                df['start_time'] = pd.to_datetime(df['time_bin'].str.split(',').str[0].str.strip('()'))
                df['end_time'] = pd.to_datetime(df['time_bin'].str.split(',').str[1].str.strip('[])'))
                # Add date column to group by day
                df['date'] = df['start_time'].dt.date
                # Group data by day and calculate the range for each day
                daily_range = df.groupby('date').agg(
                    start_range=('start_time', 'min'),
                    end_range=('end_time', 'max')
                ).reset_index()
                # Sort the DataFrame by 'time_bin'
                df = df.sort_values(by='time_bin')
                # Filter the DataFrame to include only data between 9:30 AM and 4:00 PM
                df = df[(df['start_time'].dt.time >= pd.to_datetime('09:30:00').time()) &
                        (df['end_time'].dt.time <= pd.to_datetime('16:00:00').time())]
                # Remove the new columns {'start_time', 'end_time', 'date'}
                df = df.drop(['start_time', 'end_time', 'date'], axis=1)
                # Prepare to save the processed CSV back to S3
                processed_csv = StringIO()
                df.to_csv(processed_csv, index=False)
                processed_csv.seek(0)
                # Construct the output path and upload the processed file back to S3
                output_path = file_key.replace('processed_result.csv', 'preprocessed_data.csv')
                s3.put_object(Bucket=bucket_name, Key=output_path, Body=processed_csv.getvalue())
                print(f'Processed data saved to {output_path}')
            except Exception as e:
                print(f"Error processing {file_key}: {e}")refixes', []):
    folder = prefix_dir.get('Prefix')
    # List all files in the current folder (including subfolders)
    file_response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder)
    # Check if processed_result.csv exists in the subfolder
    for obj in file_response.get('Contents', []):
        file_key = obj.get('Key')
        if file_key.endswith('processed_result.csv'):
            try:
                # Fetch the CSV file from S3
                obj = s3.get_object(Bucket=bucket_name, Key=file_key)
                csv_data = obj['Body'].read().decode('utf-8')
                # Read the CSV file into a pandas DataFrame
                df = pd.read_csv(StringIO(csv_data))
                # Remove duplicates based on the time_bin column while keeping the highest price for each bin
                df = df.sort_values(by='price', ascending=False).drop_duplicates(subset='time_bin', keep='first')
                # Split 'time_bin' column into 'start_time' and 'end_time' columns
                df['start_time'] = pd.to_datetime(df['time_bin'].str.split(',').str[0].str.strip('()'))
                df['end_time'] = pd.to_datetime(df['time_bin'].str.split(',').str[1].str.strip('[])'))
                # Add date column to group by day
                df['date'] = df['start_time'].dt.date
                # Group data by day and calculate the range for each day
                daily_range = df.groupby('date').agg(
                    start_range=('start_time', 'min'),
                    end_range=('end_time', 'max')
                ).reset_index()
                # Sort the DataFrame by 'time_bin'
                df = df.sort_values(by='time_bin')
                # Filter the DataFrame to include only data between 9:30 AM and 4:00 PM
                df = df[(df['start_time'].dt.time >= pd.to_datetime('09:30:00').time()) &
                        (df['end_time'].dt.time <= pd.to_datetime('16:00:00').time())]
                # Remove the new columns {'start_time', 'end_time', 'date'}
                df = df.drop(['start_time', 'end_time', 'date'], axis=1)
                # Prepare to save the processed CSV back to S3
                processed_csv = StringIO()
                df.to_csv(processed_csv, index=False)
                processed_csv.seek(0)
                # Construct the output path and upload the processed file back to S3
                output_path = file_key.replace('processed_result.csv', 'preprocessed_data.csv')
                s3.put_object(Bucket=bucket_name, Key=output_path, Body=processed_csv.getvalue())
                print(f'Processed data saved to {output_path}')
            except Exception as e:
                print(f"Error processing {file_key}: {e}")