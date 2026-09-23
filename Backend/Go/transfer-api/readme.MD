# GO Server for APIs

## Requirements

- [Go 1.20+](https://golang.org/dl/) installed on your machine.
- [Redpanda](https://vectorized.io/docs/quick-start-docker/) (Kafka-compatible broker) running locally.
- [Docker](https://docs.docker.com/get-docker/) for running Redpanda in a container.
- [MongoDB](https://www.mongodb.com/try/download/community) installed or running via Docker.
- [AWS CLI](https://aws.amazon.com/cli/) installed and configured for S3 integration.

---

## Setup

### 1. Clone the Repository

#### **Windows**
```cmd
git clone https://github.com/yourusername/transfer-api.git
cd transfer-api
```

#### **macOS**
```bash
git clone https://github.com/yourusername/transfer-api.git
cd transfer-api
```

---

### 2. Install Dependencies

The project uses the Sarama library for Kafka integration. Install the necessary Go dependencies:

```bash
go mod tidy
```

---

### 3. Setup MongoDB for Client Credentials Storage

MongoDB is used to store client credentials for token generation.

#### **MongoDB Installation**

1. Download and install MongoDB Community Edition from the [official website](https://www.mongodb.com/try/download/community).

2. **Start MongoDB**:

   - **Windows**:
     ```cmd
     net start MongoDB
     ```

   - **macOS**:
     ```bash
     brew tap mongodb/brew
     brew install mongodb-community@6.0
     brew services start mongodb/brew/mongodb-community@6.0
     ```

3. **Create the `authdb` Database and `clients` Collection**:
   Use the MongoDB shell to insert client credentials:

   ```javascript
   mongosh
   use authdb
   db.createCollection("clients")
   db.clients.insertOne({"client_id": "exampleClientID","client_secret": "exampleClientSecret","scopes": ["transfer-data"]})
   ```

   Replace `"exampleClientID"` and `"exampleClientSecret"` with secure values for production.

---

### 4. Running Redpanda (Kafka Broker)

#### **Start a Local Redpanda Instance**

```bash
docker run -d --name=redpanda -p 9092:9092 -p 9644:9644 docker.redpanda.com/vectorized/redpanda:v23.1.8
```

#### **Create the Required Kafka Topic**

```bash
docker exec -it redpanda rpk topic create your-topic-name
```

---

### 5. Set Up AWS S3 Bucket

1. Create a new bucket in the **AWS Management Console**.
2. Update your `.env` file with the following variables:

   ```plaintext
   AWS_ACCESS_KEY_ID=your-access-key-id
   AWS_SECRET_ACCESS_KEY=your-secret-access-key
   S3_REGION=us-east-1
   S3_BUCKET_NAME=your-bucket-name
   KAFKA_TOPIC=your-topic-name
   ```

---

### 6. Running the API Server

To run the API server that sends generated fake data to the Kafka topic:

#### **Windows**
```cmd
go run cmd/main.go
```

#### **macOS**
```bash
go run cmd/main.go
```

The API server will start and listen on `localhost:8080`.

---

### 7. Testing the API with Python SDK

The API uses JWT-based authentication. A sample Python SDK (`sdk.py`) is provided to obtain a token and make API requests.

#### **SDK Usage**

1. **Navigate to the SDK Folder**:

   - **Windows**:
     ```cmd
     cd PythonSDK
     ```

   - **macOS**:
     ```bash
     cd PythonSDK
     ```

2. **Obtain Access Token**:
   The SDK will use the `/get-token` endpoint to get an access token with the stored client credentials.

3. **Call Protected Endpoint**:
   The SDK then calls `/transfer-data`, passing the token in the Authorization header to securely transfer data to the Kafka topic.

   ```bash
   python sdk.py transfer-data
   ```

   The `transfer-data` command should return a success message if the data was successfully sent to Kafka.

---

### 8. Verifying Data in Kafka Topic

You can consume messages from the Kafka topic in Redpanda to verify that the data has been sent.

#### **Using Redpanda CLI**

```bash
docker exec -it redpanda rpk topic consume your-topic-name
```

You should see the generated trade data being printed out.

---

## Code Documentation

### **1. `main.go`**
**Purpose**: The main entry point for the API server that handles JWT authentication, data transfer to Kafka, and MongoDB integration.

- **Endpoints**:
  - `/`: Root handler to verify the server is running.
  - `/get-token`: Generates JWT for valid client credentials stored in MongoDB.
  - `/transfer-data`: A protected endpoint that sends generated data to Kafka and uploads it to S3.

- **Key Features**:
  - Middleware for JWT validation.
  - Kafka producer for sending messages.
  - MongoDB client for storing and validating client credentials.

---

### **2. `generator.go`**
**Purpose**: Generates fake trading data for testing the pipeline.

- **Functionality**:
  - Generates data including `symbol`, `price`, `volume`, and `timestamp` in JSON format.

---

### **3. `producer.go`**
**Purpose**: Sends generated data to Kafka and uploads it to S3.

- **Key Features**:
  - Kafka producer to send messages to a specified topic.
  - AWS S3 client to upload data to an S3 bucket.
  - Configures Kafka and S3 using environment variables.
  - Logs Kafka partition and offset for each message.

---

### **4. `consumer.go`**
**Purpose**: Listens for Kafka messages and uploads them to S3.

- **Key Features**:
  - Consumes messages from a Kafka topic.
  - Uploads received messages to S3 as JSON files.
  - Configures Kafka and S3 clients dynamically.

---

## Authentication Flow

The API uses JWTs for authentication, and the flow is as follows:

1. **Client Credential Validation**: The client provides `client_id` and `client_secret` to the `/get-token` endpoint.
2. **Token Generation**: If credentials are valid, a JWT is generated and returned.
3. **Access Protected Endpoint**: The SDK includes this JWT in the Authorization header when accessing the `/transfer-data` endpoint.

--- 

