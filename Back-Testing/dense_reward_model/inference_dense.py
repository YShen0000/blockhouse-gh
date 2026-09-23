import os
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import torch
from gym import spaces

import warnings

# from utils.macro_model import MetaLearner
from test_model.data_handler import DataProcessor, InferenceDataHandler
from test_model.macro_model_utils import MacroTraderModel
from test_model import fetch_merge_data
# import dataframe_image as dfi
# import blockhouse_ml.equities.sell.benchmark_utils as benchmarks
from collections import defaultdict

from sklearn import preprocessing
from sklearn.linear_model import LinearRegression
from test_model.data_handler_v2 import process_data, fetch_data
from stable_baselines3 import SAC

def decide_order_type(df, idx, action='sell', future_minutes=25):
# Method implementation as shown above
    # (Copy the decide_order_type method provided earlier)
    # [Include the complete method here]

    # Get the future data
    future_df = df.iloc[idx+1 : idx+1+future_minutes].copy()
    
    if future_df.empty or len(future_df) < 2:
        # Not enough data ahead, default to market order
        return 'market', None
    
    # Calculate mid_prices
    future_df['mid_price'] = (future_df['price'] + future_df['arrival']) / 2
    
    # Fit linear regression
    X = np.arange(len(future_df)).reshape(-1,1)
    y = future_df['mid_price'].values.reshape(-1,1)
    reg = LinearRegression().fit(X, y)
    slope = reg.coef_[0][0]
    
    # Calculate volatility over that interval
    returns = future_df['arrival'].pct_change().dropna()
    if len(returns) < 1:
        return 'market', None
    volatilities = returns.rolling(window=5).std().dropna()
    
    if len(volatilities) < 1:
        return 'market', None
    
    # Compute the 70th percentile of volatility over that interval
    volatility_threshold = np.percentile(volatilities, 70)
    current_volatility = volatilities.iloc[-1]  # use the last calculated volatility
    
    if current_volatility > volatility_threshold:
        # Volatility is high
        if action == 'sell':
            if slope > 0:
                # For selling: if trend is up, set limit order
                order_type = 'limit'
                # Get the second highest mid_price in the interval
                second_highest_mid_price = future_df['mid_price'].nlargest(2).iloc[-1]
                price = second_highest_mid_price
            else:
                # Trend is down
                order_type = 'market'
                price = None
        elif action == 'buy':
            if slope < 0:
                # For buying: if trend is down, set limit order
                order_type = 'limit'
                # Get the second lowest mid_price in the interval
                second_lowest_mid_price = future_df['mid_price'].nsmallest(2).iloc[-1]
                price = second_lowest_mid_price
            else:
                # Trend is up
                order_type = 'market'
                price = None
    else:
        # Volatility is low, execute market order
        order_type = 'market'
        price = None
    
    return order_type, price


def five_level_data(ticker = 'AAPL',start_date='2024-07-01', end_date= '2024-08-16'):
    data_dir = 'Data'
    os.makedirs(data_dir, exist_ok=True)
    # start_date = '2024-07-01'
    # end_date = '2024-08-16'


    data_filepath = fetch_data(ticker=ticker, start_date=start_date, end_date=end_date, data_dir=data_dir)

    data = pd.read_csv(data_filepath)
    data.dropna(inplace=True)
    data.set_index("timestamp", inplace=True)

    train_data = data[:int(len(data) * 0)]
    test_data = data[int(len(data) * 0.8):]

    processor_filename = f"{ticker}_{start_date}_{end_date}"
    processed_train_data = process_data(train_data, name=ticker, cols=data.columns, train=True)
    processed_test_data = process_data(test_data, name=ticker, cols=data.columns, train=False)
    processed_train_data.to_csv("five_level_data_csv.csv")
    processed_test_data.to_csv("five_level_data_test_csv.csv")

    processed_train_data.describe()
    print(len(processed_train_data))
    print(len(processed_test_data))
    return processed_train_data, processed_test_data


# def create_bar_graph

def get_data(data_dir, ticker, start_time, end_time):
    data_processor = DataProcessor()
    # Define the forecast steps
    forecast_steps = {
        'open': (360, '1T'),
        'high': (360, '1T'),
        'low': (360, '1T'),
        'close': (360, '1T'),
        'volatility': (360, '1T'),
        'volume': (360, '1T'),
        'transaction_cost': (360, '1T')
    }

    ## Fetch and process the data and save it to the data directory, if it doesn't exist
    filename = f'{data_dir}/merged_data_{ticker}_{start_time}_{end_time}.csv'
    if os.path.exists(filename):
        data = pd.read_csv(filename)
    else:
        data = fetch_merge_data.fetch_and_merge_data(ticker, start_date=start_time, end_date=end_time,
                                                     save_dir=data_dir)

    processed_filename = f'{data_dir}/processed_data_{ticker}_{start_time}_{end_time}.csv'

    if os.path.exists(processed_filename):
        processed_data = pd.read_csv(processed_filename)
    else:
        processed_data = data_processor.process_data(data, forecast_steps, n_jobs=4)
        processed_data.to_csv(processed_filename)

    return processed_data

def run_benchmark_function(our_trades, test_data, timeframe, tenv):
    slippage, oppotunuty, tc, spread_cost, vwap_rew, IS_vwap_per_ticker, count_missing_data = benchmarks.simulate_strategy(
        our_trades,
        data=test_data,
        preferred_timeframe=timeframe,
        env=tenv)
    results_our[ticker] = (slippage, oppotunuty, tc, spread_cost)
    print(results_our)
    IS_ours[ticker] = IS_vwap_per_ticker
    print("slippage on our: ", sum(slippage))
    print("oppotunuty on our: ", sum(oppotunuty))
    print("spread_cost on our: ", sum(spread_cost))
    print("IS on our: ", IS_vwap_per_ticker.mean())
    print("missing data on our: ", len(count_missing_data) - sum(count_missing_data))
    print(len(count_missing_data))
    # print("------------------------")

def classify_market_cap(market_cap_value):
    if market_cap_value < 2e9:
        return "small"
    elif market_cap_value < 10e9:
        return "medium"
    else:
        return "large"

def classify_scenario(inventory):
    if inventory < 100:
        return "small"
    elif inventory < 1000:
        return "medium"
    else:
        return "large"

if __name__ == '__main__':
    # Initialize the model directory, where the models will be saved
    MODEL_DIR = 'Models'
    MODEL_DIR = 'Models_dynamic_benchmark'
    MODEL_DIR = 'Models'

    os.makedirs(MODEL_DIR, exist_ok=True)

    # Initialize the data directory, where the data will be stored
    data_dir = 'Data'
    os.makedirs(data_dir, exist_ok=True)

    # Initialize the MetaLearner
    # meta = MetaLearner()

    # Initialize the MacroTraderModel
    macro_trader = MacroTraderModel(MODEL_DIR)

    # Initialize the data processor

    state_cols =  ['open', 'high', 'low', 'close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist',
                              'Stoch_k', 'Stoch_d', 'OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 'ATR_1', 'ADX',
                              '+DI', '-DI', 'CCI', 'ATR_2', 'ATR_5', 'ATR_10', 'ATR_20', 'ADX', '+DI', '-DI',
                              'CCI', 'DLR', 'transaction_cost', 'forecast_6Hr_open', 'market_liquidity',
                              'expected_price',
                              'log_return', 'volatility', 'mid_price', 'mean_vol', 'mean_liq',
                              '5_min_volatility', '5_min_volume', '5_min_TC', 'forecast_6Hr_close',
                              'forecast_6Hr_high', 'forecast_6Hr_low', 'forecast_6Hr_volatility',
                              'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost', "bid_price", "ask_price"]
    # Inference data handler
    inference_data_handler = InferenceDataHandler()

    # Define the start and end dates
    # start_time = '2024-09-09'
    # end_time = '2024-09-09'
    start_time = '2024-07-01'
    end_time = '2024-08-16'

    # List of Companies based on Market Capitalization
    large_cap_companies = ['AAPL', 'CSCO', 'MCD', 'IBM', 'AMZN', 'TSLA', 'PFE', 'MS', 'MSFT', 'NVDA']
    large_cap_companies = ['AAPL', 'CSCO', 'MCD', 'IBM', 'AMZN', 'TSLA', 'PFE', 'MS', 'MSFT', 'NVDA']

    large_cap_companies = ['AAPL']
    # large_cap_companies = ['ACMR']


    # large_cap_companies = ['AAPL', 'CSCO', 'MCD', 'IBM', 'AMZN', 'TSLA']

    mid_cap_companies = []  #['AEG', 'NICE', 'NLY', 'ONTO', 'PSN', 'SAIA', 'OWL','PNW','TWLO','HAS']
    small_cap_companies = []  #['NVAX','AMC','WOLF','IREN','SEDG', 'UPWK','SERV','FSLY','BMBL','ARRY']

    training_params = {'callback': None, 'total_timesteps': 45000}

    training_config_tab = {'learning_rate': 0.00006, 'n_steps': 8, 'batch_size': 32,
                           'gamma': 0.9999, 'clip_range': 0.359147, 'n_epochs': 6, 'ent_coef': 0.000183877,
                           'verbose': 1}

    training_config_tab = {'learning_rate': 0.00001, 'n_steps': 1024, 'batch_size': 32, 'gamma': 0.9900,
                           'clip_range': 0.2, 'n_epochs': 16, 'ent_coef': 0.7, "use_sde": True, 'verbose': 1}

    training_config_tab = {'learning_rate': 0.000001, 'n_steps': 1024, 'batch_size': 64, 'gamma': 0.965901,
                           'clip_range':0.03 , 'n_epochs': 8, 'ent_coef': 0.3 , "use_sde": True, 'verbose': 1}




    results_twap = defaultdict()  # Dictionary to store results from TWAP, VWAP and OUR model
    results_our = defaultdict()
    results_vwap = defaultdict()
    results_tab = defaultdict()

    IS_twaps = defaultdict()  # Dictionary to store IS from TWAP model for each ticker
    IS_ours = defaultdict()
    IS_vwaps = defaultdict()
    IS_ourstab = defaultdict()

    # Load the trained model
    MODEL_DIR = 'test_model'
    model_path = os.path.join(MODEL_DIR, 'dense_reward_model.zip')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    trained_model = SAC.load(model_path)
    print(f"Loaded model from: {model_path}")

    for companies in [large_cap_companies]:  #, mid_cap_companies, small_cap_companies]:
        for ticker in companies:
            processed_data = get_data(data_dir, ticker, start_time, end_time)
            # Only need test data for testing
            train_data_raw = processed_data[:int(len(processed_data) * 0.8)]
            test_data_raw = processed_data[int(len(processed_data) * 0.8):]
            test_data_raw['ticker'] = [ticker] * len(test_data_raw)
            train_data_raw['ticker'] = [ticker] * len(train_data_raw)

            train_data_raw = train_data_raw.loc[train_data_raw['bid_price'] > 0]
            test_data_raw = test_data_raw.loc[test_data_raw['bid_price'] > 0]

            train_data_raw = train_data_raw.loc[train_data_raw['ask_size'] > 0]
            test_data_raw = test_data_raw.loc[test_data_raw['ask_size'] > 0]

            train_data_raw = train_data_raw.loc[train_data_raw['bid_size'] > 0]
            test_data_raw = test_data_raw.loc[test_data_raw['bid_size'] > 0]

            print(train_data_raw.isna().sum())
            print(test_data_raw.isna().sum())

            train_data = train_data_raw.copy()
            test_data = test_data_raw.copy()

            # scaler = preprocessing.StandardScaler().fit(train_data_raw[state_cols])
            # train_data[state_cols] = scaler.transform(train_data_raw[state_cols])
            # test_data[state_cols] = scaler.transform(test_data_raw[state_cols])

            train_data.to_csv('processed_train_data.csv')
            test_data.to_csv('processed_test_data.csv')

            test_data['ticker'] = [ticker] * len(test_data)
            train_data['ticker'] = [ticker] * len(train_data)

            print("Testing Model for ", ticker)
            market_cap_int = fetch_merge_data.get_market_cap(ticker)
            market_cap = classify_market_cap(market_cap_int)
            timeframe = 390
            inventory = 10000
            # for transaction_size in [9, 99, 499, 1999, 10000]:
            scenario = classify_scenario(inventory)
            # print("Training Model for ticker: {} Transaction Size: {} Market Cap: {}".format(ticker, scenerio,
            # market_cap)) training_params['tb_log_name'] =f'{log_dir}/{ticker}_{scenerio}_{market_cap}'
            print("------------------------")
            print("Testing on ", ticker)
            print(scenario)

            processed_train_data, processed_test_data = five_level_data(ticker,start_time,end_time)

            # Remove the training step
            # modeltab, env_ = macro_trader.train(...)

            print("------------------------")
            print("Testing on ", ticker)
            print(scenario)

            # Use the loaded model for inference
            rew, tenv, model, infos = macro_trader.test_benchmark(
                test_data, 
                test_data_raw, 
                processed_test_data,
                preferred_timeframe=timeframe,
                market_cap=market_cap,
                scenario=scenario, 
                get_tab_transformer=False,
                model=trained_model  # Use the loaded model here
            )

            for info in infos:
                print(info)

            out = pd.DataFrame(infos)
            out.to_csv('trading_result_1_3.csv')
            print("agent slippage on  ", out['IS'].sum())

            rew, tenv, model, infos = macro_trader.test_benchmark_twap(test_data[:500], test_data_raw[:500], processed_test_data[:500],
                                                           preferred_timeframe=timeframe,
                                                           market_cap=market_cap,
                                                           scenario=scenario, get_tab_transformer=True)
            out = pd.DataFrame(infos)
            print("twap slippage on  ", out['IS_twap'].sum())


            rew, tenv, model, infos = macro_trader.test_benchmark(test_data[500:1000], test_data_raw[500:1000], processed_test_data[500:1000],
                                                           preferred_timeframe=timeframe,
                                                           market_cap=market_cap,
                                                           scenario=scenario, get_tab_transformer=True)
            out = pd.DataFrame(tenv.trades)
            for info in infos:
                print(info)
            out = pd.DataFrame(infos)
            out.to_csv('trading_result_2_3.csv')
            print("agent slippage on  ", out['IS'].sum())

            rew, tenv, model, infos = macro_trader.test_benchmark_twap(test_data[500:1000], test_data_raw[500:1000], processed_test_data[500:1000],
                                                           preferred_timeframe=timeframe,
                                                           market_cap=market_cap,
                                                           scenario=scenario, get_tab_transformer=True)
            out = pd.DataFrame(infos)
            print("twap slippage on  ", out['IS_twap'].sum())



            rew, tenv, model, infos = macro_trader.test_benchmark(test_data[1000:1500], test_data_raw[1000:1500], processed_test_data[1000:1500],
                                                           preferred_timeframe=timeframe,
                                                           market_cap=market_cap,
                                                           scenario=scenario, get_tab_transformer=True)
            out = pd.DataFrame(tenv.trades)
            for info in infos:
                print(info)
            out = pd.DataFrame(infos)
            out.to_csv('trading_result_3_3.csv')

            # out = pd.DataFrame(tenv.trades)
            print("agent slippage on  ", out['IS'].sum())


            rew, tenv, model, infos = macro_trader.test_benchmark_twap(test_data[1000:1500], test_data_raw[1000:1500], processed_test_data[1000:1500],
                                                           preferred_timeframe=timeframe,
                                                           market_cap=market_cap,
                                                           scenario=scenario, get_tab_transformer=True)
            out = pd.DataFrame(infos)
            print("twap slippage on  ", out['IS_twap'].sum())





