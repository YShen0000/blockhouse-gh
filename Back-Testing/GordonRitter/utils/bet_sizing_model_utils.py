"""
Additional model function for testing, saving models.
"""
import os
import pandas as pd

import torch
from stable_baselines3 import PPO

from GordonRitter.utils.bet_sizing_env import TradingEnvironment

PPO_MODEL_BEST_PARAMS = {'learning_rate': 0.0009931989008886031, 'n_steps': 512, 'batch_size': 128, 
                        'gamma': 0.9916829193042708, 'clip_range': 0.21127653449387027, 'n_epochs': 6, 'ent_coef': 0.1, 'verbose': 0}


class BetSizingModel:
    """
    This class is responsible for training, saving, and loading models for different trading scenarios. 
    Each method in the class loads a model configured with specific hyperparameters and action spaces 
    based on the trading scenario (small, small-medium, medium, medium-large, large).
    """

    def __init__(self, name, env,
                 training_config=PPO_MODEL_BEST_PARAMS,
                 model_dir='Models',
                 overide=False):
        """
        Initializes the Model class.
        """
        self.model_dir = model_dir
        self.model_path = os.path.join(model_dir, name) + '.zip'
        self.model = PPO("MlpPolicy", env, **training_config)
        if not overide and os.path.exists(self.model_path):
            # Load the model
            filepath = self.model_path
            self.model.load(filepath)
            print(f"Model loaded from {filepath}")
        else:
            os.makedirs(model_dir, exist_ok=True)
            print(f"Training from scratch...")

    def train(self, timesteps):

        # Train the model
        self.model.learn(total_timesteps=timesteps)
        
        # Save the model
        self.model.save(self.model_path)

    def test(self, env):
        
        with torch.no_grad():
            obs = env.reset()
            cum_reward = 0
            cycle_complete = False
            while not cycle_complete:
                action, _ = self.model.predict(obs)
                obs, rewards, done, cycle = env.step(action)
                cycle_complete = cycle['cycle']
                cum_reward += rewards
                if done:
                    env.reset()

    def infer(self, env, steps):
        
        with torch.no_grad():
            obs = env.reset()
            cum_reward = 0
            while env.current_step + 1 < steps:
                action, _ = self.model.predict(obs)
                obs, rewards, done, _ = env.step(action)
                cum_reward += rewards
                if done:
                    env.reset()
        return cum_reward/steps