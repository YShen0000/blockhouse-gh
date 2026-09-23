import os
import time
from datetime import datetime, timedelta
from peft import get_peft_config, get_peft_model, LoraConfig, TaskType
import pandas as pd
import numpy as np
from statsmodels.tsa.api import ARIMA, ExponentialSmoothing
import torch
from gym import spaces

import warnings

from utils.macro_model import MetaLearner
from utils.data_handler import DataProcessor, InferenceDataHandler
from utils.macro_model_utils import MacroTraderModel
from utils import fetch_merge_data
import dataframe_image as dfi
from utils.env import TradingEnvironment, CustomTradingEnvironment
import utils.benchmark_utils as benchmarks
from collections import defaultdict

from sklearn import preprocessing

from data_handler_v2 import process_data, fetch_data


def five_level_data(ticker = 'AAPL'):
    data_dir = 'Data'
    os.makedirs(data_dir, exist_ok=True)
    start_date = '2024-07-01'
    end_date = '2024-08-17'


    data_filepath = fetch_data(ticker=ticker, start_date=start_date, end_date=end_date, data_dir=data_dir)

    data = pd.read_csv(data_filepath)
    data.dropna(inplace=True)
    data.set_index("timestamp", inplace=True)

    train_data = data[:int(len(data) * 0.8)]
    test_data = data[int(len(data) * 0.8):]

    processor_filename = f"{ticker}_{start_date}_{end_date}"
    processed_train_data = process_data(train_data, name=ticker, cols=data.columns, train=True)
    processed_test_data = process_data(test_data, name=ticker, cols=data.columns, train=False)
    processed_train_data.to_csv("five_level_data_csv.csv")
    processed_test_data.to_csv("five_level_data_test_csv.csv")

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

    processed_filename = f'{data_dir}/processed_data_v2_{ticker}_{start_time}_{end_time}.csv'

    if os.path.exists(processed_filename):
        processed_data = pd.read_csv(processed_filename)
    else:
        processed_data = data_processor.process_data(data, forecast_steps, n_jobs=4)
        processed_data.to_csv(processed_filename)

    cleaned_columns = [col for col in processed_data.columns if
                       col.endswith('_x') or ('_x' not in col and '_y' not in col)]

    # Create a new DataFrame with the selected columns
    cleaned_df = processed_data[cleaned_columns].copy()

    # Optionally, remove the '_x' suffix from the column names
    cleaned_df.columns = [col.replace('_x', '') for col in cleaned_df.columns]

    data = cleaned_df["trade_sign"].copy()
    cleaned_df.drop(columns=['trade_sign'], inplace=True)
    cleaned_df['trade_sign'] = data.values[:, 0]
    print(cleaned_df.columns)

    return cleaned_df


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
    meta = MetaLearner()

    # Initialize the MacroTraderModel
    macro_trader = MacroTraderModel(MODEL_DIR)

    # Initialize the data processor

    state_cols =  ['open', 'high', 'low', 'close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist',
                              'Stoch_k', 'Stoch_d', 'OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 'ATR_1', 'ADX',
                              '+DI', '-DI', 'CCI', 'ATR_2', 'ATR_5', 'ATR_10', 'ATR_20', 'ADX', '+DI', '-DI',
                              'CCI', 'DLR', 'transaction_cost', 'forecast_6Hr_open', 'market_liquidity',
                              'expected_price', 'Rolling Volatility', 'cusum_feature', 'SADF Feature', 'corwin_schultz_spread', 'trade_sign', 'fib_level_0.236',
       'fib_level_0.382', 'fib_level_0.5', 'fib_level_0.618',
       'fib_level_0.786', 'cum_volume', 'bar_index',
                              'log_return', 'volatility', 'mid_price', 'mean_vol', 'mean_liq',
                              '5_min_volatility', '5_min_volume', '5_min_TC', 'forecast_6Hr_close',
                              'forecast_6Hr_high', 'forecast_6Hr_low', 'forecast_6Hr_volatility',
                              'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost', "bid_price", "ask_price"]
    # Inference data handler
    inference_data_handler = InferenceDataHandler()

    # Define the start and end dates
    start_time = '2024-07-01'
    end_time = '2024-08-16'

    # List of Companies based on Market Capitalization
    large_cap_companies = ['AAPL', 'CSCO', 'MCD', 'IBM', 'AMZN', 'TSLA', 'PFE', 'MS', 'MSFT', 'NVDA']
    large_cap_companies = ['AAPL', 'CSCO', 'MCD', 'IBM', 'AMZN', 'TSLA', 'PFE', 'MS', 'MSFT', 'NVDA']

    # large_cap_companies = ['AAPL']
    large_cap_companies = ['MCD']


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

    for companies in [large_cap_companies]:  #, mid_cap_companies, small_cap_companies]:
        for ticker in companies:
            processed_data = get_data(data_dir, ticker, start_time, end_time)

            # Only need test data for testing
            train_data_raw = processed_data[:int(len(processed_data) * 0.8)]
            test_data_raw = processed_data[int(len(processed_data) * 0.8):]
            print(processed_data.columns)

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

            scaler = preprocessing.StandardScaler().fit(train_data_raw[state_cols])
            train_data[state_cols] = scaler.transform(train_data_raw[state_cols])
            test_data[state_cols] = scaler.transform(test_data_raw[state_cols])

            train_data.to_csv('processed_train_data.csv')
            test_data.to_csv('processed_test_data.csv')

            test_data['ticker'] = [ticker] * len(test_data)
            train_data['ticker'] = [ticker] * len(train_data)

            print("Testing Model for ", ticker)
            market_cap_int = fetch_merge_data.get_market_cap(ticker)
            market_cap = meta.classify_market_cap(market_cap_int)
            timeframe = 390
            time_jump_resolution = 30
            inventory = 7000
            # for transaction_size in [9, 99, 499, 1999, 10000]:
            scenario = meta.classify_scenario(inventory)
            # print("Training Model for ticker: {} Transaction Size: {} Market Cap: {}".format(ticker, scenerio,
            # market_cap)) training_params['tb_log_name'] =f'{log_dir}/{ticker}_{scenerio}_{market_cap}'

            processed_train_data, processed_test_data = five_level_data(ticker)

            print("------------------------")
            print("Testing on ", ticker)
            print(scenario)
            stacked_env = True

            modeltab, env_ = macro_trader.train(train_data, train_data_raw, processed_train_data, preferred_timeframe=timeframe,
                                                market_cap=market_cap,
                                                scenario=scenario, get_tab_transformer=True, resume=False,
                                                training_params=training_params,
                                                training_config=training_config_tab, use_stacked_env = stacked_env)
            # # out = pd.DataFrame(tenv_test.trades)
            # print("slippage on  ", out['slippage'].sum())

            print("------------------------")
            print("Testing on ", ticker)
            print(scenario)

            rew, tenv, model, infos = macro_trader.test_benchmark(test_data[:500], test_data_raw[:500], processed_test_data[:500],
                                                           preferred_timeframe=timeframe,
                                                           market_cap=market_cap,
                                                           scenario=scenario, get_tab_transformer=True, use_stacked_env = stacked_env)

            for info in infos:
                if "terminal_observation" in info.keys():
                    info.pop("terminal_observation")
                print(info)

            out = pd.DataFrame(infos)
            our_trades = out
            # our_trades = pd.DataFrame(tenv.trades)
            #
            if stacked_env:
                tenv  = tenv.venv.envs[0]

            out.to_csv('trading_result_1_3.csv')
            tenv.reset()
            slippage, oppotunuty, tc, spread_cost, vwap_rew, IS_vwap_per_ticker, count_missing_data = benchmarks.simulate_strategy(
                our_trades,
                data=test_data_raw[:500],
                preferred_timeframe=timeframe,
                env=tenv)
            results_our[ticker] = (slippage, oppotunuty, tc, spread_cost)
            IS_ours[ticker] = IS_vwap_per_ticker
            print("slippage on our: ", sum(slippage))
            print("oppotunuty on our: ", sum(oppotunuty))
            print("spread_cost on our: ", sum(spread_cost))
            print("IS on our: ", IS_vwap_per_ticker.mean())
            print("missing data on our: ", len(count_missing_data) - sum(count_missing_data))
            print(len(count_missing_data))


            rew, tenv, model, infos = macro_trader.test_benchmark(test_data[500:1000], test_data_raw[500:1000], processed_test_data[500:1000],
                                                           preferred_timeframe=timeframe,
                                                           market_cap=market_cap,
                                                           scenario=scenario, get_tab_transformer=True, use_stacked_env = stacked_env)
            # out = pd.DataFrame(tenv.trades)
            for info in infos:
                if "terminal_observation" in info.keys():
                    info.pop("terminal_observation")
                print(info)

            out = pd.DataFrame(infos)
            our_trades = out

            if stacked_env:
                tenv  = tenv.venv.envs[0]

            tenv.reset()
            slippage, oppotunuty, tc, spread_cost, vwap_rew, IS_vwap_per_ticker, count_missing_data = benchmarks.simulate_strategy(
                our_trades,
                data=test_data_raw[500:1000],
                preferred_timeframe=timeframe,
                env=tenv)
            results_our[ticker] = (slippage, oppotunuty, tc, spread_cost)
            IS_ours[ticker] = IS_vwap_per_ticker
            print("slippage on our: ", sum(slippage))
            print("oppotunuty on our: ", sum(oppotunuty))
            print("spread_cost on our: ", sum(spread_cost))
            print("IS on our: ", IS_vwap_per_ticker.mean())
            print("missing data on our: ", len(count_missing_data) - sum(count_missing_data))
            print(len(count_missing_data))





            vwap_trades = benchmarks.get_vwap_trades(test_data_raw, inventory, timeframe, time_jump_resolution = time_jump_resolution)
            vwap_trades.to_csv("vwap_trades.csv")
            tenv.reset()
            slippage, oppotunuty, tc, spread_cost, vwap_rew, IS_vwap_per_ticker, count_missing_data = benchmarks.simulate_strategy(
                vwap_trades,
                data=test_data_raw,
                preferred_timeframe=timeframe, env=tenv)
            results_vwap[ticker] = (slippage, oppotunuty, tc, spread_cost)
            IS_vwaps[ticker] = IS_vwap_per_ticker
            print("slippage on VWAP: ", sum(slippage))
            print("oppotunuty on VWAP: ", sum(oppotunuty))
            print("spread_cost on VWAP: ", sum(spread_cost))
            print("IS on VWAP: ", IS_vwap_per_ticker.mean())
            print("missing data on VWAP: ", len(count_missing_data) - sum(count_missing_data))
            print(len(count_missing_data))
            print("------------------------")


            print("Testing on TWAP | ", end="")
            tenv.reset()
            twap_trades = benchmarks.get_twap_trades(test_data_raw, inventory, timeframe, time_jump_resolution = time_jump_resolution)
            slippage, oppotunuty, tc, spread_cost, twap_rew, IS_twap_per_ticker, count_missing_data = benchmarks.simulate_strategy(
                twap_trades,
                data=test_data_raw,
                preferred_timeframe=timeframe, env=tenv)
            twap_trades.to_csv("twap_trades.csv")

            results_twap[ticker] = (slippage, oppotunuty, tc, spread_cost)
            IS_twaps[ticker] = IS_twap_per_ticker
            print("slippage on TWAP: ", sum(slippage))
            print("oppotunuty on TWAP: ", sum(oppotunuty))
            print("spread_cost on TWAP: ", sum(spread_cost))
            print("IS on TWAP: ", IS_twap_per_ticker.mean())
            print("missing data on TWAP: ", len(count_missing_data) - sum(count_missing_data))
            print(len(count_missing_data))



            vwap_trades = benchmarks.get_vwap_trades(test_data_raw[500:1000], inventory, timeframe, time_jump_resolution = time_jump_resolution)
            vwap_trades.to_csv("vwap_trades.csv")
            tenv.reset()
            slippage, oppotunuty, tc, spread_cost, vwap_rew, IS_vwap_per_ticker, count_missing_data = benchmarks.simulate_strategy(
                vwap_trades,
                data=test_data_raw[500:1000],
                preferred_timeframe=timeframe, env=tenv)
            results_vwap[ticker] = (slippage, oppotunuty, tc, spread_cost)
            IS_vwaps[ticker] = IS_vwap_per_ticker
            print("slippage on VWAP: ", sum(slippage))
            print("oppotunuty on VWAP: ", sum(oppotunuty))
            print("spread_cost on VWAP: ", sum(spread_cost))
            print("IS on VWAP: ", IS_vwap_per_ticker.mean())
            print("missing data on VWAP: ", len(count_missing_data) - sum(count_missing_data))
            print(len(count_missing_data))
            print("------------------------")


            print("Testing on TWAP | ", end="")
            tenv.reset()
            twap_trades = benchmarks.get_twap_trades(test_data_raw[500:1000], inventory, timeframe, time_jump_resolution = time_jump_resolution)
            slippage, oppotunuty, tc, spread_cost, twap_rew, IS_twap_per_ticker, count_missing_data = benchmarks.simulate_strategy(
                twap_trades,
                data=test_data_raw[500:1000],
                preferred_timeframe=timeframe, env=tenv)
            twap_trades.to_csv("twap_trades.csv")

            results_twap[ticker] = (slippage, oppotunuty, tc, spread_cost)
            IS_twaps[ticker] = IS_twap_per_ticker
            print("slippage on TWAP: ", sum(slippage))
            print("oppotunuty on TWAP: ", sum(oppotunuty))
            print("spread_cost on TWAP: ", sum(spread_cost))
            print("IS on TWAP: ", IS_twap_per_ticker.mean())
            print("missing data on TWAP: ", len(count_missing_data) - sum(count_missing_data))
            print(len(count_missing_data))

