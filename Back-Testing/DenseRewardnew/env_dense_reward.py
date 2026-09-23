from numba import njit, jit
# from icecream import ic
from numba.typed import List
import gym
from gym import spaces
import numpy as np
import pandas as pd

import random
from test_model.dense_reward import TradingRewards

import math

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
from icecream import ic
import math


class EvalTradingEnvironment(gym.Env):
    metadata = {'render.modes': ['human']}

    # Preferred timeframe: The number of steps that the user wants to complete the trade in
    def __init__(self, data, raw_data, eval=False, preferred_timeframe=390, initial_inventory=10, scenario='medium'):
        super(EvalTradingEnvironment, self).__init__()
        self.data = data
        self.raw_data = raw_data
        self.eval = eval

        self.current_step = 0

        self.preferred_timeframe = preferred_timeframe
        self.initial_inventory = initial_inventory
        self.remaining_inventory = self.initial_inventory
        self.elapsed_time = 0
        self.trades = []
        self.cumulative_reward = 0
        self.scenario = scenario
        self.time_step_per_action = 40
        self.reset_reward_window = False


        # Extract state columns - have to change according to requirement
        self.state_columns = ['open', 'high', 'low', 'close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist',
                              'Stoch_k', 'Stoch_d', 'OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 'ATR_1', 'ADX',
                              '+DI', '-DI', 'CCI', 'ATR_2', 'ATR_5', 'ATR_10', 'ATR_20', 'ADX', '+DI', '-DI',
                              'CCI', 'DLR', 'transaction_cost', 'forecast_6Hr_open', 'market_liquidity',
                              'expected_price', 'Rolling Volatility', 'cusum_feature', 'SADF Feature',
                              'corwin_schultz_spread', 'trade_sign', 'fib_level_0.236',
                              'fib_level_0.382', 'fib_level_0.5', 'fib_level_0.618',
                              'fib_level_0.786', 'cum_volume', 'bar_index',
                              'log_return', 'volatility', 'mid_price', 'mean_vol', 'mean_liq',
                              '5_min_volatility', '5_min_volume', '5_min_TC', 'forecast_6Hr_close',
                              'forecast_6Hr_high', 'forecast_6Hr_low', 'forecast_6Hr_volatility',
                              'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost', "bid_price", "ask_price"]
    
        self.state_columns_all_data = self.state_columns + ["ratio", "time_left"]

        # Define action space - [%_slice, timing_of_next_slice] * Sequence_Length
        self.twap_size = (self.initial_inventory * self.time_step_per_action / self.preferred_timeframe)
        self.action_space = spaces.Box(low=np.array([0]), high=np.array([2051.282]), dtype=np.float32)

        self.observation_space = spaces.Box(low=-1000, high=1000, shape=(len(self.state_columns_all_data),),
                                            dtype=np.float32)

        self.start_vwap_price = self.data.iloc[0]['VWAP']
        self.vwap_price_set_executed_prices = []
        self.reward_window = []
        self.remaining_inventory_penalty = True
        self.add_inventory_to_state = True


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
            # market_conditions = np.append(market_conditions, self.execution_price)
            market_conditions = np.append(market_conditions,
                                          ((self.preferred_timeframe - self.elapsed_time) / self.preferred_timeframe))
        return market_conditions

    def _next_observation(self):
        return self.data[self.state_columns].iloc[self.current_step].values

    def reset(self):
        if self.eval:
            self.current_step = 0
        else:
            self.current_step = random.randint(1, len(self.data) - 1)

        self.cumulative_reward = 0
        self.remaining_inventory = self.initial_inventory
        self.elapsed_time = 0
        self.trades = []
        self.vwap_price_set_executed_prices = []
        if self.reset_reward_window:
            self.reward_window = []

        return self._get_state()

    def step(self, action):
        # Adding some noise to the actions
        # print(f'Action taken: {action}')

        size_of_slice = action[0]
        # Convert size of slice into whole number
        size_of_slice = int(np.ceil(size_of_slice))

        timing_of_slice = self.time_step_per_action
        self.elapsed_time += timing_of_slice

        if self.elapsed_time >= self.preferred_timeframe:
            size_of_slice = self.remaining_inventory

        # Print current and next step for debugging
        # print(f'Current step: {self.current_step}')
        self.current_step += timing_of_slice
        # print(f'Next step: {self.current_step}')

        # Ensure the index is sequential
        if self.current_step >= len(self.data):
            self.current_step = len(self.data) - 1

        execution_price = self._take_action(size_of_slice)

        if self.current_step >= len(self.data):
            self.current_step = 1


        done = self.remaining_inventory <= 0 or self.elapsed_time >= self.preferred_timeframe


        # if done:
        #     print(f'Cumulative Rewards: {self.cumulative_reward}')

        info = {
            'step': self.current_step,
            #                 'timestamp': self.data.index[self.current_step],
            'action': action[0],
            'inventory': self.remaining_inventory,
            'time left': self.preferred_timeframe - self.elapsed_time,
            'volatility' : self.raw_data['volatility'].iloc[self.current_step],
            'market_liquidity' : self.raw_data['market_liquidity'].iloc[self.current_step],
            'shares': size_of_slice,
        }
        self.trades.append(info)
        # ic(trade_info)
        # info = {
        #     'step': self.current_step,
        #     'action': action,
        #     'price': execution_price
        # }

        return self._get_state(), 0, done, info

    def _add_noise_to_action(self, action):
        # Add noise to the first action (percentage of inventory)
        noise_action_0 = np.random.normal(0, 0.02, size=action[0].shape)  # Small noise for percentage
        action[0] += noise_action_0
        action[0] = np.clip(action[0], self.action_space.low[0], self.action_space.high[0])

        # Add noise to the second action (timing of next slice)
        noise_action_1 = np.random.normal(0, 5, size=action[1].shape)  # Setting SD to be 5% of the range (1-100)
        action[1] += noise_action_1
        action[1] = np.clip(action[1], self.action_space.low[1], self.action_space.high[1])

        return action

    def _take_action(self, size_of_slice):
        self.remaining_inventory -= size_of_slice
        # print(f'Remaining inventory: {self.remaining_inventory}')
        if self.remaining_inventory < 0:
            self.remaining_inventory = 0
        execution_price = self.data['close'].iloc[self.current_step]
        return execution_price

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



class TradingEnvironmentMacroV3(gym.Env):
    metadata = {'render.modes': ['human']}

    # Preferred timeframe: The number of steps that the user wants to complete the trade in
    def __init__(self, data, raw_data, five_level_data, eval=False, preferred_timeframe=390, initial_inventory=10000, scenario='large'):
        super(TradingEnvironmentMacroV3, self).__init__()
        self.data = data
        self.raw_data = raw_data
        self.five_level_data = five_level_data
        self.current_step = 0
        self.eval = eval
        self.preferred_timeframe = preferred_timeframe
        self.total_inventory = initial_inventory  # Store total inventory
        self.remaining_inventory = self.total_inventory
        self.time_elapsed = 0
        self.trades = []
        self.cumulative_reward = 0
        self.verbose = False
        self.scenario = scenario
        self.vwap_price_set_executed_prices = []
        self.T = len(five_level_data)


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
                              'log_return', 'volatility', 'mid_price', 'mean_vol', 'mean_liq','5_min_volatility']
                            #   '5_min_volatility', '5_min_volume', '5_min_TC', 'forecast_6Hr_close',
                            #   'forecast_6Hr_high', 'forecast_6Hr_low', 'forecast_6Hr_volatility',
                            #   'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost', "bid_price", "ask_price"]

        self.five_level_state_columns = list(filter(lambda x: "processed" in x, self.five_level_data.columns.tolist()))

        self.state_columns_all_data = self.state_columns + ["ratio", "size_of_slice", "execution_price", "time_left"] + self.five_level_state_columns


        # Define action space - [%_slice, timing_of_next_slice] * Sequence_Length

        # self.action_space = action_space
        self.remaining_inventory_penalty = True
        self.add_inventory_to_state = True
        self.reward_window = []
        self.trades_info = []

        if self.add_inventory_to_state:
            shape = len(self.state_columns) + 4
        else:
            shape = len(self.state_columns)
        self.observation_space = spaces.Box(low=-100000, high=100000, shape=(len(self.state_columns_all_data)-10,),
                                            dtype=np.float32)

        self.twap = self._get_twap_order_size(self.total_inventory, self.preferred_timeframe)


        self.action_space = spaces.Box(low=np.array([0]), high=np.array([2*self.twap]), dtype=np.float32)
        # self.action_space = spaces.Box(low=np.array([0]), high=np.array([2 * self.twap]), dtype=np.float32)

        # self.action_space = spaces.Box(low=np.array([0]), high=np.array([52]), dtype=np.float32)

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
        self.plus_set = []
        self.minus_set = []
        self.normal_set = []
        self.action_set = []


    def _get_state(self):
        market_conditions = self._next_observation()
        five_level_data= self.five_level_data[self.five_level_state_columns].iloc[self.current_step].values
        ratio = self.remaining_inventory / self.total_inventory
        if self.add_inventory_to_state:
            # arr[:len(market_conditions)] = market_conditions
            # arr[-1] = ratio
            # market_conditions = arr
            # market_conditions = np.append(market_conditions, ratio)
            market_conditions = np.concatenate([market_conditions, ratio * np.ones(1, dtype=np.float32)])
            market_conditions = np.append(market_conditions, self.size_of_slice / self.total_inventory)
            market_conditions = np.append(market_conditions, self.execution_price)
            market_conditions = np.append(market_conditions,
                                          ((self.preferred_timeframe - self.time_elapsed) / self.preferred_timeframe))

            market_conditions = np.append(market_conditions, five_level_data)
        return market_conditions

    def _next_observation(self):

        return self.data[self.state_columns].iloc[self.current_step].values

    def reset(self):
        # print('------------------------------------------------Class resetted------------------------------------------------')
        if not self.eval:
            self.current_step = random.randint(1, len(self.data) - 1)
        else:
            self.current_step = 0
        self.cumulative_reward = 0
        self.remaining_inventory = self.total_inventory
        self.time_elapsed = 0
        self.trades = []
        self.expected_price_set = []
        self.avg_wvap = []
        self.plus_set = []
        self.minus_set = []
        self.normal_set = []
        self.action_set = []

        return self._get_state()

    def step(self, action):
        # Adding some noise to the actions

        # Convert size of slice into whole number

        size_of_slice = round(action[0])
        timing_of_slice = 1

        size_of_slice = np.clip(size_of_slice, 0, self.remaining_inventory)



        self.time_elapsed += timing_of_slice

        self.current_step += timing_of_slice


        if self.current_step >= len(self.data):
            self.current_step = 1


        reward, is_action, is_twap, arrival_price, expected_price = self.input_is_values_to_reward(size_of_slice)
        # reward, is_action, is_twap, arrival_price, expected_price = self.simple_reward_func(size_of_slice)

        done = self.remaining_inventory <= 0 or self.time_elapsed >= self.preferred_timeframe


        # if done and self.remaining_inventory > 0:
        #     ratio = ((self.total_inventory- self.remaining_inventory) / self.total_inventory)
        #     reward = reward + 10 * ratio
        #     print('remaining inventory reward')
        # print(30 * (last_step_inventory / self.initial_inventory))

        self.cumulative_reward += reward

        # ic(opportunity_cost)
        self.execution_price = expected_price
        self.size_of_slice = size_of_slice

        trade_info = {
            'step': self.current_step,
            #                 'timestamp': self.data.index[self.current_step],
            'action': action,
            'price': expected_price,
            "arrival": arrival_price,
            'shares': self.size_of_slice,
            'reward': reward,
            'inventory': self.remaining_inventory,
            'time left': self.preferred_timeframe - self.time_elapsed,
            'IS': -is_action,
            'IS_diff': is_action - is_twap,
            'IS_twap': is_twap,
        }
        self.trades.append(trade_info)
        # ic(trade_info)
        #
        # if not self.eval:
        #     ic(trade_info)
        if self.current_step >= len(self.data):
            self.current_step = 0

        return self._get_state(), reward, done, trade_info


    def _execute_trade(self, size_of_slice):
        # Initialize variables
        shares_left = size_of_slice
        total_executed_shares = 0
        total_executed_value = 0

        # Loop through the top 5 bid prices and their respective sizes
        for i in range(1, 6):
            bid_size = self.five_level_data[f'bid_size_{i}'].iloc[min(self.current_step, self.T - 1)]
            bid_price = self.five_level_data[f'bid_price_{i}'].iloc[min(self.current_step, self.T - 1)]

            trade_volume = min(shares_left, bid_size)
            total_executed_shares += trade_volume
            total_executed_value += trade_volume * bid_price
            shares_left -= trade_volume
            if self.verbose:
                print("step : ", self.current_step, " Traded Shares: ", trade_volume, "Price: ", bid_price,
                      "Total Executed Shares: ", total_executed_shares, "Total Executed Value: ", total_executed_value)
            if shares_left <= 0:
                break

        # Handle remaining shares that could not be sold at the top 5 bids
        penalty = 0
        if shares_left > 0:
            # Could not execute all shares
            # Apply a quadratic penalty
            penalty = shares_left ** 2
            # Remaining shares stay in the inventory for now
            worst_price = self.five_level_data[f'bid_price_5'].iloc[min(self.current_step, self.T - 1)]
            total_executed_shares += shares_left
            total_executed_value += shares_left * worst_price
            if self.verbose:
                print("Trading Share at Worst Bid: ", shares_left, "Price: ", worst_price, "Total Executed Shares: ",
                      total_executed_shares, "Total Executed Value: ", total_executed_value)

        # Calculate the weighted average price
        if total_executed_shares > 0:
            weighted_avg_price = total_executed_value / total_executed_shares
        else:
            # No shares executed; use the worst bid price as an estimate
            weighted_avg_price = self.five_level_data['bid_price_5'].iloc[min(self.current_step, self.T - 1)]

        i = 1
        bid_size = self.five_level_data[f'bid_size_{i}'].iloc[min(self.current_step, self.T - 1)]
        bid_price = self.five_level_data[f'bid_price_{i}'].iloc[min(self.current_step, self.T - 1)]
        if self.verbose:
            print("Best Bid: ", bid_price, "total_executed_shares: ", total_executed_shares, "total_executed_value: ",
                  total_executed_value, "weighted_avg_price: ", weighted_avg_price)
        # Log the executed trade
        # self.execution_prices.append((total_executed_shares, weighted_avg_price, bid_size, bid_price))
        # self.total_shares_traded += total_executed_shares

        return total_executed_shares, weighted_avg_price, bid_size, bid_price

    def _calculate_IS_twap(self):
        total_traded_volume = 0
        total_executed_value = 0

        twap_order_size = self.twap
        # print("================")
        # print("twap_order_size : ",twap_order_size)
        best_price = 0
        step = self.current_step
        shares_left = twap_order_size

        for i in range(1, 6):
            bid_size = self.five_level_data[f'bid_size_{i}'].iloc[step]
            bid_price = self.five_level_data[f'bid_price_{i}'].iloc[step]
            # print("bid_size: ", bid_size, "bid_price: ", bid_price)
            if i == 1:
                best_price += bid_price
            trade_volume = min(shares_left, bid_size)
            total_traded_volume += trade_volume
            total_executed_value += trade_volume * bid_price
            shares_left -= trade_volume
            if self.verbose:
                print("step : ", step, " Traded Shares: ", trade_volume, "Price: ", bid_price,
                      "Total Executed Shares: ", total_traded_volume, "Total Executed Value: ",
                      total_executed_value)
            if shares_left <= 0:
                break

        # Handle remaining shares
        if shares_left > 0:
            # Assume remaining shares are sold at the worst bid price
            worst_price = self.five_level_data[f'bid_price_5'].iloc[min(step, self.T - 1)]
            total_traded_volume += shares_left
            total_executed_value += shares_left * worst_price
            if self.verbose:
                print("Trading Share at Worst Bid: ", shares_left, "Price: ", worst_price,
                      "Total Executed Shares: ", total_traded_volume, "Total Executed Value: ",
                      total_executed_value)

        best_price = best_price / self.preferred_timeframe

        IS_twap = (best_price * self.total_inventory) - total_executed_value

        if self.verbose:
            print("IS_twap : ", IS_twap, " best_price : ", best_price, " total_traded_volume : ", total_traded_volume,
                  " total_executed_value : ", total_executed_value)
        # print("IS_twap : ",IS_twap)
        return IS_twap, best_price

    def input_is_values_to_reward(self, size_of_slice):
        rewards_calc = TradingRewards()

        total_executed_shares, weighted_avg_price, bid_size, bid_price = self._execute_trade(size_of_slice)
        expected_price = weighted_avg_price

        self.remaining_inventory -= total_executed_shares


        arrival_price = bid_price
        action = size_of_slice
        is_action =  arrival_price * size_of_slice -  weighted_avg_price *  total_executed_shares
        is_action = -1 * is_action

        def is_func(action):
            if action < 0:
                return 0
            else:
                total_executed_shares, weighted_avg_price, bid_size, bid_price = self._execute_trade(action)
                return -bid_price * action + weighted_avg_price * total_executed_shares

        is_twap, best_price = self._calculate_IS_twap()
        is_twap = -1 * is_twap

        is_action_plus = is_func(action + 0.2 * self.twap)
        is_action_minus = is_func(action - 0.2 * self.twap)


        self.action_set.append(action)
        self.plus_set.append(is_action_plus)
        self.minus_set.append(is_action_minus)
        self.normal_set.append(is_action)


        is_t = is_action  # Current Implementation Shortfall
        total_shares_plus = sum(self.action_set) + len(self.plus_set) * (0.2 * self.twap)
        total_shares_minus = sum(self.action_set) - len(self.minus_set) * (0.2 * self.twap)


        avg_plus_set = sum(self.plus_set) / total_shares_plus
        avg_minus_set = sum(self.minus_set) / total_shares_minus
        avg_normal_set = sum(self.normal_set) / (sum(self.action_set))


        if self.time_elapsed == 1:
            self.is_t_1 = is_action
            self.prev_is_t = is_action

        is_t_minus_1 = self.prev_is_t  # Previous Implementation Shortfall
        is_1 = self.is_t_1  # Initial Implementation Shortfall
        is_final_step = False  # Boolean indicating if this is the final step

        if self.time_elapsed >= self.preferred_timeframe:
            is_final_step = True

        # Calculate the reward
        reward = rewards_calc.calculate_reward(
            action, self.twap, is_action, is_twap, avg_plus_set, avg_minus_set, avg_normal_set, is_func,
            is_t, is_t_minus_1, is_1, is_final_step
        )
        self.prev_is_t = is_t
        return reward, is_action, is_twap, arrival_price, expected_price

    def _calculate_time_pressure_penalty(self):
        time_elapsed_ratio = self.time_elapsed / self.preferred_timeframe
        inventory_remaining_ratio = self.remaining_inventory / self.total_inventory

        if time_elapsed_ratio > inventory_remaining_ratio:
            return (time_elapsed_ratio - inventory_remaining_ratio) * 5  # Adjust the multiplier as needed
        return 0

    def simple_reward_func(self, size_of_slice):

        total_executed_shares, weighted_avg_price, bid_size, bid_price = self._execute_trade(size_of_slice)

        self.remaining_inventory -= total_executed_shares


        arrival_price = bid_price
        action = size_of_slice
        is_action =  arrival_price * size_of_slice -  weighted_avg_price *  total_executed_shares
        self.normal_set.append(is_action)
        avg_agent = sum(self.normal_set)/len(self.normal_set)
        is_twap, best_price = self._calculate_IS_twap()

        self.avg_wvap.append(is_twap)
        avg_twap = sum(self.avg_wvap)/len(self.avg_wvap)



        if avg_agent > avg_twap:
            reward =  -1
        elif avg_twap >= avg_agent and avg_agent > 0.9 * avg_twap:
            reward = 0
        elif 0.9 * avg_twap >= avg_agent:
            reward = 1
        else:
            reward = 0

        reward_2 = -abs(action - self.twap) / (0.8 * self.twap)

        reward =  reward + reward_2
        return reward, is_action, is_twap, arrival_price, weighted_avg_price



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

    def _get_twap_order_size(self, inventory, preferred_timeframe):
        # twap_total_order_size = self.data['bid_price_2'].iloc[current_step:preferred_timeframe].sum()  # This is the TWAP order size

        # return twap_total_order_size/preferred_timeframe  # This variable will be inputted -- total_trades / total_timeframe (in mins)
        return inventory / preferred_timeframe


class TradingEnvironmentMacroTWAPTest(gym.Env):
    metadata = {'render.modes': ['human']}

    # Preferred timeframe: The number of steps that the user wants to complete the trade in
    def __init__(self, data, raw_data, five_level_data, eval=False, preferred_timeframe=390, initial_inventory=10000,
                 scenario='large'):
        super(TradingEnvironmentMacroTWAPTest, self).__init__()
        self.data = data
        self.raw_data = raw_data
        self.five_level_data = five_level_data
        self.current_step = 0
        self.eval = eval
        self.preferred_timeframe = preferred_timeframe
        self.total_inventory = initial_inventory  # Store total inventory
        self.remaining_inventory = self.total_inventory
        self.time_elapsed = 0
        self.trades = []
        self.cumulative_reward = 0
        self.verbose = False
        self.scenario = scenario
        self.vwap_price_set_executed_prices = []
        self.T = len(five_level_data)

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

        self.five_level_state_columns = list(filter(lambda x: "processed" in x, self.five_level_data.columns.tolist()))

        self.state_columns_all_data = self.state_columns + ["ratio", "size_of_slice", "execution_price",
                                                            "time_left"] + self.five_level_state_columns

        # Define action space - [%_slice, timing_of_next_slice] * Sequence_Length

        # self.action_space = action_space
        self.remaining_inventory_penalty = True
        self.add_inventory_to_state = True
        self.reward_window = []
        self.trades_info = []

        if self.add_inventory_to_state:
            shape = len(self.state_columns) + 4
        else:
            shape = len(self.state_columns)

        self.observation_space = spaces.Box(low=-100000, high=100000, shape=(len(self.state_columns_all_data),),
                                            dtype=np.float32)

        self.twap = self._get_twap_order_size(self.total_inventory, self.preferred_timeframe)

        self.action_space = spaces.Box(low=np.array([0]), high=np.array([2 * self.twap]), dtype=np.float32)
        # self.action_space = spaces.Box(low=np.array([0]), high=np.array([2 * self.twap]), dtype=np.float32)

        # self.action_space = spaces.Box(low=np.array([0]), high=np.array([52]), dtype=np.float32)

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
        self.plus_set = []
        self.minus_set = []
        self.normal_set = []
        self.action_set = []

    def _get_state(self):
        market_conditions = self._next_observation()
        five_level_data = self.five_level_data[self.five_level_state_columns].iloc[self.current_step].values
        ratio = self.remaining_inventory / self.total_inventory
        if self.add_inventory_to_state:
            # arr[:len(market_conditions)] = market_conditions
            # arr[-1] = ratio
            # market_conditions = arr
            # market_conditions = np.append(market_conditions, ratio)
            market_conditions = np.concatenate([market_conditions, ratio * np.ones(1, dtype=np.float32)])
            market_conditions = np.append(market_conditions, self.size_of_slice / self.total_inventory)
            market_conditions = np.append(market_conditions, self.execution_price)
            market_conditions = np.append(market_conditions,
                                          ((self.preferred_timeframe - self.time_elapsed) / self.preferred_timeframe))

            market_conditions = np.append(market_conditions, five_level_data)
        return market_conditions

    def _next_observation(self):

        return self.data[self.state_columns].iloc[self.current_step].values

    def reset(self):
        # print('------------------------------------------------Class resetted------------------------------------------------')
        if not self.eval:
            self.current_step = random.randint(1, len(self.data) - 1)
        else:
            self.current_step = 0
        self.cumulative_reward = 0
        self.remaining_inventory = self.total_inventory
        self.time_elapsed = 0
        self.trades = []
        self.expected_price_set = []
        self.avg_wvap = []
        self.plus_set = []
        self.minus_set = []
        self.normal_set = []
        self.action_set = []

        return self._get_state()

    def step(self, action):
        # Adding some noise to the actions

        # Convert size of slice into whole number

        size_of_slice = round(action[0])
        timing_of_slice = 1

        size_of_slice = np.clip(size_of_slice, 0, self.remaining_inventory)

        self.time_elapsed += timing_of_slice

        self.current_step += timing_of_slice

        if self.current_step >= len(self.data):
            self.current_step = 1

        is_twap, best_price = self._calculate_IS_twap()

        done = self.time_elapsed >= self.preferred_timeframe

        self.cumulative_reward += 0

        # ic(opportunity_cost)
        self.size_of_slice = size_of_slice

        trade_info = {
            'step': self.current_step,
            #                 'timestamp': self.data.index[self.current_step],
            'action': action,

            'shares': self.size_of_slice,
            'inventory': self.remaining_inventory,
            'time left': self.preferred_timeframe - self.time_elapsed,
            'IS_twap': is_twap,
        }
        self.trades.append(trade_info)
        # ic(trade_info)
        #
        if not self.eval:
            ic(trade_info)
        if self.current_step >= len(self.data):
            self.current_step = 0

        return self._get_state(), 0, done, trade_info

    def _calculate_IS_twap(self):
        total_traded_volume = 0
        total_executed_value = 0

        twap_order_size = self.twap
        # print("================")
        # print("twap_order_size : ",twap_order_size)
        best_price = 0
        step = self.current_step
        shares_left = twap_order_size

        for i in range(1, 6):
            bid_size = self.five_level_data[f'bid_size_{i}'].iloc[step]
            bid_price = self.five_level_data[f'bid_price_{i}'].iloc[step]
            # print("bid_size: ", bid_size, "bid_price: ", bid_price)
            if i == 1:
                best_price += bid_price
            trade_volume = min(shares_left, bid_size)
            total_traded_volume += trade_volume
            total_executed_value += trade_volume * bid_price
            shares_left -= trade_volume
            if self.verbose:
                print("step : ", step, " Traded Shares: ", trade_volume, "Price: ", bid_price,
                      "Total Executed Shares: ", total_traded_volume, "Total Executed Value: ",
                      total_executed_value)
            if shares_left <= 0:
                break

        # Handle remaining shares
        if shares_left > 0:
            # Assume remaining shares are sold at the worst bid price
            worst_price = self.five_level_data[f'bid_price_5'].iloc[min(step, self.T - 1)]
            total_traded_volume += shares_left
            total_executed_value += shares_left * worst_price
            if self.verbose:
                print("Trading Share at Worst Bid: ", shares_left, "Price: ", worst_price,
                      "Total Executed Shares: ", total_traded_volume, "Total Executed Value: ",
                      total_executed_value)

        best_price = best_price / self.preferred_timeframe

        IS_twap = (best_price * self.total_inventory) - total_executed_value

        if self.verbose:
            print("IS_twap : ", IS_twap, " best_price : ", best_price, " total_traded_volume : ", total_traded_volume,
                  " total_executed_value : ", total_executed_value)
        # print("IS_twap : ",IS_twap)
        return IS_twap, best_price

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

    def _get_twap_order_size(self, inventory, preferred_timeframe):
        # twap_total_order_size = self.data['bid_price_2'].iloc[current_step:preferred_timeframe].sum()  # This is the TWAP order size

        # return twap_total_order_size/preferred_timeframe  # This variable will be inputted -- total_trades / total_timeframe (in mins)
        return inventory / preferred_timeframe
