# Streamlit Application

Welcome to the Streamlit Application! This application consists of two main sites: **Blockhouse** and **Hoodinked**. Each site offers unique features to help you manage and visualize your data.

## Table of Contents

- [Streamlit Application](#streamlit-application)
  - [Table of Contents](#table-of-contents)
  - [Blockhouse](#blockhouse)
    - [Features](#features)
  - [Hoodinked](#hoodinked)
    - [Features](#features-1)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Running the Application](#running-the-application)
  - [Contributing](#contributing)

## Blockhouse

Blockhouse is designed to provide detailed reports and data on various firms.

### Features

- **Report**: Generate and view detailed reports on firm performance and other metrics.
- **Firms Data**: Access and manage data related to different firms.

## Hoodinked

Hoodinked offers a comprehensive set of tools for reporting, graphing, and onboarding.

### Features

- **Report**: Create and view reports on various datasets.
- **Graph**: Visualize data through interactive graphs and charts.
- **Onboard**: Manage the onboarding process for new users or data entries.

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Make sure you have the following installed on your system:

- Python 3.7 or higher
- pip (Python package installer)

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/Blockhouse-Repo/Blockhouse-Streamlit.git
    cd Blockhouse-Streamlit
    ```

2. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

### Running the Application

To run the Streamlit application, use the following command:

```sh
streamlit run app.py
```

This will start the Streamlit server and open the application in your default web browser.

## Contributing

We welcome contributions to improve this project! Please fork the repository and create a pull request with your changes. Make sure to follow the existing code style and include tests for any new features or bug fixes.


# Transaction Cost Savings Calculator - Streamlit App

## Table of Contents

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Installation Instructions](#installation-instructions)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Set Up a Virtual Environment (Optional but Recommended)](#2-set-up-a-virtual-environment-optional-but-recommended)
  - [3. Install Required Packages](#3-install-required-packages)
  - [4. Place the Data Files](#4-place-the-data-files)
- [Application Structure](#application-structure)
  - [Main Components](#main-components)
  - [Code Explanation](#code-explanation)
- [Running the Application](#running-the-application)
- [Using the Application](#using-the-application)
  - [User Inputs](#user-inputs)
  - [Understanding the Results](#understanding-the-results)
  - [Visualization](#visualization)
- [Troubleshooting](#troubleshooting)
- [Additional Notes](#additional-notes)
- [Contact Information](#contact-information)

## Introduction

The **Transaction Cost Savings Calculator** is a Streamlit application designed to help users estimate potential cost savings when executing trades in the equities market. By comparing transaction costs against benchmarks like TWAP (Time-Weighted Average Price) and VWAP (Volume-Weighted Average Price), the app provides insights into how predictive models can reduce transaction costs and improve trading efficiency.

This application leverages historical stock data and predictive modeling to calculate cost savings based on user-defined parameters such as asset class, benchmark, trading frequency, time period, and order size.

## Prerequisites

- **Python 3.7 or higher**: Ensure you have Python installed on your system.
- **Streamlit**: A Python library for creating interactive web applications.
- **Required Python Packages**: Listed in the [Installation Instructions](#installation-instructions) section.

## Installation Instructions

Follow these steps to set up and run the application on your local machine.

### 1. Clone the Repository

If not, create a new directory and place the provided `calculator_app.py` file in it.

### 2. Set Up a Virtual Environment (Optional but Recommended)

It's good practice to use a virtual environment to manage dependencies:

#### On Windows:

```bash
cd transaction-cost-calculator
python -m venv venv
venv\Scripts\activate
```

#### On macOS/Linux:

```bash
cd transaction-cost-calculator
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Required Packages

Install the necessary Python packages using `pip`:

```bash
pip install pandas numpy matplotlib scipy streamlit
```

### 4. Place the Data Files

Ensure that the following CSV files are in the same directory as your `calculator_app.py` script:

- `aapl_data.csv`
- `lstm_proj.csv`

**Note**: If you have these files in a different directory or under a folder (e.g., `data/`), adjust the file paths in the script accordingly.

#### Data Files Explanation

- **aapl_data.csv**: Contains historical data for Apple Inc. stock (AAPL), including closing prices, volume, and calculated transaction costs using the Almgren-Chriss model for various order sizes.
- **lstm_proj.csv**: Contains predicted transaction costs using an LSTM (Long Short-Term Memory) model for the same order sizes as in `aapl_data.csv`.

## Application Structure

### Main Components

1. **User Interface**: Built with Streamlit widgets to collect user inputs.
2. **Data Loading**: Reads data from CSV files into pandas DataFrames.
3. **Calculations**: Processes data to compute potential cost savings.
4. **Visualization**: Generates plots to illustrate cost savings against order sizes.
5. **Output Display**: Shows calculated results and visualizations to the user.

### Code Explanation

#### Imports

- **Data Handling**: `pandas`, `numpy`
- **Visualization**: `matplotlib.pyplot`
- **Mathematical Operations**: `scipy.interpolate`, `numpy.polyfit`, `numpy.poly1d`
- **Streamlit**: `streamlit`
- **Operating System Interaction**: `os` (for file path handling)
- **Logging**: `logging` (for error logging)

#### Main Function: `main()`

- Sets the title of the app.
- Collects user inputs using Streamlit widgets:
  - `st.selectbox` for selecting options.
  - `st.number_input` for numerical inputs.
- When the **Calculate** button is clicked, the app:
  - **Loads Data**:
    - Constructs file paths relative to the script's location using `os.path`.
    - Reads CSV files into DataFrames.
  - **Performs Calculations**:
    - Processes columns to calculate differences between actual and predicted transaction costs.
    - Fits polynomial models to the calculated savings data.
    - Defines functions to estimate cost savings for user-defined order sizes.
    - Calculates total cost savings, cost savings percentage, and excess returns based on user inputs.
  - **Displays Results**:
    - Shows calculated values using `st.write`.
    - Generates and displays plots using `matplotlib` and `st.pyplot`.
- Includes error handling to catch and display any exceptions.

#### Helper Functions

- **`process_columns()`**: Processes the DataFrame columns to calculate average transaction costs based on the smallest predicted values.
- **`fit_polynomial()`**: Fits a polynomial to the data for modeling cost savings across different order sizes.
- **`lstm_twap_cost_savings_calc()` and `lstm_vwap_cost_savings_calc()`**: Calculate estimated cost savings using the fitted polynomial models.
- **`calculate_cost_savings()`**: Calculates total cost savings, cost savings percentage, and excess returns based on user inputs and the selected benchmark.

## Running the Application

Navigate to the directory containing `calculator_app.py` and run the following command:

```bash
streamlit run calculator_app.py
```

This will start the Streamlit app, and you should see output similar to:

```plaintext
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

Open the local URL in your web browser to interact with the app.

## Using the Application

### User Inputs

- **Asset Class**: Currently limited to 'Equities'.
- **Benchmark**: Choose between 'TWAP' (Time-Weighted Average Price) and 'VWAP' (Volume-Weighted Average Price).
- **Frequency of Trades (per Time Period)**: Number of trades executed per selected time period.
- **Time Period**: Choose from 'day', 'week', 'month', or 'year'.
- **Order Size (Number of Shares)**: The size of each trade in shares.

After setting your desired parameters, click the **Calculate** button to perform the calculations.

### Understanding the Results

The app displays the following results:

- **Total Cost Savings (USD)**: The estimated total cost savings in US dollars over one year based on your inputs.
- **Cost Savings Percentage**: The cost savings expressed as a percentage of the total value traded over the year.
- **Excess Returns Relative to Benchmark**: The excess returns as a percentage relative to a benchmark return (e.g., S&P 500 annual return).

### Visualization

A plot is generated to visualize the relationship between order size and cost savings:

- **X-Axis**: Order Size (Number of Shares), displayed on a logarithmic scale.
- **Y-Axis**: Cost Savings (USD).
- **Data Points**: Actual calculated savings for different order sizes.
- **Fitted Curves**: Polynomial models fitted to the data points for both TWAP and VWAP benchmarks.

The plot helps to understand how cost savings scale with different order sizes.

## Troubleshooting

### Common Issues and Solutions

#### 1. FileNotFoundError: `[Errno 2] No such file or directory: 'aapl_data.csv'`

**Solution**:

- Ensure that `aapl_data.csv` and `lstm_proj.csv` are in the same directory as `calculator_app.py`.
- Verify that the file names are correct, including capitalization and file extensions.
- Check that the file paths in the script are correctly constructed using `os.path.join`.

#### 2. ModuleNotFoundError: No module named 'streamlit'

**Solution**:

- Install Streamlit using `pip install streamlit`.
- Ensure that you're using the correct Python interpreter, especially if using a virtual environment.

#### 3. The App Doesn't Launch or Shows a Blank Page

**Solution**:

- Check the console for any error messages.
- Ensure that there are no syntax errors or missing imports in the script.
- Verify that all required packages are installed.

#### 4. Plot Not Displaying Correctly

**Solution**:

- Ensure that `matplotlib` is installed.
- Check for any errors in the plotting code.
- Confirm that the data being plotted is in the expected format.

### Logging

The app uses Python's `logging` module to log errors. If you encounter an error, check the console output for detailed error messages.

To enable logging to the console, you can configure the logging level at the beginning of your script:

```python
import logging

logging.basicConfig(level=logging.ERROR)
```

## Additional Notes

- **Data Accuracy**: The calculations and visualizations are based on the data provided in the CSV files. Ensure that these files contain accurate and up-to-date information.
- **Adjusting Polynomial Degree**: The degree of the polynomial used in the `fit_polynomial()` function is set to 3. Depending on your data, you might need to adjust this degree for a better fit.
- **Extensibility**: While the app currently only supports 'Equities' as the asset class, it can be extended to include other asset classes by modifying the data and calculations accordingly.
- **Dependencies**: If you plan to deploy this app or share it with others, consider creating a `requirements.txt` file containing all the dependencies. You can generate it using:

  ```bash
  pip freeze > requirements.txt
  ```

## Contact Information

If you have any questions, issues, or suggestions, feel free to reach out to Nimit Dave:



---