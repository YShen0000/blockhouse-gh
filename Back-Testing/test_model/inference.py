

import os
import numpy as np
import pandas as pd
import pickle as pkl
from datetime import datetime
import pytz

from test_model.model import RLModel5
from test_model.data_handler import InferenceDataHandler
from test_model.data_process import DataProcessor


class EquityInference:
    def __init__(self, data_dir='Data', model_dir='Models', logging_dir='logs', n_env=1):
        # self.data_dir = 'Data'
        # self.model_dir = 'Models'
        # self.logging_dir = 'logs'
        self.data_dir = data_dir
        self.model_dir = model_dir
        self.logging_dir = logging_dir

        self.news_sentiment_dir = '/Users/anshulrana/Desktop/blockhouse/blockhouseTrialPeriod/Blockhouse/Back-Testing/test_model/news_sentiment_to_merge.csv'
        self.data_dir = '/Users/anshulrana/Desktop/blockhouse/blockhouseTrialPeriod/Blockhouse/Back-Testing/test_model/output.csv'


        # os.makedirs(self.data_dir, exist_ok=True)
        # os.makedirs(self.model_dir, exist_ok=True)
        # os.makedirs(self.logging_dir, exist_ok=True)

        self.n_env = n_env
    
        self.data_handler = DataProcessor(self.data_dir, self.news_sentiment_dir)

        self.data_handler = InferenceDataHandler(data_dir)

        
        # TODO : Need to clarify the data_dir
        self.grModel = RLModel5(model_dir=model_dir,data_dir = data_dir)

    def run_inference(self, ticker, start_date, end_date, timeframe, inventory, action="sell"):

        df = self.data_handler.preprocess()
        processed_data = self.data_handler.process(df)
        print(f"All column data headers: {processed_data.columns.tolist()}")

        # Fetch and process the data, generate forecast
        # processed_data = self.data_handler.get_data(ticker=ticker, start_date=start_date, end_date=end_date, timeframe=timeframe)

        # setting model name fixed for now, if we train more models, we can change it
        # trial = "_env6_trial3_totpen_multi_env_exp_rew_price_sde_false_allinv"
        if action=="sell":
            trial = "_env6_sell"
        else:
            trial = "_env6_buy"
        # model_name = f"AAPL_trial{trial}.pt"
        

        trades = self.grModel.test(processed_data,ticker = ticker ,end_timestamp=end_date,timeframe=timeframe,inventory=10000,bet_sz_model_dir="Models/bet_sizing_v1",backtest=True)
        return trades
