

import os
import numpy as np
import pandas as pd
import pickle as pkl
from datetime import datetime
import pytz

from test_model.model import Model
from test_model.data_handler import InferenceDataHandler


class EquityInference:
    def __init__(self, data_dir='Data', model_dir='Models', logging_dir='logs', n_env=1):
        # self.data_dir = 'Data'
        # self.model_dir = 'Models'
        # self.logging_dir = 'logs'
        self.data_dir = data_dir
        self.model_dir = model_dir
        self.logging_dir = logging_dir

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.logging_dir, exist_ok=True)

        self.n_env = n_env
    
        self.data_handler = InferenceDataHandler(data_dir)

        
        self.sac_model = Model(model_dir=model_dir, logging_dir=logging_dir, n_env=n_env)

    def run_inference(self, ticker, start_date, end_date, timeframe, inventory, action="sell", model_name="first.pt"):
        # Fetch and process the data, generate forecast
        processed_data = self.data_handler.get_data(ticker=ticker, start_date=start_date, end_date=end_date, timeframe=timeframe)

        # Environment parameters
        env_params = {}
        env_params["preferred_timeframe"] = timeframe
        env_params["inventory"]=inventory
        env_params["inference"] = True
        env_params["action"] = action

        # setting model name fixed for now, if we train more models, we can change it
        # trial = "_env6_trial3_totpen_multi_env_exp_rew_price_sde_false_allinv"
        if action=="sell":
            trial = "_env6_sell"
        else:
            trial = "_env6_buy"
        model_name = f"AAPL_trial{trial}.pt"

        rew, trades = self.sac_model.test(processed_data, model=None, model_name=model_name, env_params=env_params)

        return trades