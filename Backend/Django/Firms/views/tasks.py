from celery import shared_task, chord
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time
import os
import yfinance as yf
from datetime import date, timedelta, datetime
import logging
import json
import boto3
from random import random
from django.conf import settings

logging.basicConfig(level=logging.INFO, filename='error_log.txt', filemode='w',
                    format='%(name)s - %(levelname)s - %(message)s')

@shared_task
def update_summary_report():
    total_firms = 5  # len(df.index)-1
    batch_size = 3 # 5
    batches = [(i, min(i + batch_size, total_firms)) for i in range(0, total_firms, batch_size)]

    # First chord: Scraping tasks and merging CSVs
    scraping_tasks = [scrape_companies.s(start, end) for start, end in batches]
    first_chord = chord(scraping_tasks)(merge_csvs.s(batches))

    return "Scraping tasks scheduled and second chord will run after the first one"

def scrape_callback(batches):
    # Define the second chord
    second_tasks = [gather_all_data_post_scrape.s(start, end) for start, end in batches]  # Replace with your actual task
    second_chord = chord(second_tasks)(merge_summary_report_csvs.s())  # Define the final callback task for the second chord

# Imports the data from yfinance api for each stock for the firms stocks
# Input:    stock_list      (list of stocks for this firm),
#           firm_name       (name of the firm we are analyzing),
#           delta_time      (the historical time interval we are looking at eg. past 25 days),
#           time_interval   (the time interval in terms of how often we want data eg. data every day='1d')
#
# Output:   combined_data   (the total data for all the stocks for this firm based on the inputs)
def import_data(stock_list, firm_name, delta_time, time_interval):
    # Fresh data up to "today" cant get todays data directly because that costs money and is paid from PolygonAPI
    end_date = date.today()
    # Start date is "today" aka yesterday - delta_time
    start_date = end_date - timedelta(days=delta_time)
    combined_data = []
    # For each of the four tickers
    for ticker in stock_list:
        try:
            # Fetch the data based on the start and end dates (creates a time interval DIFFERENT from actual time_interval variable)
            # time_interval = how often we want to fetch data. For example every hour: '1h' or every day: '1d'
            time.sleep(random(0, 2))
            data = yf.download(ticker, start=start_date, end=end_date, interval=time_interval)
            # Create a column to store ticker along with data
            data['Ticker'] = ticker
            # Combine data for the four stocks into one array
            combined_data.append(data)
        except Exception as e:
            # yfinance error for that ticker causing exception. Either it doesn't exist, or its data is null, etc
            logging.error(f"Failed to download data for {ticker} for firm {firm_name}: {e}")
            continue
    # Return the four stocks data
    return combined_data

# Calculates the TWAP Prices for N number of stocks
# Input:    num_stocks (total number of stocks we are calculating TWAP Values for),
#           all_stock_data (stock data for num_stocks stocks)
#
# Output:   all_twap (a list of calculated TWAP values for num_stocks stocks)
def calculate_twap(num_stocks, all_stock_data):
    # Create an Array to store all TWAP Prices
    all_twap = []
    for i in range(num_stocks):
        net_daily_avg_price = 0
        for j in range(len(all_stock_data[i]['Open'])):
            # Calculate the average price of the stock for each time step (dependent on what time step was fetched from yfinance)
            day_avg_price = 0
            for category in ['Open', 'Close', 'High', 'Low']:
                day_avg_price += all_stock_data[i][category].iloc[j]
            day_avg_price /= 4
            # Keep track of running sum of all days average price
            net_daily_avg_price += day_avg_price
        # TWAP = Sum of all average day prices / number of days
        all_twap.append(net_daily_avg_price / len(all_stock_data[i]['Open']))
    # Return an array of length num_stocks with the calculated TWAP value for each stock
    return all_twap

# Calculates the VWAP Prices for N number of stocks
# Input:    num_stocks (total nuber of stocks we are calculating VWAP Values for),
#           all_stock_data (stock data for num_stocks stocks)
#
# Output:   all_vwap (a list of calculated VWAP values for num_stocks stocks)
def calculate_vwap(num_stocks, all_stock_data):
    # Create an array to store all VWAP Prices
    all_vwap = []
    for i in range(num_stocks):
        net_daily_avg_price_x_volume = 0
        net_volume = 0
        for j in range(len(all_stock_data[i]['Open'])):
            # Calculate the average price of the stock for each time step (dependent on what time step was fetched from yfinance)
            day_avg_price = 0
            for category in ['Open', 'Close', 'High', 'Low']:
                day_avg_price += all_stock_data[i][category].iloc[j]
            day_avg_price /= 4
            # Multiply each days average price with each days volume
            day_avg_price *= all_stock_data[i]['Volume'].iloc[j]
            # Keep a running sum of the net volume for ALL days
            net_volume += all_stock_data[i]['Volume'].iloc[j]
            net_daily_avg_price_x_volume += day_avg_price
        # VWAP = ( sum of (daily average price * daily shares traded) ) / net volume for all days
        all_vwap.append(net_daily_avg_price_x_volume / net_volume)
    # Return an array of length num_stocks with the calculated VWAP value for each stock
    return all_vwap

# Calculates the average of an array
# Input:    array (any array with length >= 1)
#
# Output:   (average = sum(array elements) / num elements)
def array_average(array):
    return sum(array) / len(array)

# ML API endpoint fetch for stock predictions
# Ask ML team for information on how this works
def fetch_bhouse_predic(ticker, action):
    try:
        # Prepare your JSON payload
        payload = {
                "ticker": ticker,
                "action": action,
                "end_timestamp": str(datetime.today().strftime('%Y-%m-%d')),
                "backtest": True,
            }
        request_body = json.dumps(payload)
        # Create a low-level client representing Amazon SageMaker Runtime
        sagemaker_runtime = boto3.client(
            "sagemaker-runtime",
            region_name='us-east-1',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        # Make the prediction

        # Gets inference from the model hosted at the specified endpoint:
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName="prod-adjusted-vwap-BL-report-1", 
            Body=request_body, #bytes(request_body, 'utf-8')
            ContentType='application/json',
            InferenceComponentName="adjusted-vwap-BL-report-1-inference-component"
            )
    except Exception as e:
        print(e)
    # Decodes and prints the response body:
    return json.loads(response['Body'].read().decode('utf-8')[1:-1])

# Calculates and gatheres all of the firms data
# Input:    firm_name   (name of the firm),
#           stock_list  (list of the 4 stocks we are looking at for the firm),
#           all_shares  (list of the 4 share amounts for the 4 stocks),
#           all_change  (list of all of the change in holdings for the 4 stocks),
# 
# Output:   data        (the gathered data in json format for the firm, includes all the information:
#                           firm name, net shares for 4 stocks, stock info (name, shares, change in shares, open, close, average val,
#                           twap val, vwap val, model val) for each of the 4 stocks, along with some average info (average open, close
#                           twap, vwap, model values).)
def calculate_and_gather_firm_data(firm_name, stock_list, all_shares, all_change):
    try:
        num_stocks = len(stock_list)
        print("Firm: " + firm_name)
        print("Stock list:")
        print(stock_list)
        print("All Shares:")
        print(all_shares)
        print("All Change:")
        print(all_change)
        # Processed Holdings + Gathered stock data for top three stocks for the firm
        x = import_data(stock_list, firm_name, delta_time=25, time_interval='1d')

        # Uses fetched prices of stocks from yfinance and calculates: average price = (open+close+high+low) / 4 
        prices = []
        for i in range(len(x)):
            stock_price = 0
            stock_price = sum([x[i][category].iloc[-1] for category in ['Open', 'Close', 'High', 'Low']])
            stock_price /= 4
            prices.append(stock_price)
        print("Prices Based on YFinance:")
        print(prices)
        average_price = array_average(prices)

        # Open, Close Calculations for each of the three stocks along with the average
        # Open
        all_open = [x[i]['Open'].iloc[-1] for i in range(num_stocks)]
        print("Open:")
        print(all_open)
        average_open = array_average(all_open)

        # Close
        all_close = [x[i]['Close'].iloc[-1] for i in range(num_stocks)]
        print("Close:")
        print(all_close)
        average_close = array_average(all_close)
        
        # TWAP Calculations for each of the three stocks and average using yfinance
        all_twap = calculate_twap(num_stocks=num_stocks, all_stock_data=x)
        print("TWAP:")
        print(all_twap)
        average_twap_dollar = array_average(all_twap)

        # VWAP Calculations for each of the three stocks and average using yfinance
        all_vwap = calculate_vwap(num_stocks=num_stocks, all_stock_data=x)
        print("VWAP:")
        print(all_vwap)
        average_vwap_dollar = array_average(all_vwap)

        # Fetches Model estimates for stocks. Skips firms with anything that isnt able to be analyzed by the model (ETFs, etc)
        all_bhouse_buy = []
        for i in range(4):
            try:
                # Fetch data from Sagemaker Endpoint
                all_bhouse_buy.append(fetch_bhouse_predic(stock_list[i], "buy")['price'])
            except Exception as e:
                # If the stock data couldnt be fetched
                logging.error(f"ERROR: Could not gather information on {stock_list[i]} for buy")
        
        print("BHouse Buy:")
        print(all_bhouse_buy)
        # Average Blockhouse Model Buy prices for the 4 stocks
        average_bhouse_buy = array_average(all_bhouse_buy)

        all_bhouse_sell = []
        for i in range(4):
            try:
                all_bhouse_sell.append(fetch_bhouse_predic(stock_list[i], "sell")['price'])
            except Exception as e:
                logging.error(f"ERROR: Could not gather information on {stock_list[i]} for sell")
        print("BHouse Sell:")
        print(all_bhouse_sell)
        # Average Blockhouse Model Sell prices for the 4 stocks
        average_bhouse_sell = array_average(all_bhouse_sell)
        print("\n")

        data = {
            # Name of Firm
            'FileName': firm_name,

            # Number of Shares in the three stocks we are looking at
            'Shares': sum(all_shares),

            #Stock 1 Name
            'Stock1': stock_list[0],
            # Stock 1 net shares
            'Shares1': all_shares[0],
            # Stock 1 Change in Shares
            'Change1': all_change[0],
            # Stock 1 Value (average calculated based on Open, Close, High, Low)
            'Value1': prices[0],
            # Open value of the stock (most recent)
            'Open1': all_open[0],
            # Close value of the stock (most recent)
            'Close1': all_close[0],
            # Stock 1 TWAP Calculated Value
            'TWAPVal1': all_twap[0],
            # Stock 1 VWAP Calculated Value
            'VWAPVal1': all_vwap[0],
            # Stock 1 BHouse Calculated Value
            'BHBuy1': all_bhouse_buy[0],

            'BHSell1': all_bhouse_sell[0],

            # Stock 2 Name
            'Stock2': stock_list[1],
            # Stock 2 net shares
            'Shares2': all_shares[1],
            # Stock 2 Change in Shares
            'Change2': all_change[1],
            # Stock 2 Value (average calculated based on Open, Close, High, Low)
            'Value2': prices[1],
            # Open value of the stock (most recent)
            'Open2': all_open[1],
            # Close value of the stock (most recent)
            'Close2': all_close[1],
            # Stock 2 TWAP Calculated Value
            'TWAPVal2': all_twap[1],
            # Stock 2 VWAP Calculated Value
            'VWAPVal2': all_vwap[1],
            # Stock 2 BHouse Calculated Value
            'BHBuy2': all_bhouse_buy[1],

            'BHSell2': all_bhouse_sell[1],

            # Stock 3 Name
            'Stock3': stock_list[2],
            # Stock 3 net shares
            'Shares3': all_shares[2],
            # Stock 3 Change in Shares
            'Change3': all_change[2],
            # Stock 3 Value (average calculated based on Open, Close, High, Low)
            'Value3': prices[2],
            # Open value of the stock (most recent)
            'Open3': all_open[2],
            # Close value of the stock (most recent)
            'Close3': all_close[2],
            # Stock 3 TWAP Calculated Value
            'TWAPVal3': all_twap[2],
            # Stock 3 VWAP Calculated Value
            'VWAPVal3': all_vwap[2],
            # Stock 3 BHouse Calculated Value
            'BHBuy3': all_bhouse_buy[2],

            'BHSell3': all_bhouse_sell[2],

            # Stock 4 Name
            'Stock4': stock_list[3],
            # Stock 4 net shares
            'Shares4': all_shares[3],
            # Stock 4 Change in Shares
            'Change4': all_change[3],
            # Stock 4 Value (average calculated based on Open, Close, High, Low)
            'Value4': prices[3],
            # Open value of the stock (most recent)
            'Open4': all_open[3],
            # Close value of the stock (most recent)
            'Close4': all_close[3],
            # Stock 4 TWAP Calculated Value
            'TWAPVal4': all_twap[3],
            # Stock 4 VWAP Calculated Value
            'VWAPVal4': all_vwap[3],
            # Stock 4 BHouse Calculated Value
            'BHBuy4': all_bhouse_buy[3],

            'BHSell4': all_bhouse_sell[3],

            # Average overall Price for the three stocks above
            'AvgPrice': average_price,
            # Average Open Cost for the three stocks above
            'AvgOpen': average_open,
            # Average Close Cost for the three stocks above
            'AvgClose': average_close,

            # Average TWAP Value for the three stocks above
            'AvgTWAPVal': average_twap_dollar,
            # Average VWAP Value for the three stocks above
            'AvgVWAPVal': average_vwap_dollar,
            # Average BHouse Value for the three stocks above
            'AvgBHBuy': average_bhouse_buy,

            'AvgBHSell': average_bhouse_sell,
        }
        return data
    except Exception as e:
        logging.error(f"Failed to process firm {firm_name}: {e}")

# All other functions run here.
# Step by step:
#       1. Check if we have data from whale wisdom
#           a. if yes, calculate all data using calculate_and_gather_firm_data function, add the data to the csv. Skip step 2.
#           b. if no, go to step 2.
#       2. (Only if we dont have firm data from whalewisdom) Fetch data from AdvisorPro
#           a. if we have the AdvisorPro xlsx file for the firm, calculate_and_gather_firm_data.
#           b. if no, write firm name to a list to output to the user indicating that we need firm data from AdvisorPro for that firm
#       3. Write all outputs:
#           a. Summary_Report.csv               (holds all of the firm data that the code could calculate for)
#           b. AdvisorPro_Files_Needed.csv      (list of the firms that we could not find on whalewisdom and we dont have an AdvisorPro
#                                                       xlsx file for)
@shared_task
def gather_all_data_post_scrape(start_idx, end_idx):
    summary_data = []
    whale_wisdom_data = pd.read_csv(os.getcwd() + "/Firms/views/companies_output.csv")
    advisor_pro_files_needed = []
    firms = whale_wisdom_data["FileName"].to_list()[start_idx:end_idx]
    # For each firm
    for idx in range(start_idx, end_idx):
        firm_name = whale_wisdom_data["FileName"][idx]
        # If we have whalewisdom data:
        if whale_wisdom_data["Error"][idx] == "No":
            try:
                # List of 4 stocks for the firm
                stock_list = [whale_wisdom_data["IncStock1"][idx], whale_wisdom_data["IncStock2"][idx], whale_wisdom_data["DecStock1"][idx], whale_wisdom_data["DecStock2"][idx]]
                # Removing any trailing data for tickers (eg. GBLI PUT = GBLI, need to only be one word no spaces)
                stock_list = [ticker_iter.split(" ")[0] for ticker_iter in stock_list]
                # All holdings for the 4 stocks
                all_shares = [whale_wisdom_data["IncStockShares1"][idx], whale_wisdom_data["IncStockShares2"][idx], whale_wisdom_data["DecStockShares1"][idx], whale_wisdom_data["DecStockShares2"][idx]]
                # All change in shares for the four stocks
                all_change = [whale_wisdom_data["IncStockVal1"][idx], whale_wisdom_data["IncStockVal2"][idx], whale_wisdom_data["DecStockVal1"][idx], whale_wisdom_data["DecStockVal2"][idx]]
                # Calculate all data
                data = calculate_and_gather_firm_data(firm_name, stock_list, all_shares, all_change)
                if data != None:
                    # If there are no errors with the firms stocks write to our Summary_Report.csv
                    summary_data.append(data)
            except Exception as e:
                logging.error(f"Could not generate data for {firm_name}. Holdings might have error.")
                continue
        # If we dont have whalewisdom data:
        else:
            # Check if we have the xlsx file
            file_name = firm_name.replace(' ', '_') + '.xlsx'
            try:
                # If we do have it:
                path = os.getcwd() + "/views/Xlsx_Files/" + file_name
                try:
                    holdings = pd.read_excel(path)
                except Exception as e:
                    print(e)
                idx_list = []
                stock_list = []
                counter = 0
                while len(stock_list) < 4 or counter > len(holdings['Ticker']):
                    try:
                        ticker = yf.Ticker(holdings["Ticker"][counter])
                    except Exception as e:
                        counter += 1
                        continue
                    if ticker.info['quoteType'] != "ETF":
                        stock_list.append(holdings["Ticker"][counter])
                        idx_list.append(counter)
                    counter += 1
                all_shares = [holdings["Shares"][idx] for idx in idx_list]
                # Hardcoded change in shares to show a "simulated buy/sell".
                # If you bought this many shares of this and sold this many shares of this, this is how your money would change...
                all_change = [500000, 500000, -500000, -500000]
                # Calculate all data
                data = calculate_and_gather_firm_data(firm_name, stock_list, all_shares, all_change)
                if data != None:
                    # If no errors with the firm stocks, write to Summary_Report.csv
                    summary_data.append(data)
            except Exception as e:
                # No whalewisdom data, no AdvisorPro xlsx file:
                logging.error(f"Could not find {file_name}. Need an AdvisorPro file for {firm_name}.")
                advisor_pro_files_needed.append({"Firm": firm_name, "File": file_name})
                continue
    # Write to Summary_Report.csv
    summary_df = pd.DataFrame(summary_data)
    advpro_df = pd.DataFrame(advisor_pro_files_needed)
    return (summary_df.to_json(orient='records'), advpro_df.to_json(orient="records"))
    # Done!

@shared_task
def merge_summary_report_csvs(all_outputs):
    final_csv_path = '/Firms/views/summary_report.csv'
    needed_csv_path = '/Firms/views/AdvisorPro_Files_Needed.csv'
    all_summary_dfs = []
    all_adv_pro_dfs = []
    for summ, advpro in all_outputs:
        summ_df = pd.read_json(summ)
        advpro_df = pd.read_json(advpro)
        all_summary_dfs.append(summ_df)
        all_adv_pro_dfs.append(advpro_df)
    final_df = pd.concat(all_summary_dfs, ignore_index=True)
    needed_df = pd.concat(all_adv_pro_dfs, ignore_index=True)
    final_df.to_csv(os.getcwd() + final_csv_path, mode='w')
    needed_df.to_csv(os.getcwd() + needed_csv_path, mode='w')
    return "Completed update of Summary_Report.csv"


@shared_task
def merge_csvs(all_outputs, batches):
    # Define paths
    final_csv_path = '/Firms/views/companies_output.csv'
    all_dfs = []
    for out in all_outputs:
        out_df = pd.read_json(out)
        all_dfs.append(out_df)
    final_df = pd.concat(all_dfs, ignore_index=True)
    final_df.to_csv(os.getcwd() + final_csv_path, mode='w')
    time.sleep(1)
    scrape_callback(batches)
    return f"Done! Merged all temp_outputs to companies_output.csv csv_files"

@shared_task
def scrape_companies(start_idx, end_idx):
    # Load companies from CSV file
    csv_file_path = os.getcwd() + "/Firms/views/All_firm_names.csv"  # Path to your CSV file containing the list of companies
    companies_df = pd.read_csv(csv_file_path)

    # Extract the company names from the 'FileName' column
    companies = companies_df['FileName'].tolist()[start_idx:end_idx]

    # Initialize the result dictionary
    results = {}

    filter_out_etfs = True

    # Function to process each company
    def process_company(driver, company):
        company_data = {
            "Increase": [],
            "Decrease": []
        }

        try:
            # Open WhaleWisdom and wait for page to load
            driver.get("https://whalewisdom.com")
            time.sleep(3)  # Allow page to load completely
            driver.maximize_window()  # Make the Chrome window full screen
            time.sleep(2)

            # Locate the filter dropdown to select "13F Filers Only"
            try:
                # First attempt: locate the dropdown using its class and role attributes
                filter_dropdown = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@class='v-input__slot' and @role='button' and contains(@aria-owns, 'list')]"))
                )
                filter_dropdown.click()

                # Wait for dropdown menu to open and select "13F Filers Only"
                filter_option = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'v-list-item__title') and text()='13F Filers Only']"))
                )
                filter_option.click()

            except (TimeoutException, NoSuchElementException):
                # Second attempt: locate the dropdown using an alternative XPath
                try:
                    filter_dropdown_alternative = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'v-input') and contains(@class, 'v-select')]//div[@role='button']"))
                    )
                    filter_dropdown_alternative.click()

                    # Wait for dropdown menu to open and select "13F Filers Only"
                    filter_option = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'v-list-item__title') and text()='13F Filers Only']"))
                    )
                    filter_option.click()

                except (TimeoutException, NoSuchElementException) as filter_exception:
                    # Handle case where filter dropdown or filter option cannot be found
                    return {"Error": "Unable to locate the 13F Filers Only filter"}

            # Locate the search box by placeholder
            search_box = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search for funds/stocks']"))
            )
            search_box.clear()
            search_box.send_keys(company)
            search_box.send_keys(Keys.RETURN)  # Press Enter to trigger search

            # Wait for the search results popup to appear
            try:
                # Check if search results are available
                search_results = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='v-card v-sheet theme--light rounded-0']//a"))
                )
                search_results.click()

            except TimeoutException:
                # No search results were found, handle this specific case
                return {"Error": "No search results"}

            # Wait for the company's page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)  # Allow the company's page to load fully

            # Locate the "Holdings" tab and click on it
            holdings_tab = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='tab' and contains(text(), 'Holdings')]"))
            )
            holdings_tab.click()

            # Wait for the holdings section to load
            time.sleep(5)
            if (filter_out_etfs):
                try:
                    additional_filters_button = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Click to See Additional Filters')]"))
                    )
                    additional_filters_button.click()
                except (TimeoutException, NoSuchElementException):
                    print("Unable to locate the 'Click to See Additional Filters' button.")

                time.sleep(3)

                # After clicking on the "Click to See Additional Filters" button

                # Locate and click the "Is ETF?" dropdown
                try:
                    is_etf_dropdown = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, "//label[contains(text(), 'Is ETF?')]/following-sibling::div[@class='v-select__selections']"))
                    )
                    is_etf_dropdown.click()
                    # Wait for dropdown menu to open and select "No"
                    filter_option = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'v-list-item__title') and text()='No']"))
                    )
                    filter_option.click()
                except (TimeoutException, NoSuchElementException):
                    print("Unable to locate the 'Is ETF?' dropdown.")

            # Click on the "Change in Shares" column to sort (Largest Decrease)
            change_in_shares_column = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//th[contains(@aria-label, 'Change in Shares')]"))
            )
            change_in_shares_column.click()

            # Add a delay after clicking to allow the table to update
            time.sleep(5)

            # Extract ticker and change in shares for the first two rows after sorting by largest decrease in shares
            for i in range(1, 3):
                row_xpath = f"//table//tbody//tr[{i}]//td"
                row_elements = driver.find_elements(By.XPATH, row_xpath)

                # Clean up row elements by removing all leading blank entries
                formatted_row_elements = [element.text.strip() for element in row_elements if element.text.strip() != ""]
                # print(f"Formatted Row Elements (Decrease) for {company}, Row {i}: {formatted_row_elements}")

                # Extract ticker (first non-empty value)
                ticker = formatted_row_elements[0] if len(formatted_row_elements) > 0 else "N/A"
                ticker_shares = formatted_row_elements[3] if len(formatted_row_elements) > 3 else "N/A"

                # Extract change in shares using direct XPath
                change_in_shares_xpath = f"//table//tbody//tr[{i}]//td[9]/span"
                change_in_shares_element = driver.find_element(By.XPATH, change_in_shares_xpath)
                change_in_shares = change_in_shares_element.text.strip() if change_in_shares_element else "N/A"

                # Convert change_in_shares to integer
                change_in_shares = change_in_shares.replace(",", "")
                if change_in_shares.lower() == "no change":
                    change_in_shares = 0
                else:
                    try:
                        change_in_shares = int(change_in_shares)
                    except ValueError:
                        change_in_shares = "N/A"

                # Convert change_in_shares to integer
                ticker_shares = ticker_shares.replace(",", "")
                if ticker_shares.lower() == "no change":
                    ticker_shares = 0
                else:
                    try:
                        ticker_shares = int(ticker_shares)
                    except ValueError:
                        ticker_shares = "N/A"

                # Add to "Decrease" list in company data
                company_data["Decrease"].append([ticker, change_in_shares, ticker_shares])

            # Click on the "Change in Shares" column again to sort for largest increase
            change_in_shares_column.click()

            # Add a delay after clicking to allow the table to update
            time.sleep(5)

            # Extract ticker and change in shares for the first two rows after sorting by largest increase in shares
            for i in range(1, 3):
                row_xpath = f"//table//tbody//tr[{i}]//td"
                row_elements = driver.find_elements(By.XPATH, row_xpath)

                # Clean up row elements by removing all leading blank entries
                formatted_row_elements = [element.text.strip() for element in row_elements if element.text.strip() != ""]
                # print(f"Formatted Row Elements (Increase) for {company}, Row {i}: {formatted_row_elements}")

                # Extract ticker (first non-empty value)
                ticker = formatted_row_elements[0] if len(formatted_row_elements) > 0 else "N/A"
                ticker_shares = formatted_row_elements[3] if len(formatted_row_elements) > 3 else "N/A"

                # Extract change in shares using direct XPath
                change_in_shares_xpath = f"//table//tbody//tr[{i}]//td[9]/span"
                change_in_shares_element = driver.find_element(By.XPATH, change_in_shares_xpath)
                change_in_shares = change_in_shares_element.text.strip() if change_in_shares_element else "N/A"

                # Convert change_in_shares to integer
                change_in_shares = change_in_shares.replace(",", "")
                if change_in_shares.lower() == "no change":
                    change_in_shares = 0
                else:
                    try:
                        change_in_shares = int(change_in_shares)
                    except ValueError:
                        change_in_shares = "N/A"

                ticker_shares = ticker_shares.replace(",", "")
                if ticker_shares.lower() == "no change":
                    ticker_shares = 0
                else:
                    try:
                        ticker_shares = int(ticker_shares)
                    except ValueError:
                        ticker_shares = "N/A"

                # Add to "Increase" list in company data
                company_data["Increase"].append([ticker, change_in_shares, ticker_shares])

            return company_data

        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            # If there's an error, add an error message to the results dictionary
            error_message = str(e).split('\n')[0]  # Get a short version of the error message
            return {"Error": error_message}


    # Set up Chrome driver
    driver = webdriver.Chrome()  # Ensure ChromeDriver is in your PATH

    try:
        # First pass: Go through all companies and store the results
        for company in companies:
            results[company] = process_company(driver, company)

        # Second pass: Retry for companies with errors (excluding "No search results")
        for company, data in results.items():
            if "Error" in data and data["Error"] != "No search results":
                # Re-run the process for companies with errors other than "No search results"
                print(f"Retrying for {company} due to error: {data['Error']}")
                results[company] = process_company(driver, company)
        
        for company, data in results.items():
            if "Error" in data and data["Error"] != "No search results":
                # Re-run the process for companies with errors other than "No search results"
                print(f"Retrying for {company} due to error: {data['Error']}")
                results[company] = process_company(driver, company)

    finally:
        driver.quit()

    # Prepare the data for CSV output
    output_data = []

    for company, data in results.items():
        row = {
            # Name of the firm
            "FileName": company,
            # Greatest increase in change in holdings for this firm
            "IncStock1": data["Increase"][0][0] if "Increase" in data and len(data["Increase"]) > 0 else "N/A",
            # Change in shares held for this stock (increase)
            "IncStockVal1": data["Increase"][0][1] if "Increase" in data and len(data["Increase"]) > 0 else "N/A",
            # Shares held for this stock
            "IncStockShares1": data["Increase"][0][2] if "Increase" in data and len(data["Increase"]) > 0 else "N/A",
            # Second greatest increase in change in holdings for this firm
            "IncStock2": data["Increase"][1][0] if "Increase" in data and len(data["Increase"]) > 1 else "N/A",
            # Change in shares held for this stock (increase)
            "IncStockVal2": data["Increase"][1][1] if "Increase" in data and len(data["Increase"]) > 1 else "N/A",
            # Shares held for this stock
            "IncStockShares2": data["Increase"][1][2] if "Increase" in data and len(data["Increase"]) > 1 else "N/A",
            # Greatest decrease in change in holdings for this firm
            "DecStock1": data["Decrease"][0][0] if "Decrease" in data and len(data["Decrease"]) > 0 else "N/A",
            # Change in shares held for this stock (decrease)
            "DecStockVal1": data["Decrease"][0][1] if "Decrease" in data and len(data["Decrease"]) > 0 else "N/A",
            # Shares held for this stock
            "DecStockShares1": data["Decrease"][0][2] if "Decrease" in data and len(data["Decrease"]) > 0 else "N/A",
            # Second greatest decrease in change in holdings for this firm
            "DecStock2": data["Decrease"][1][0] if "Decrease" in data and len(data["Decrease"]) > 1 else "N/A",
            # Change in shares held for this stock (decrease)
            "DecStockVal2": data["Decrease"][1][1] if "Decrease" in data and len(data["Decrease"]) > 1 else "N/A",
            # Shares held for this stock
            "DecStockShares2": data["Decrease"][1][2] if "Decrease" in data and len(data["Decrease"]) > 1 else "N/A",
            # If there was any errors or N/A values put "Yes", else "No"
            "Error": "Yes" if "Error" in data else "No"
        }
        output_data.append(row)

    # Create a DataFrame and write to CSV
    output_df = pd.DataFrame(output_data)

    return output_df.to_json(orient='records')