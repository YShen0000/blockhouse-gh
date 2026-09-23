# Instructions for Using Firm Analysis API

For full documentation refer to the following site:
[Notion Blockhouse Equity Report](https://www.notion.so/blockhouse1/Blockhouse-Report-Equities-113ca1a7e5b48016b984cf85828f5c9b)

## Overview

This Django API provides endpoints to generate and display various financial reports based on the `Summary_Report.csv` file. The main functionalities include generating bar charts, stacked bar charts, and tables from the firm's data, as well as providing textual analysis based on stock performance.

---

## Functions and How They Work

### 1. `create_graphs(data)`
- **Input:** 
  - `data`: A DataFrame containing the firm's data from the `Summary_Report.csv`.
- **Output:** 
  - `bar_chart_dict`: A dictionary representing the bar chart data.
  - `stacked_bar_chart_dict`: A dictionary representing the stacked bar chart data.
  - `table_dict`: A dictionary representing the table data.
  - `line_chart_dict`: A dictionary representing placeholder data for a line chart (still in progress).

- **How It Works:**
  - Generates data for:
    - Bar charts (open/close slippage values for TWAP, VWAP, and LSTM strategies).
    - Stacked bar charts (savings for each stock vs TWAP and VWAP).
    - A table displaying savings and other relevant stock data.
    - A placeholder line chart for weekly savings.

### 2. `firm_view(request)`
- **Input:** 
  - Request parameter `firm_name`: The name of the firm from the URL query string.
- **Output:**
  - Renders an HTML report page for the specified firm.
  
- **How It Works:**
  - Extracts firm data from `Summary_Report.csv` based on the firm name.
  - If data exists, it generates bar charts, stacked bar charts, tables, and analysis text.
  - If no data is found, returns a 404 response.

### 3. `firm_graph_data(request)`
- **Input:** 
  - Request parameter `firm_name`: The name of the firm from the URL query string.
- **Output:**
  - Returns a JSON response with the generated chart and table data for the specified firm.

- **How It Works:**
  - Similar to `firm_view` but outputs JSON for integration into the front end.
  - Contains bar charts, stacked bar charts, table data, and textual analysis.

### 4. `firm_list(request)`
- **Output:** 
  - Renders an HTML page listing all firms.
  
- **How It Works:**
  - Reads the `Summary_Report.csv` file and generates an HTML list of links for each firm.

### 5. `get_firm_list(request)`
- **Output:** 
  - Returns a JSON response containing the list of firm names.
  
- **How It Works:**
  - Reads the `Summary_Report.csv` file and sends a list of firm names as JSON.

### 6. `book_call(request)`
- **Output:**
  - Redirects the user to a Calendly link to schedule a call.
  
- **How It Works:**
  - Performs a simple redirect to a Calendly link.

---

## How to Use the API

### 1. Access the Firm Reports
- **Endpoint:** `/api/firms/firm?firm_name=<FirmName>`
- Replace `<FirmName>` with the name of the firm you're interested in (e.g., `Day Hagan Asset Management`).
- This will render a report page with the firm’s data, charts, and analysis.

### 2. Get JSON Data for Firm
- **Endpoint:** `/api/firms/firm-graph-data?firm_name=<FirmName>`
- This will return JSON data for the firm’s charts, tables, and analysis.

### 3. List All Firms
- **Endpoint:** `/api/firms/firm-list/`
- This will render an HTML page with a list of all firms.

### 4. Get List of Firms in JSON
- **Endpoint:** `/api/firms/get-firm-list/`
- This returns a JSON response with a list of all firm names.

### 5. Book a Call
- **Endpoint:** `/api/firms/book-call/`
- This will redirect to a Calendly link to schedule a call.

---

## Notes

- Ensure the `Summary_Report.csv` is updated regularly, as it provides the base data for generating reports and charts.
- The **line chart** functionality is still a work in progress and currently uses placeholder data.
- The API relies heavily on Plotly for chart generation and Pandas for data manipulation.
