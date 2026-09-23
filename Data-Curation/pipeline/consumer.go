from dotenv import load_dotenv
import os
import json
import signal
import sys
import time
import boto3
from confluent_kafka import Consumer, KafkaException
from threading import Timer, Lock

# Load the .env file
load_dotenv(dotenv_path='.env')

# Access environment variables
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

# Configuration
BUCKET_NAME = "my-datacuration-pipeline-bucket"
FOLDER_NAME = "RawDataZone/"
REGION = "us-east-1"
TOPIC_NAME = "historical-data"
BATCH_SIZE = 100
UPLOAD_INTERVAL = 30  # in seconds

# AWS S3 client
s3_client = boto3.client('s3', region_name=REGION, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

# Kafka consumer
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'my-group',
    'auto.offset.reset': 'latest'
})

consumer.subscribe([TOPIC_NAME])

# Lock for thread-safe access to messages
lock = Lock()
messages = []

def upload_to_s3():
    global messages
    with lock:
        if messages:
            timestamp = int(time.time() * 1e6)
            file_name = f"{FOLDER_NAME}data_{timestamp}.json"

            # Convert messages to JSON and prepare it for upload
            data = json.dumps(messages, indent=2)
            s3_client.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=data)
            print(f"Uploaded to S3 as a single JSON file: {file_name}")

            # Clear the messages list after upload
            messages = []

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    print("Interrupt received, shutting down...")

    # Upload remaining messages before exiting
    upload_to_s3()
    consumer.close()
    sys.exit(0)

# Set up signal handler for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)

# Start the periodic upload timer
def start_timer():
    Timer(UPLOAD_INTERVAL, periodic_upload).start()

# Periodic upload to S3
def periodic_upload():
    upload_to_s3()
    start_timer()

start_timer()

print("Listening for historical trading data...")

# Consume messages
try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaException._PARTITION_EOF:
                continue
            else:
                print(msg.error())
                break

        message_value = msg.value().decode('utf-8')
        with lock:
            messages.append(message_value)

            # Check if batch size is reached
            if len(messages) >= BATCH_SIZE:
                print("Batch size reached, preparing to upload...")
                upload_to_s3()
except KeyboardInterrupt:
    pass
finally:
    # Upload remaining messages before shutting down
    upload_to_s3()
    consumer.close()
