# Welcome to Blockhouse!

## Introduction
Blockhouse optimizes trading execution for both buy-side and sell-side institutions. The platform ingests trade data and provides actionable insights that improve execution strategies, reduces transaction costs and ensures compliance with financial regulations such as FINRA.

## Installation & Setup
1. Clone the repo

```
    git clone https://github.com/Blockhouse-Repo/Blockhouse.git
```

2. Create a .env file locally and paste env from the link below

```
    https://www.notion.so/blockhouse1/environmental-variables-2ae897fb879a4aa980ef3b7d2e0cdee4?pvs=4
```

## Setting Up the Backend

The backend of Blockhouse is built using Django. To set up the backend, you will need to install the required Python packages, perform database migrations, and then run the Django server.

### Steps:

1. **Install Python Packages**: First, you need to install the necessary Python packages. Open your terminal and navigate to the directory where you have the Blockhouse backend code. Then run the following command:

    ```bash
    pip install -r requirements.txt
    ```

    This command will install all the Python packages listed in the `requirements.txt` file.
    
    If you haven't installed django, run the following commands:
    ```bash
    pip install djangorestframework
    pip install --upgrade djangorestframework-simplejwt
    ```

3. **Database Migrations**: Before running the server, it's essential to set up your database. Django uses migrations to manage database schema changes. Run the following commands in the same directory:

    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

    These commands will create the necessary database tables and apply any database schema changes.

4. **Run the Server**: To start the Django server, run:

    ```bash
    python manage.py runserver
    ```

    After running this command, the backend will be accessible at `http://localhost:8000`.

## Accessing Blockhouse

After you have both the backend and frontend running, you can access the complete Blockhouse application. The backend API endpoints are available at `http://localhost:8000`.

## How to raise PR's

- Follow PR creation steps from this [Notion Document](https://blockhouse1.notion.site/How-to-Create-a-Pull-Request-44020cdbda2e4f36bcf5d3a7a07ee4a2)

> **Note:**

- Do not push code directly to main, staging or development branch
- Diverge from main or staging or development and create PR to a specific branch according to task and info provided by a senior member from team.
- Only raise PR's with commits for which a Linear ticket has been assigned to you

## Tech Stack

- **Django** to handle server-side logic, and APIs
- **React** for building the user interface.
- **Next Js middleware** with **Next auth** for authorization
- **TypeScript** provides static typing for JavaScript
- **Mongo DB** for database
- **FastAPI** is a modern Python framework for building fast, high-performance APIs
- **Plaid** to get users financial data from brokerages

## Project structure

#### Backend

The backend is written in Django and data is stored in Postgres. The entry point of the Django app and its configuration is located in the `Blockhouse` directory. The `Analytics` and `Chatbot` directories consist of modular functions and handlers for the respective features. The `Blockhouse` directory also contains the `settings.py` file which contains the configuration for the Django app and orchestrates all the views contained in the `views.py` file.

* `Analytics`: Contains migrations and functions pertaining to the analytics features. The `views` directory powers the API endpoints for the dashboard. All the calculations according to different charts are in the respective view file, for ex. `views/bid_ask_chart.py`.
* `Chatbot`: Contains functions pertaining to the chatbot feature. It also contains integrations with OpenAI and Pinecone. 

#### Chatbot flow

##### Intent Embedding 
* First the intents are turned to embeddings using `all-MiniLM-L6-v2` model running locally. The model is loaded using `SentenceTransformer` from `sentence_transformers` library.
* The embeddings are indexed into Pinecone index.

##### Intent Classification
* The query is passed through OpenAI api to get the intent in a structured format. The output includes parameters like `intent`, `start_date` etc.
* Embedding is calculated for the intent with the same local model and the closest matching intent is found from the Pinecone index.
* The closest intent is returned as the final intent if the confidence is greater than 0.3.

##### Query execution
* The function selected by the intent is executed along with the parameters initially extracted by OpenAI. These functions are the same as mapped against the dashboard UI.
* Original query with the function output is sent to OpenAI again for generating the final chatbot response.

## Components

- Backend(API)

  /Analytics/views/barchart.py
  
  - This file contains code for an API endpoint that processes market data into a bar chart

  /Analytics/views/bid_ask_chart.py
  
  - This file contains code for an API endpoint that processes market data into a bid-ask chart

  /Analytics/views/chartCalculation.py

  - This file contains code for an API endpoint that processes trade data and calculates cost savings associated with different trading benchmark

  /Analytics/views/chat.py

  - This file contains code for an API endpoint that allows a user to interact with a chatbot

  /Analytics/views/check_messages.py

  - This file contains code for an API endpoint that checks the status of a specific run within a thread

  /Analytics/views/delete_file.py

  - This file contains code for an API endpoint for deleting a file from S3 bucket

  /Analytics/views/email_capture.py

  - This file contains code for an API endpoint for capturing email with Hubspot

  /Analytics/views/executions_over_time.py

  - This file contains code for an API endpoint for summarizing P&L

  /Analytics/views/files_list.py

  - This file contains code for an API endpoint for listing the uploaded files

  /Analytics/views/heatmap.py

  - This file contains code for an API endpoint that generates a heatmap for trades

  /Analytics/views/hoodwinked.py

  - This file contains code for API endpoints that interact with Hoodwinked

  /Analytics/views/piechart.py

  - This file contains code for an API endpoint that generates a pie chart based off trade data

  /Analytics/views/send_chat_message.py

  - This file contains code for an API endpoint allowing the user to interact with the chatbot

  /Analytics/views/signin.py

  - This file contains code for an API endpoint allowing the user to signin

  /Analytics/views/signup.py

  - This file contains code for an API endpoint allowing the user to signup

  /Analytics/views/traded_quantities.py

  - This file contains code for an API endpoint for calculating the total number of traded quantities

  /Analytics/views/upload_file.py

  - This file contains code for an API endpoint allowing the user to upload their trade data
