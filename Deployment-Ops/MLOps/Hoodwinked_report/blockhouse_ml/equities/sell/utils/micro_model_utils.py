"""
Additional model function for testing, saving models.
"""
import os
import pandas as pd
import numpy as np

import torch
from stable_baselines3 import PPO
from gym import spaces
from ray import tune

from blockhouse_ml.equities.sell.utils.macro_model import PPO_MODEL_BEST_PARAMS, MetaLearner
from blockhouse_ml.equities.sell.utils.micro_model import CustomTransformerPolicy
from blockhouse_ml.equities.sell.utils.env import TradingEnvironmentMicro


class MicroTraderModel:
    """
    This class is responsible for training, saving, and loading models for Micro Trader. 
    """

    def __init__(self, model_dir = 'Models'):
        """
        Initializes the Model class.
        """
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
    

        
    def load_model(self, env, policy_kwargs):
        """
        Loads a PPO model with a custom transformer policy.
        
        Args:
        - env (gym.Env): The trading environment for the model.
        - filepath (str): The file path to the saved model parameters.
        - policy_kwargs (dict): Additional keyword arguments for configuring the policy.
        - best_hyperparameters (dict): The best hyperparameters used for training the PPO model.

        Returns:
        - model (PPO): The loaded PPO model configured with the given environment and hyperparameters.
        """

        # Define the best hyperparameters
        best_hyperparameters = {'learning_rate': 0.0009931989008886031, 'n_steps': 512, 'batch_size': 128, 
                                'gamma': 0.9916829193042708, 'clip_range': 0.21127653449387027, 'n_epochs': 6, 'ent_coef': 0.1}
        
        model = PPO(CustomTransformerPolicy, env, verbose=1,   policy_kwargs=policy_kwargs, **best_hyperparameters)
        
        filepath = os.path.join(self.model_dir,'trading_agent')
        
        if os.path.exists(filepath):
            model.load(filepath)
            # print(f"Model loaded from {filepath}")

        return model

