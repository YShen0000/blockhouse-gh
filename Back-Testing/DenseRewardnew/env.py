import gym
from gym import spaces
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

class TradingEnvironment(gym.Env):
    
    def __init__(self, data, max_shares):
        super(TradingEnvironment, self).__init__()
        
        self.data = data  # The pandas DataFrame containing price and other market information
        self.max_shares = max_shares
        self.current_step = 0
        self.total_shares_traded = 0
        self.execution_prices = []  # Store execution prices

        self.action_space = spaces.Discrete(max_shares + 1)  # Number of shares from 0 to max_shares
        self.observation_space = spaces.Box(low=0, high=np.inf, shape=(len(self.data.columns),), dtype=np.float32) # Market info from row of data
        
        self.initial_price = self.data['price'].iloc[0]  # Intial trading price, also assuming the 'price' column exists in the data
        self.T = len(data)  # Total number of time steps based on the length of the data

    def reset(self):
        self.current_step = 0
        self.total_shares_traded = 0
        self.execution_prices = []
        self.initial_price = self.data['price'].iloc[0]  # Reset initial price at t=0
        return self.data.iloc[self.current_step].values  # Return initial observation from the data

    def step(self, action):
        # Execute trade 
        self._execute_trade(action)
        
        # Check if the episode is at the final time step
        if (self.current_step == (self.T - 1)):
            reward = self._calculate_reward()
            self.done = True
        else:
            reward = 0
            self.done = False
        
        # Move to the next step and return the next observation
        self.current_step += 1
        next_observation = self.data.iloc[self.current_step].values
        
        return next_observation, reward, self.done, {} # the empty brackets are a placeholder for info dictionary

    def _execute_trade(self, action):
        #Execute a trade by selling shares at the current price
        current_price = self.data['price'].iloc[self.current_step]
        self.execution_prices.append((action, current_price))  # Log the executed trade
        self.total_shares_traded += action

    def _calculate_IS_ppo(self):
        # Calculate the IS for the agent's trading strategy 
        total_quantity = sum([trade[0] for trade in self.execution_prices])

        if total_quantity == 0: # No shares traded
            return 0

        avg_executed_price = sum([trade[0] * trade[1] for trade in self.execution_prices]) / total_quantity
        traded_volume = total_quantity
        IS_ppo = (self.initial_price * traded_volume) - (avg_executed_price * traded_volume) # as mentioned in paper
        return IS_ppo

    def _calculate_IS_twap(self):
        # Calculate the IS for TWAP strategy
        twap_order = self.total_shares_traded / self.T  # TWAP order size (constant per period)
        twap_execution_price = self.data['second_best_bid'].mean() # Paper says twap uses at least second-best bid price on average 
        traded_volume = self.total_shares_to_trade
        IS_twap = (self.initial_price * traded_volume) - (twap_execution_price * traded_volume)
        return IS_twap    

    def _calculate_reward(self):
        # Calculate the reward based on the agent's IS compared to TWAP
        IS_ppo = self._calculate_IS_ppo()
        IS_twap = self._calculate_IS_twap()

        if IS_ppo < IS_twap:
            return -1
        elif IS_twap <= IS_ppo < 1.1 * IS_twap:
            return 0
        elif IS_ppo >= 1.1 * IS_twap:
            return 1
        return 0