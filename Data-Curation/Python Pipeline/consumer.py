import json
import os
import signal
import time
import tempfile
import boto3
from kafka import KafkaConsumer

# AWS S3 configuration
BUCKET_NAME = "my-datacuration-pipeline-bucket"
FOLDER_NAME = "RawDataZone/"
REGION = "us-east-1"  # Update to your S3 bucket region if different

# Batch and upload configuration
BATCH_SIZE = 100
UPLOAD_INTERVAL = 30  # Upload every 30 seconds

def upload_as_json(s3_client, data):
    file_name = f"{FOLDER_NAME}data_{int(time.time() * 1000)}.json"
    
    # Create a temporary JSON file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8') as tmp_file:
        json.dump(data, tmp_file)
        tmp_file_path = tmp_file.name

    # Upload the temporary JSON file to S3
    with open(tmp_file_path, 'rb') as file:
        s3_client.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=file)
    print(f"Uploaded to S3 as a single JSON file: {file_name}")
    
    # Remove the temporary file
    os.remove(tmp_file_path)

def main():
    consumer = KafkaConsumer(
        'historical-data',
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    s3_client = boto3.client('s3', region_name=REGION)

    def signal_handler(sig, frame):
        print("Interrupt received, shutting down...")
        if messages:
            upload_as_json(s3_client, messages)
        os._exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

    print("Listening for historical trading data...")
    messages = []
    last_upload_time = time.time()

    for msg in consumer:
        message_dict = msg.value
        messages.append(message_dict)
        current_time = time.time()

        if len(messages) >= BATCH_SIZE or current_time - last_upload_time >= UPLOAD_INTERVAL:
            upload_as_json(s3_client, messages)
            messages.clear()
            last_upload_time = current_time

    if messages:
        upload_as_json(s3_client, messages)

if __name__ == "__main__":
    main()
