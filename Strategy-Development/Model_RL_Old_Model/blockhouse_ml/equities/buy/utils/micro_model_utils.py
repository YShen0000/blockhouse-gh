import os
import pandas as pd
import numpy as np
from stable_baselines3 import PPO
from gym import spaces
from blockhouse_ml.equities.buy.utils.macro_model import MetaLearner
from blockhouse_ml.equities.buy.utils.micro_model import *
from blockhouse_ml.equities.buy.utils.env import TradingEnvironmentMicro
import sys

class MicroTraderModel:
    """
    This class is responsible for training, saving, and loading models for Micro Trader. 
    """

    def __init__(self, model_dir='MicroBuyEquityModels'):
        """
        Initializes the Model class and sets up model directory.

        Args:
        - model_dir (str): Directory path where models will be saved.
        """
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

    def load_model(self, env, policy_kwargs, market_cap):
        """
        Loads a PPO model with a custom transformer policy, or initializes it if not found.
        
        Args:
        - env (gym.Env): The trading environment for the model.
        - policy_kwargs (dict): Additional keyword arguments for configuring the policy.
        
        Returns:
        - model (PPO): The loaded or initialized PPO model configured with the given environment and hyperparameters.
        """
        # Define the best hyperparameters
        best_hyperparameters = {
            'learning_rate': 0.0009931989008886031, 
            'n_steps': 512, 
            'batch_size': 128, 
            'gamma': 0.9916829193042708, 
            'clip_range': 0.21127653449387027, 
            'n_epochs': 6, 
            'ent_coef': 0.1
        }
        
        print(sys.path)


        # Initialize PPO model
        model = PPO(TabTransformerPolicy, env, verbose=1, policy_kwargs=policy_kwargs, **best_hyperparameters)

        # Define the model filepath
        filepath = os.path.join(self.model_dir, 'trading_agent_v2.zip')
        # model_path = "./Models/trading_agent_v2.zip"

        # Check if the model exists
        if os.path.exists(filepath):
            print("Model found!")
        else:
            print("Model not found. Please check the path.")
        # Load model if already saved
        
        if os.path.exists(filepath):

            custom_objects={"observation_space": env.observation_space, "action_space": env.action_space, "policy_class": TabTransformerPolicy}
            model = PPO.load(filepath, env=env, custom_objects = custom_objects)
            # model.set_parameters(model_path)
            print(f"Model loaded from the new directory {filepath}")
        else:
            current_directory = os.getcwd()
            print(f"CurrentDirectory{current_directory}")
            print(f"No saved model found. Initializing a new PPO model{filepath}.")

        return model

    def train_model(self, env, policy_kwargs, total_timesteps=200000, model_save_path="trading_agent"):
        """
        Trains the PPO model on the provided environment and saves it.
        
        Args:
        - env (gym.Env): The trading environment.
        - policy_kwargs (dict): Additional keyword arguments for configuring the policy.
        - total_timesteps (int): The total number of timesteps to train the model for.
        - model_save_path (str): Path where the trained model should be saved (default: "trading_agent").
        
        Returns:
        - model (PPO): The trained PPO model.
        """
        # Define the best hyperparameters
        best_hyperparameters = {
            'learning_rate': 0.0009931989008886031, 
            'n_steps': 512, 
            'batch_size': 128, 
            'gamma': 0.9916829193042708, 
            'clip_range': 0.21127653449387027, 
            'n_epochs': 6, 
            'ent_coef': 0.1
        }

        # Initialize PPO model
        model = PPO(TabTransformerPolicy, env, verbose=1, policy_kwargs=policy_kwargs, **best_hyperparameters)

        # Train the model
        model.learn(total_timesteps=total_timesteps)

        # Save the model
        model_save_path = os.path.join(self.model_dir, model_save_path)
        model.save(model_save_path)
        print(f"Model saved at {model_save_path}")

        return model

    def test_model(self, env, model_filepath):
        """
        Tests the trained model on the provided environment by loading it and evaluating performance.
        
        Args:
        - env (gym.Env): The environment for testing the model.
        - model_filepath (str): Path to the saved model file.

        Returns:
        - None
        """
        # Load model
        model = PPO.load(model_filepath, env=env)
        obs = env.reset()

        # Test for a few steps
        for i in range(10000):  # Or any other number of steps you want to test
            action, _states = model.predict(obs)
            # print(f"Observations at step {self.current_step}: {self._last_obs}")

            obs, rewards, dones, info = env.step(action)

            if dones:
                print("Episode finished.")
                obs = env.reset()

        print(f"Model tested from {model_filepath}")

