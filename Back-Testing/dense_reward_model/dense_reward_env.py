from numba.typed import List
import gym
from gym import spaces
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from datetime import datetime, timedelta
import pytz
from polygon import RESTClient
import databento as db
from functools import lru_cache
import random
from test_model.dense_reward import TradingRewards
import math

class TradingEnvironment(gym.Env):
    metadata = {'render.modes': ['human']}

    # Preferred timeframe: The number of steps that the user wants to complete the trade in
    def __init__(self, data, raw_data, action_space, original_action_space, eval=False, preferred_timeframe=390,
                 initial_inventory=10, scenario='medium'):
        super(TradingEnvironment, self).__init__()
        self.data = data
        self.raw_data = raw_data
        self.current_step = 0
        self.eval = eval
        self.preferred_timeframe = preferred_timeframe
        self.initial_inventory = initial_inventory
        self.remaining_inventory = self.initial_inventory
        self.elapsed_time = 0
        self.trades = []
        self.cumulative_reward = 0
        self.scenario = scenario
        self.vwap_price_set_executed_prices = []

        # Define scenario-specific penalties
        if self.scenario == 'large':
            self.beta = 1
            self.delta = 1
        elif self.scenario == 'medium-large':
            self.beta = 1e2
            self.delta = 1e2
        elif self.scenario == 'medium':
            self.beta = 1e3
            self.delta = 1e3
        elif self.scenario == 'small-medium':
            self.beta = 1e4
            self.delta = 1e4
        elif self.scenario == 'small':
            self.beta = 1e5
            self.delta = 1e5
        else:
            raise ValueError(f"Unknown scenario: {self.scenario}")

        # Extract state columns - have to change according to requirement
        self.state_columns = ['open', 'high', 'low', 'close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist',
                              'Stoch_k', 'Stoch_d', 'OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 'ATR_1', 'ADX',
                              '+DI', '-DI', 'CCI', 'ATR_2', 'ATR_5', 'ATR_10', 'ATR_20', 'ADX', '+DI', '-DI',
                              'CCI', 'DLR', 'transaction_cost', 'forecast_6Hr_open', 'market_liquidity',
                              'expected_price',
                              'log_return', 'volatility', 'mid_price', 'mean_vol', 'mean_liq',
                              '5_min_volatility', '5_min_volume', '5_min_TC', 'forecast_6Hr_close',
                              'forecast_6Hr_high', 'forecast_6Hr_low', 'forecast_6Hr_volatility',
                              'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost', "bid_price", "ask_price"]

        self.state_columns_all_data = self.state_columns + ["ratio", "size_of_slice", "execution_price", "time_left"]

        # Define action space - [%_slice, timing_of_next_slice] * Sequence_Length

        self.original_action_space = original_action_space
        # self.action_space = action_space
        self.remaining_inventory_penalty = True
        self.add_inventory_to_state = True
        self.reward_window = []


        up_amount = self.original_action_space.high[0]
        down_amount = self.original_action_space.low[0]

        self.low = np.array([down_amount])
        self.high = np.array([up_amount])

        if self.add_inventory_to_state:
            shape = len(self.state_columns) + 4
        else:
            shape = len(self.state_columns)

        self.twap = 26
        self.observation_space = spaces.Box(low=-100000, high=100000, shape=(shape,),
                                            dtype=np.float32)
        self.action_space = spaces.Box(low=np.array([0]), high=np.array([2*self.twap]), dtype=np.float32)

        # self.action_space = spaces.Discrete(3)
        # self.action_mapping_amount = {0: 0.02, 1: 0.15, 2: 0.35}
        # self.action_mapping_time = {0: 30, 1: 40, 2: 50}

        self.minimum_reward = -1000
        self.reward_range = (1000, self.minimum_reward)
        self.size_of_slice = 0
        self.execution_price = 0
        self.prev_is_t = 0
        self.is_t_1 = 0
        self.expected_price_set = []
        self.avg_wvap = []

    def _get_state(self):
        market_conditions = self._next_observation()
        arr = np.zeros_like(len(market_conditions) + 1)
        ratio = self.remaining_inventory / self.initial_inventory
        if self.add_inventory_to_state:
            # arr[:len(market_conditions)] = market_conditions
            # arr[-1] = ratio
            # market_conditions = arr
            # market_conditions = np.append(market_conditions, ratio)
            market_conditions = np.concatenate([market_conditions, ratio * np.ones(1, dtype=np.float32)])
            market_conditions = np.append(market_conditions, self.size_of_slice / self.initial_inventory)
            market_conditions = np.append(market_conditions, self.execution_price)
            market_conditions = np.append(market_conditions,
                                          ((self.preferred_timeframe - self.elapsed_time) / self.preferred_timeframe))

        return market_conditions

    def scale_action(self, action: np.ndarray) -> np.ndarray:
        """
        Rescale the action from [low, high] to [-1, 1]
        (no need for symmetric action space)

        :param action: Action to scale
        :return: Scaled action
        """
        return 2.0 * ((action - self.low) / (self.high - self.low)) - 1.0

    def unscale_action(self, scaled_action: np.ndarray) -> np.ndarray:
        """
        Rescale the action from [-1, 1] to [low, high]
        (no need for symmetric action space)

        :param scaled_action: Action to un-scale
        """
        return self.low + (0.5 * (scaled_action + 1.0) * (self.high - self.low))

    def _next_observation(self):

        return self.data[self.state_columns].iloc[self.current_step].values

    def reset(self):
        # print('------------------------------------------------Class resetted------------------------------------------------')
        self.current_step = random.randint(1, len(self.data) - 1)
        self.cumulative_reward = 0
        self.remaining_inventory = self.initial_inventory
        self.elapsed_time = 0
        self.trades = []
        self.expected_price_set = []
        self.avg_wvap = []

        return self._get_state()

    def process_reward_window(self, reward):
        if len(self.reward_window) < 3000:
            self.reward_window.append(reward)
        else:
            self.reward_window.append(reward)
            self.reward_window.pop(0)
        curr_mean = np.mean(np.array(self.reward_window))
        curr_std = np.std(np.array(self.reward_window))
        eps = 1e-05
        normalized_mean = (reward - curr_mean) / (curr_std + eps)

        return normalized_mean

    def step(self, action):
        # Adding some noise to the actions

        # print(f'Action taken: {action}')
        # action = self.unscale_action(action)
        # action = (self.action_mapping_amount[action[0]], self.action_mapping_time[action[1]])

        #
        # if not self.eval:
        #     action = self._add_noise_to_action(action)

        # size_of_slice = action[0] * self.remaining_inventory
        # size_of_slice = action[0] * self.initial_inventory

        # Convert size of slice into whole number
        size_of_slice = np.ceil(action)[0]

        # Scale action[1] to a desired range, e.g., 1 to 10
        # timing_of_slice = round(action[1])
        timing_of_slice = 1

        # print(f'timing_of_slice: {timing_of_slice}')


        self.elapsed_time += timing_of_slice

        execution_price = self._take_action(size_of_slice)
        # execution_price, size_of_slice = self._take_action_v2(size_of_slice)

        # Print current and next step for debugging
        # print(f'Current step: {self.current_step}')
        self.current_step += timing_of_slice
        # print(f'Next step: {self.current_step}')

        # Ensure the index is sequential
        # if self.current_step >= len(self.data):
        #     self.current_step = len(self.data) - 1

        if self.current_step >= len(self.data):
            self.current_step = 1

        expected_price = self.raw_data['close'].iloc[self.current_step]
        slippage, transaction_Costs, opportunity_cost = (0,0,0)
        reward, is_action, is_twap = self.input_is_values_to_reward(expected_price, size_of_slice)
        slippage = is_action


        done = self.remaining_inventory <= 0 or self.elapsed_time >= self.preferred_timeframe

        self.cumulative_reward += reward

        # if done:
        #     print(f'Cumulative Rewards: {self.cumulative_reward}')
        # ic(reward)
        # ic(slippage)
        # ic(transaction_Costs)
        # ic(opportunity_cost)
        self.execution_price = execution_price
        self.size_of_slice = size_of_slice

        trade_info = {
            'step': self.current_step,
            #                 'timestamp': self.data.index[self.current_step],
            'action': action[0],
            'price': expected_price,
            'shares': self.size_of_slice,
            'timestamp': self.data['datetime'].iloc[self.current_step],
            'reward': reward,
            'slippage': slippage,
            'transaction_cost': transaction_Costs,
            "opportunity_cost": opportunity_cost,
            'inventory': self.remaining_inventory,
            'time left': self.preferred_timeframe - self.elapsed_time,
            'IS': slippage,
            'IS_diff': slippage - is_twap,
            'IS_twap': is_twap,
        }
        self.trades.append(trade_info)
        info = {
            'step': self.current_step,
            'action': action[0],
            'price': expected_price,
            'IS': slippage,
            'IS_diff': slippage - is_twap,
            'IS_twap': is_twap,
        }

        if self.eval:
            ic(trade_info)
            ic(reward)
        if self.current_step >= len(self.data):
            self.current_step = 0

        return self._get_state(), reward, done, info

    def _add_noise_to_action(self, action):
        # Add noise to the first action (percentage of inventory)
        noise_action_0 = np.random.normal(0, 0.03, size=action[0].shape)  # Small noise for percentage
        action[0] += noise_action_0
        action[0] = np.clip(action[0], self.low[0], self.high[0])

        # Add noise to the second action (timing of next slice)
        # noise_action_1 = np.random.normal(0, 10, size=action[1].shape)  # Setting SD to be 5% of the range (1-100)
        # action[1] += noise_action_1
        # action[1] = np.clip(action[1], self.low[1], self.high[1])

        return action

    def _take_action(self, size_of_slice):
        self.remaining_inventory -= size_of_slice
        # print(f'Remaining inventory: {self.remaining_inventory}')
        if self.remaining_inventory < 0:
            self.remaining_inventory = 0
        execution_price = self.data['close'].iloc[self.current_step]
        return execution_price

    def _take_action_v2(self, size_of_slice):
        if size_of_slice >= self.remaining_inventory:
            size_of_slice = self.remaining_inventory
        self.remaining_inventory -= size_of_slice
        execution_price = self.data['close'].iloc[self.current_step]
        return execution_price, size_of_slice

    def _calculate_transaction_cost(self, volume, daily_volume, volatility=None):
        if volatility is None:
            volatility = self.data['volatility'].iloc[self.current_step]
        return volatility * np.sqrt(volume / daily_volume)

    @staticmethod
    def calculate_vwap(bid_prices, bid_sizes, size_of_slice):
        # VWAP calculation: sum(price * size) / sum(size)
        cum_sum_size = 0
        for idx, size in enumerate(bid_sizes):
            cum_sum_size += size
            if cum_sum_size >= size_of_slice:
                break

        # Only consider elements before order is filled
        bid_prices = bid_prices[:idx + 1]
        bid_sizes = bid_sizes[:idx + 1]
        vwap = np.sum(bid_prices * bid_sizes) / np.sum(bid_sizes)
        return vwap

    def input_is_values_to_reward(self, expected_price, size_of_slice):

        rewards_calc = TradingRewards()

        expected_price = self.raw_data.iloc[self.current_step]['bid_price']
        action = size_of_slice
        is_action = (expected_price -  self.raw_data.iloc[self.current_step]['VWAP']) * size_of_slice
        self.expected_price_set.append(expected_price)
        self.avg_wvap.append(self.raw_data.iloc[self.current_step]['VWAP'])

        is_twap = (expected_price -  self.raw_data.iloc[self.current_step]['VWAP']) * self.twap
        is_t = is_action  # Current Implementation Shortfall
        avg_expected_price = sum(self.expected_price_set) / len(self.expected_price_set)
        avg_wvap = sum(self.avg_wvap) / len(self.avg_wvap)

        is_func = lambda x: (expected_price -  self.raw_data.iloc[self.current_step]['VWAP']) * x

        avg_is_func =  lambda x: (avg_expected_price -  avg_wvap) * x


        if self.elapsed_time == 1:
            self.is_t_1 = is_twap
            self.prev_is_t = is_twap

        is_t_minus_1 = self.prev_is_t  # Previous Implementation Shortfall
        is_1 = self.is_t_1  # Initial Implementation Shortfall
        is_final_step = False  # Boolean indicating if this is the final step

        if self.elapsed_time >= self.preferred_timeframe:
            is_final_step = True

        # Calculate the reward
        reward = rewards_calc.calculate_reward(
            action, self.twap, is_action, is_twap, avg_is_func, is_func,
            is_t, is_t_minus_1, is_1, is_final_step
        )
        self.prev_is_t = is_t

        return reward, is_action, is_twap


    def render(self, mode='human', close=False):
        print('--------------------------------------------------')
        print(f'Steps: {self.current_step}')
        print(f'Remaining inventory: {self.remaining_inventory}')
        print(f'Cumulative reward: {self.cumulative_reward}')
        self.print_trades()

    def print_trades(self):
        trades_df = pd.DataFrame(self.trades)
        for trade in self.trades:
            print(
                f"Step: {trade['step']}, Action: {trade['action']}, Price: {trade['price']}, Shares: {trade['shares']}, Reward: {trade['reward']}, Inventory: {trade['inventory']}, TimeLeft: {trade['time left']}")

        return self.trades
