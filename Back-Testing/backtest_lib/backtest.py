import ast
import os, sys
from datetime import datetime, timedelta
import pytz
import csv
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

sys.path.append("/Users/anshulrana/Desktop/blockhouse/blockhouseTrialPeriod/Blockhouse/Back-Testing")

from plot_backtests import streamlit_metrics_plot
from plot_backtests import plot_metrics
from plot_backtests import plot_slippage_dist
from plot_backtests import plot_slippage_by_interval
from plot_backtests import plot_market_impact_against_shares
from equities.utils.fetch_merge_data import PolygonClient
# from equities.utils.data_handler import DataProcessor


from test_model.data_process import DataProcessor
from test_model.ml_prod import run_equities_sell_inference
from test_model.ml_prod import run_equities_buy_inference
from test_model.data_process import DataProcessor


# from backtest_lib.ml_prod import run_equities_sell_inference
# from backtest_lib.ml_prod import run_equities_buy_inference
from backtest_lib.loadData import get_full_day_expected_price
from backtest_lib.equities.sell.utils.benchmark_utils import (
    get_twap_trades as eq_sell_get_twap_trades,
    get_vwap_trades as eq_sell_get_vwap_trades,
    simulate_strategy as eq_sell_simulate_strategy
)
from backtest_lib.equities.buy.utils.benchmark_utils import (
    get_twap_trades as eq_buy_get_twap_trades,
    get_vwap_trades as eq_buy_get_vwap_trades,
    simulate_strategy as eq_buy_simulate_strategy
)
# from backtest_lib.options.utils.benchmark_utils import (
#     get_twap_trades as opt_get_twap_trades,
#     get_vwap_trades as opt_get_vwap_trades,
#     simulate_strategy as opt_simulate_strategy
# )

# Function to create the CSV file with headers
def create_csv_file(filename):
    # Column headers
    headers = [
        'trader_model', 
        'ticker', 
        'date', 
        'shares', 
        'slippage', 
        'market_impact', 
        'spread_cost', 
        'opportunity_cost_vs_close', 
        'opportunity_cost_vs_open', 
    ]

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)  # Write the headers
    
    print(f"CSV file '{filename}' created with headers")
    return 

# Function to append rows of various model data to the CSV file
def append_metric_rows(filename, ticker, date, shares, m_metrics_sum, t_metrics_sum, v_metrics_sum):
    with open(filename, mode='a', newline='') as file:  # 'a' mode opens the file for appending
        writer = csv.writer(file)
        writer.writerow(['Model', ticker, date, shares, m_metrics_sum[0], m_metrics_sum[1], m_metrics_sum[2], m_metrics_sum[4], m_metrics_sum[5]])
        writer.writerow(['TWAP', ticker, date, shares, t_metrics_sum[0], t_metrics_sum[1], t_metrics_sum[2], t_metrics_sum[4], t_metrics_sum[5]])
        writer.writerow(['VWAP', ticker, date, shares, v_metrics_sum[0], v_metrics_sum[1], v_metrics_sum[2], v_metrics_sum[4], v_metrics_sum[5]])
    
    print(f"Model rows added to '{filename}'.")
    return

def get_backtest_day_data(day_of_backtest, ticker):
    data_client = PolygonClient('Data') 
    data_processor = DataProcessor(data_dir = '/Users/anshulrana/Desktop/blockhouse/blockhouseTrialPeriod/Blockhouse/Back-Testing/test_model/output.csv',	news_sentiment_dir = '/Users/anshulrana/Desktop/blockhouse/blockhouseTrialPeriod/Blockhouse/Back-Testing/test_model/news_sentiment_to_merge.csv')

    backtest_datatime_obj = datetime.strptime(day_of_backtest, '%Y-%m-%d')

    # Need to get data from trading day before backtest so there are no Nan values due to rolling averages
    cal = USFederalHolidayCalendar() # Get federal holidays
    holidays = cal.holidays(start=backtest_datatime_obj - pd.DateOffset(years=1), end=backtest_datatime_obj + pd.DateOffset(years=1)) # Holidays for year of date
    data = None
    days_prior = 1 # Number of days before backtest day (most recent trading day)
    while True:
        previous_trading_day = (backtest_datatime_obj - timedelta(days=days_prior)).strftime('%Y-%m-%d')
        previous_trading_day_datetime = pd.to_datetime(previous_trading_day)
        if (previous_trading_day_datetime.weekday() >= 5) or (previous_trading_day_datetime in holidays): # Weekend or federal holiday
            days_prior += 1 
        else:
            # Get data 
            data = data_client.fetch_and_merge_data(ticker, start_date=previous_trading_day, end_date=day_of_backtest)
            # Add indicators
            # data = data_processor.add_technical_indicators(data)
            break

    # Remove data points from before backtest day
    time_str = '13:30:00'
    datetime_str = f"{day_of_backtest} {time_str}"
    target_datetime  = pd.Timestamp(datetime_str)
    startIdx = data.index[data['datetime'] == target_datetime].item()
    day_of_backtest_data = data.loc[startIdx:,:]  

    return day_of_backtest_data

def save_backtest_data(ticker, day_of_backtest):
    print("Saving OHLCV, Technical Indicators, and Minute Data")

    day_of_backtest_data = get_backtest_day_data(day_of_backtest, ticker) # Get data from backtest day
    day_of_backtest_data.to_csv(f'BacktestData/{ticker}_{day_of_backtest}.csv', index=False) # Save DataFrame to a CSV file

    time_start = '13:30:00'
    datetime_start = f"{day_of_backtest} {time_start}"
    start_time  = pd.Timestamp(datetime_start)
    time_end = '20:00:00'
    datetime_end = f"{day_of_backtest} {time_end}"
    end_time  = pd.Timestamp(datetime_end)   
    # Get and save minute data
    get_full_day_expected_price(ticker, start_time, end_time)

def load_backtest_data(ticker, day_of_backtest):
    # Check if OHLCV/Technical Indicators file already exists
    filename = f'BacktestData/{ticker}_{day_of_backtest}.csv'    
    if os.path.exists(filename):
        print(f"Loading Backtest Day Data")
        day_of_backtest_data = pd.read_csv(filename)
        day_of_backtest_data['datetime'] = pd.to_datetime(day_of_backtest_data['datetime'])
    else:
        # Use API to get data from backtest day
        print(f"Backtest Day Data Not Saved")
        save_backtest_data(ticker, day_of_backtest)  
        day_of_backtest_data = pd.read_csv(filename)
        day_of_backtest_data['datetime'] = pd.to_datetime(day_of_backtest_data['datetime'])

    # Check if minute bid/ask quote file already exists
    datetime_start = f"{day_of_backtest}_13-30-00"
    minute_filename = f'BacktestData/minute_{ticker}_{datetime_start}.csv'
    if os.path.exists(minute_filename):
        print(f"Loading Minute Bid/Ask Quote Backtest Day Data")

    else:
        print(f"Minute Bid/Ask Quote Backtest Day Data Not Saved")
        time_start = '13:30:00'
        datetime_start = f"{day_of_backtest} {time_start}"
        start_time  = pd.Timestamp(datetime_start)
        time_end = '20:00:00'
        datetime_end = f"{day_of_backtest} {time_end}"
        end_time  = pd.Timestamp(datetime_end)  
        get_full_day_expected_price(ticker, start_time, end_time)

    minute_backtest_data = pd.read_csv(minute_filename)
    minute_backtest_data['timestamp'] = pd.to_datetime(minute_backtest_data['timestamp'])
    minute_backtest_data['bid_prices'] = minute_backtest_data['bid_prices'].apply(ast.literal_eval)
    minute_backtest_data['bid_sizes'] = minute_backtest_data['bid_sizes'].apply(ast.literal_eval)
    minute_backtest_data['ask_prices'] = minute_backtest_data['ask_prices'].apply(ast.literal_eval)
    minute_backtest_data['ask_sizes'] = minute_backtest_data['ask_sizes'].apply(ast.literal_eval)
    
    return day_of_backtest_data, minute_backtest_data

def eq_sell_backtest(ticker, inventory, day_of_backtest, bt_data, min_bt_data, timeframe=390):
    print("Executing Equities Sell Backtest")

    # Use basic Linear Regression + VWAP
    model_trades = run_equities_sell_inference(ticker, day_of_backtest, timeframe, inventory, bt_data)
    # Calculating twap trades
    twap_trades = eq_sell_get_twap_trades(bt_data, inventory, timeframe)
    # Calculating vwap trades
    vwap_trades = eq_sell_get_vwap_trades(bt_data, inventory, timeframe)

    # Calculating model metrics
    model_slippage, model_market_impact, model_spread_cost, _, model_IS, model_opportunity_cost_vs_close, model_opportunity_cost_vs_open = eq_sell_simulate_strategy(model_trades, bt_data, timeframe, ticker, min_bt_data)
    model_metrics_summed = [sum(model_slippage), sum(model_market_impact), sum(model_spread_cost), sum(model_IS), model_opportunity_cost_vs_close, model_opportunity_cost_vs_open]

    # Calculating twap metrics
    twap_slippage, twap_market_impact, twap_spread_cost, _, twap_IS, twap_opportunity_cost_vs_close, twap_opportunity_cost_vs_open = eq_sell_simulate_strategy(twap_trades, bt_data, timeframe, ticker, min_bt_data)
    twap_metrics_summed = [sum(twap_slippage), sum(twap_market_impact), sum(twap_spread_cost), sum(twap_IS), twap_opportunity_cost_vs_close, twap_opportunity_cost_vs_open]

    # Calculating vwap metrics
    vwap_slippage, vwap_market_impact, vwap_spread_cost, _, vwap_IS, vwap_opportunity_cost_vs_close, vwap_opportunity_cost_vs_open = eq_sell_simulate_strategy(vwap_trades, bt_data, timeframe, ticker, min_bt_data)
    vwap_metrics_summed = [sum(vwap_slippage), sum(vwap_market_impact), sum(vwap_spread_cost), sum(vwap_IS), vwap_opportunity_cost_vs_close, vwap_opportunity_cost_vs_open]
    # Create DataFrames for each strategy's slippage
    df_model = pd.DataFrame({'timestamp': model_trades['timestamp'], "shares": model_trades['shares'], 'model_slippage': model_slippage, 'model_market_impact': model_market_impact, 'model_spread_cost': model_spread_cost})
    df_twap = pd.DataFrame({'timestamp': twap_trades['timestamp'], "shares": twap_trades['shares'], 'twap_slippage': twap_slippage, 'twap_market_impact': twap_market_impact, 'twap_spread_cost': twap_spread_cost})
    df_vwap = pd.DataFrame({'timestamp': vwap_trades['timestamp'], "shares": vwap_trades['shares'], 'vwap_slippage': vwap_slippage, 'vwap_market_impact': vwap_market_impact, 'vwap_spread_cost': vwap_spread_cost})

      # Merge TWAP and VWAP first
    df_metrics = df_twap.merge(df_vwap, on='timestamp', how='outer')
    
    # Then merge the model data
    df_metrics = df_metrics.merge(df_model, on='timestamp', how='left')
    # Convert the 'timestamp' column to datetime (if necessary)
    df_metrics['timestamp'] = pd.to_datetime(df_metrics['timestamp'])
    df_metrics = df_metrics.fillna(0)
    # Sort the DataFrame by timestamp
    df_metrics = df_metrics.sort_values('timestamp')
    df_metrics.to_csv('metrics_data.csv', index=False)
    return model_trades, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed

def eq_buy_backtest(ticker, inventory, day_of_backtest, bt_data, min_bt_data, timeframe=390):
    print("Executing Equities Buy Backtest")

    # Run model for trading
    model_trades = run_equities_buy_inference(ticker, day_of_backtest, timeframe, inventory, bt_data)

    # Calculating twap trades
    twap_trades = eq_buy_get_twap_trades(bt_data, inventory, timeframe)

    # Calculating vwap trades
    vwap_trades = eq_buy_get_vwap_trades(bt_data, inventory, timeframe)

    # Calculating model metrics
    model_slippage, model_market_impact, model_spread_cost, _, model_IS, model_opportunity_cost_vs_close, model_opportunity_cost_vs_open = eq_buy_simulate_strategy(model_trades, bt_data, timeframe, ticker, min_bt_data)
    model_metrics_summed = [sum(model_slippage), sum(model_market_impact), sum(model_spread_cost), sum(model_IS), model_opportunity_cost_vs_close, model_opportunity_cost_vs_open]

    # Calculating twap metrics
    twap_slippage, twap_market_impact, twap_spread_cost, _, twap_IS, twap_opportunity_cost_vs_close, twap_opportunity_cost_vs_open = eq_buy_simulate_strategy(twap_trades, bt_data, timeframe, ticker, min_bt_data)
    twap_metrics_summed = [sum(twap_slippage), sum(twap_market_impact), sum(twap_spread_cost), sum(twap_IS), twap_opportunity_cost_vs_close, twap_opportunity_cost_vs_open]
    
    # Calculating vwap metrics
    vwap_slippage, vwap_market_impact, vwap_spread_cost, _, vwap_IS, vwap_opportunity_cost_vs_close, vwap_opportunity_cost_vs_open = eq_buy_simulate_strategy(vwap_trades, bt_data, timeframe, ticker, min_bt_data)
    vwap_metrics_summed = [sum(vwap_slippage), sum(vwap_market_impact), sum(vwap_spread_cost), sum(vwap_IS),vwap_opportunity_cost_vs_close,vwap_opportunity_cost_vs_open]
    
    # Create DataFrames for each strategy's slippage
    df_model = pd.DataFrame({'timestamp': model_trades['timestamp'], "shares": model_trades['shares'], 'model_slippage': model_slippage, 'model_market_impact': model_market_impact, 'model_spread_cost': model_spread_cost})
    df_twap = pd.DataFrame({'timestamp': twap_trades['timestamp'], "shares": twap_trades['shares'], 'twap_slippage': twap_slippage, 'twap_market_impact': twap_market_impact, 'twap_spread_cost': twap_spread_cost})
    df_vwap = pd.DataFrame({'timestamp': vwap_trades['timestamp'], "shares": vwap_trades['shares'], 'vwap_slippage': vwap_slippage, 'vwap_market_impact': vwap_market_impact, 'vwap_spread_cost': vwap_spread_cost})

      # Merge TWAP and VWAP first
    df_metrics = df_twap.merge(df_vwap, on='timestamp', how='outer')
    
    # Then merge the model data
    df_metrics = df_metrics.merge(df_model, on='timestamp', how='left')
    # Convert the 'timestamp' column to datetime (if necessary)
    df_metrics['timestamp'] = pd.to_datetime(df_metrics['timestamp'])
    df_metrics = df_metrics.fillna(0)
    # Sort the DataFrame by timestamp
    df_metrics = df_metrics.sort_values('timestamp')
    df_metrics.to_csv('metrics_data.csv', index=False)
    return model_trades, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed

# NOT TESTED
def opt_sell_backtest(is_sell, ticker, inventory, day_of_backtest, bt_data, min_bt_data, timeframe=390):
    print("Executing Options Backtest")

    # Run model for trading
    # model_trades = run_options_inference()
    model_trades = []

    # Calculating twap trades
    twap_trades = opt_get_twap_trades(bt_data, inventory, timeframe)

    # Calculating vwap trades
    vwap_trades = opt_get_vwap_trades(bt_data, inventory, timeframe)

    # Calculating model metrics
    model_slippage, model_market_impact, model_spread_cost, model_tc, _, model_IS = opt_simulate_strategy(model_trades, bt_data, timeframe, ticker, is_sell, min_bt_data)
    model_metrics_summed = [sum(model_slippage), sum(model_market_impact), sum(model_spread_cost), sum(model_tc), sum(model_IS)]

    # Calculating twap metrics
    twap_slippage, twap_market_impact, twap_spread_cost, twap_tc, _, twap_IS = opt_simulate_strategy(twap_trades, bt_data, timeframe, ticker, is_sell, min_bt_data)
    twap_metrics_summed = [sum(twap_slippage), sum(twap_market_impact), sum(twap_spread_cost), sum(twap_tc), sum(twap_IS)]

    # Calculating vwap metrics
    vwap_slippage, vwap_market_impact, vwap_spread_cost, vwap_tc, _, vwap_IS = opt_simulate_strategy(vwap_trades, bt_data, timeframe, ticker, is_sell, min_bt_data)
    vwap_metrics_summed = [sum(vwap_slippage), sum(vwap_market_impact), sum(vwap_spread_cost), sum(vwap_tc), sum(vwap_IS)]

    return model_trades, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed

def equity_backtest(ticker, inventory, day_of_backtest, bt_data, min_bt_data, is_sell):
    if (is_sell): # Run sell model
        model_trades, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed = eq_sell_backtest(ticker, inventory, day_of_backtest, bt_data, min_bt_data)
    else: # Run buy model
        model_trades, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed = eq_buy_backtest(ticker, inventory, day_of_backtest, bt_data, min_bt_data)

    return model_trades, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed

# NOT TESTED
def options_backtest(ticker, inventory, day_of_backtest, bt_data, min_bt_data, is_sell):
    if (is_sell): # Run sell model
        model_trades, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed = opt_sell_backtest(ticker, inventory, day_of_backtest, bt_data, min_bt_data)
    else: # Run buy model
        model_trades, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed = opt_buy_backtest(ticker, inventory, day_of_backtest, bt_data, min_bt_data)

    return model_trades, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed

def run_backtest(ticker='AAPL', inventory=1000, day_of_backtest=(datetime.now(pytz.UTC) - timedelta(days=2)).strftime('%Y-%m-%d'),
                 is_equity=True, is_sell=True, record_data=False, plotter=False):
    
    # Load data for metric calculations
    bt_data, min_bt_data = load_backtest_data(ticker, day_of_backtest)

    if (is_equity): # Equity asset type
        print('equity')
        model_trades, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed = equity_backtest(ticker, inventory, day_of_backtest, bt_data, min_bt_data, is_sell)
    else: # Option asset type
        model_trades, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed = options_backtest(ticker, inventory, day_of_backtest, bt_data, min_bt_data, is_sell)

    if (record_data):
        # CSV file that stores all metrics
        filename = 'trading_metrics.csv'
        create_csv_file(filename)
        # Add data to csv file
        append_metric_rows(filename, ticker, day_of_backtest, inventory, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed) 
        if (plotter):
            plot_metrics(filename, is_sell, is_equity=True) # Create and save bar plot of model metrics
            plot_slippage_dist() # Create and save bar plot of slippage data
            plot_slippage_by_interval()
            plot_market_impact_against_shares()
            streamlit_metrics_plot(filename, is_sell, is_equity=True)
    return model_trades, model_metrics_summed, twap_metrics_summed, vwap_metrics_summed

def run_hw_trade_list(csv_file_path):
    user_trades_data = pd.read_csv(csv_file_path)
    
    model_trade_info = []
    # Loop through each row of the DataFrame (each trade the user made)
    for i, row in user_trades_data.iterrows():
        day_of_backtest, ticker, inventory, is_sell, is_equity = row['date'], row['ticker'], row['shares'], row['is_sell'], row['is_equity']
        model_trades, _ = run_backtest(ticker, inventory, day_of_backtest, is_equity, is_sell)

        # Weighted avg price of trades made for this test case (note that price is based on 'closed' price)
        weighted_avg_price = (model_trades['price'] * model_trades['shares']).sum() / model_trades['shares'].sum()
        model_trade_info.append([day_of_backtest, ticker, inventory, is_sell, is_equity, weighted_avg_price])

    columns = ['date', 'ticker', 'inventory', 'is_sell', 'is_equity', 'price'] # Column names
    model_trade_info = pd.DataFrame(model_trade_info, columns=columns) # Convert to pandas DataFrame

    return model_trade_info

def run_blockhouse_list(csv_file_path):
    list_of_backtests = pd.read_csv(csv_file_path)
    
    comparison_info = []
    # Loop through each row of the DataFrame (each trade the user made)
    for i, row in list_of_backtests.iterrows():
        day_of_backtest, ticker, inventory, is_sell, is_equity = row['date'], row['ticker'], row['shares'], row['is_sell'], row['is_equity']
        _,  model_metrics_summed, twap_metrics_summed, vwap_metrics_summed = run_backtest(ticker, inventory, day_of_backtest, is_equity, is_sell)
        comparison_info.append([day_of_backtest, ticker, inventory, is_sell, is_equity, 
                                model_metrics_summed[0], model_metrics_summed[1], model_metrics_summed[2], model_metrics_summed[3],
                                twap_metrics_summed[0], twap_metrics_summed[1], twap_metrics_summed[2], twap_metrics_summed[3],
                                vwap_metrics_summed[0], vwap_metrics_summed[1], vwap_metrics_summed[2], vwap_metrics_summed[3]])

    columns = ['date', 'ticker', 'inventory', 'is_sell', 'is_equity', 
               'model_slippage', 'model_market_impact', 'model_spread_cost', 'model_transaction_cost',
               'twap_slippage', 'twap_market_impact', 'twap_spread_cost', 'twap_transaction_cost',
               'vwap_slippage', 'vwap_market_impact', 'vwap_spread_cost', 'vwap_transaction_cost'] # Column names
    comparison_info = pd.DataFrame(comparison_info, columns=columns) # Convert to pandas DataFrame
    
    return comparison_info

