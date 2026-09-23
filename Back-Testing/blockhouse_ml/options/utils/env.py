import gym
from gym import spaces
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from datetime import datetime, timedelta
import pytz
from polygon import RESTClient
import databento as db
import random
import math
from gym.utils import seeding

import sys

databento_api_key = "db-eKU7cAt4iTryxUbycEY7REuXXkwcU"

class TradingEnvironment(gym.Env):
    metadata = {'render.modes': ['human']}
    
    # Preferred timeframe: The number of steps that the user wants to complete the trade in
    def __init__(self, data, action_space, original_action_space, preferred_timeframe=390, initial_inventory=10, scenario='medium', inference=False):
        super(TradingEnvironment, self).__init__()
        self.data = data
        self.current_step = random.randint(0, len(self.data) - 1)
        # self.prev_step = self.current_step
        self.preferred_timeframe = preferred_timeframe
        self.initial_inventory = initial_inventory
        self.remaining_inventory = self.initial_inventory
        self.elapsed_time = 0
        self.trades = []
        self.cumulative_reward = []
        self.scenario = scenario
        self.vwap_price_set_executed_prices =[]

        # Define max and min rewards for clipping rewards, avoiding gradient overflow
        self.max_reward = 1e12
        self.min_reward = -1e12
        
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
        self.state_columns = ['ask_price', 'ask_size', 'bid_price', 'bid_size', 'open', 'high', 'low',
                               'close', 'volume', 'adj_close', 'time_to_maturity', 'strike_price','mid_price', 'rfr',
                               'implied_vol', 'delta', 'gamma', 'theta', 'vega',
                               'transaction_cost', 'forecast_3Hr_open', 'forecast_3Hr_high',
                               'forecast_3Hr_low', 'forecast_3Hr_close',
                               'forecast_3Hr_transaction_cost', 'forecast_3Hr_delta',
                               'forecast_3Hr_gamma', 'forecast_3Hr_theta', 'forecast_3Hr_vega', 'forecast_3Hr_implied_vol',
                               'forecast_3Hr_time_to_maturity', 'forecast_3Hr_mid_price']

        print("Length of state columns : ", len(self.state_columns))
        
        # print("Initialized environment : State Columns : ", self.state_columns)
        # Define action space - [%_slice, timing_of_next_slice] * Sequence_Length
        self.original_action_space = original_action_space
        self.action_space = action_space

        up_time = self.original_action_space.high[1]
        down_time = self.original_action_space.low[1]

        up_amount = self.original_action_space.high[0]
        down_amount = self.original_action_space.low[0]

        adjusted_up = round(self.preferred_timeframe * up_time / 390)
        adjusted_down = round(self.preferred_timeframe * down_time / 390)
        if adjusted_down < 5:
            adjusted_down = 5

        self.low = np.array([down_amount, adjusted_down])
        self.high = np.array([up_amount, adjusted_up])
        
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(len(self.state_columns),), dtype=np.float32)

        self.contract = self.data.iloc[0]["contract"]
        self.is_inference = inference
        self.timestamp = pd.to_datetime(self.data['timestamp'])
        # random.seed(0)
        self.seed(None)
    
    def _get_state(self):
        market_conditions = self._next_observation()
#         state = np.append(market_conditions, self.remaining_inventory / self.initial_inventory)
        return market_conditions
    
    def _next_observation(self):
        return self.data[self.state_columns].iloc[self.current_step].values
    
    def reset(self, randomize=True):
        # print('------------------------------------------------Class resetted------------------------------------------------')
        if randomize:
            self.current_step = random.randint(0, len(self.data) - 1)
        else:
            self.current_step = 0
        self.cumulative_reward = []
        self.remaining_inventory = self.initial_inventory
        self.elapsed_time = 0
        self.trades = []
        # self.prev_step = self.current_step
        if self.is_inference:
            self.timestamp = pd.to_datetime(self.data.iloc[0]['timestamp'])
        else:
            self.timestamp = pd.to_datetime(self.data.iloc[self.current_step]['timestamp'])
        return self._get_state()
    
    def step(self, action):
        # Adding some noise to the actions
        # action = self._add_noise_to_action(action)
        # print(f'Action taken: {action}')

        action = self._unscale_action(action)

        size_of_slice = action[0] * self.remaining_inventory
        # Convert size of slice into whole number
        size_of_slice = int(np.ceil(size_of_slice))

        # Scale action[1] to a desired range, e.g., 1 to 10
        timing_of_slice = int(np.ceil(action[1]))
        # print(f'timing_of_slice: {timing_of_slice}')
        
        self.elapsed_time += timing_of_slice
        
        if self.elapsed_time >= self.preferred_timeframe:
            size_of_slice = self.remaining_inventory

        execution_price = self._take_action(size_of_slice)

        # Print current and next step for debugging
        # print(f'Current step: {self.current_step}')
        self.current_step += timing_of_slice


        truncated = False
        done = self.remaining_inventory <= 0 or self.elapsed_time >= self.preferred_timeframe 
        
        if not self.is_inference:
            done = done or self.current_step >= len(self.data)
            if self.current_step >= len(self.data):
                self.current_step = len(self.data) - 1
            # print(f'Current step: {self.current_step}',file=sys.stderr)
            rewards_data = self._calculate_reward(size_of_slice, timing_of_slice)
            while rewards_data is None:
                self.current_step += 1
                if self.current_step >= len(self.data):
                    break
                rewards_data = self._calculate_reward(size_of_slice, timing_of_slice)
                
            
            if rewards_data is not None:
                reward, slippage, transaction_Costs = rewards_data  
                reward = self.clip_reward(reward)
                self.cumulative_reward.append(reward)
            else:
                # current_timestamp = pd.to_datetime(self.data.iloc[self.current_step]['timestamp'])
                # next_timestamp = self.get_next_valid_market_timestamp(current_timestamp, timing_of_slice)
                
                reward, slippage, transaction_Costs = sum(self.cumulative_reward)/len(self.cumulative_reward) if len(self.cumulative_reward) > 0 else self.min_reward, 0, 0
                self.remaining_inventory += size_of_slice
                truncated = True
                done = True
            # if done:
            #     print(f'Cumulative Rewards: {self.cumulative_reward}')

            trade_info = {
                    'step': self.current_step,
                    'timestamp': self.data.index[self.current_step],
                    'action': action,
                    'price': execution_price,
                    'shares': size_of_slice,
                    'reward': reward,
                    'slippage' : slippage,
                    'transaction_cost' : transaction_Costs,
                    'inventory': self.remaining_inventory,
                    'time left': self.preferred_timeframe - self.elapsed_time
                }
        else:
            current_timestamp = self.timestamp
            next_timestamp = self.get_next_valid_market_timestamp(current_timestamp, timing_of_slice)
            # print("current timestamp : ", current_timestamp, " next timestamp : ", next_timestamp)
            trade_info = {
                'timestamp': next_timestamp,
                'action': action,
                'shares': size_of_slice,
                'inventory': self.remaining_inventory,
                'time left': self.preferred_timeframe - self.elapsed_time
            }
            self.timestamp = next_timestamp

        
        self.trades.append(trade_info)

        info = {
            'step': self.current_step,
            'action': action,
            'price': execution_price
        }
        # print(f'Remaining inventory: {self.remaining_inventory}, Cumulative reward: {self.cumulative_reward}, shares: {size_of_slice}, timing of slice: {timing_of_slice}, done: {done}')
        if self.is_inference:
            return done, info
        
        return self._get_state(), reward, done, info

    def _scale_action(self, action: np.ndarray) -> np.ndarray:
        """
        Rescale the action from [low, high] to [-1, 1]
        (no need for symmetric action space)

        :param action: Action to scale
        :return: Scaled action
        """
        return 2.0 * ((action - self.low) / (self.high - self.low)) - 1.0

    def _unscale_action(self, scaled_action: np.ndarray) -> np.ndarray:
        """
        Rescale the action from [-1, 1] to [low, high]
        (no need for symmetric action space)

        :param scaled_action: Action to un-scale
        """
        return self.low + (0.5 * (scaled_action + 1.0) * (self.high - self.low))

            
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
        if not self.is_inference: 
            execution_price = self.data['close'].iloc[self.current_step]
            return execution_price
        return 0

    def _calculate_transaction_cost(self, volume, daily_volume, volatility=None):
        if volatility is None:
            volatility = self.data['volatility'].iloc[self.current_step]
        return volatility * np.sqrt(volume / daily_volume)
    
    
    def calculate_vwap(self, bid_prices, bid_sizes):
        # VWAP calculation: sum(price * size) / sum(size)
        vwap = np.sum(bid_prices * bid_sizes) / np.sum(bid_sizes)
        return vwap
            
    def _calculate_reward(self, size_of_slice, timing_of_slice):
        # Constants
        kappa = 0.1
        order_size = size_of_slice
        time_remaining = self.preferred_timeframe - self.elapsed_time
        total_time = self.preferred_timeframe


        # Convert current_timestamp to datetime object
        # est_tz = pytz.timezone('America/New_York')
        current_timestamp = self.data['datetime'].iloc[self.current_step]
        timestamp = pd.to_datetime(current_timestamp)#.replace(tzinfo=est_tz)

        # Fetch expected price, bid_sizes, ask_sizes, and bid_prices from the Polygon API
        expected_price = self.data['expected_price_sell'].iloc[self.current_step]
        if expected_price is None:
            # print("Expected price couldn't be fetched, returning no reward.")
            return None

        spread_cost = self.data['spread_cost'].iloc[self.current_step]

        # Calculate VWAP based on bid prices and sizes
        actual_price = self.data['actual_price'].iloc[self.current_step]


        # Slippage: difference between expected price and actual execution price
        slippage = (expected_price - actual_price) * size_of_slice

        transaction_costs = self.data['transaction_cost'].iloc[self.current_step] 

        # # VWAP for opportunity cost calculation
        opportunity_cost = 0
        # if not hasattr(self, 'start_vwap_price'):
        #     self.start_vwap_price = self.data.iloc[0]['VWAP']
        # self.vwap_price_set_executed_prices.append(self.data.iloc[self.current_step]['VWAP'])
        # opportunity_cost = self.start_vwap_price - sum(self.vwap_price_set_executed_prices) / len(self.vwap_price_set_executed_prices)
        
        # if self.prev_step != self.current_step:
        #     opportunity_cost = self.data.iloc[self.prev_step:self.current_step]["VWAP"].mean() - self.data.iloc[self.current_step]["VWAP"]
        #     self.prev_step = self.current_step
        # Penalize actions taken early in the timeframe (encourage spreading actions)
        early_action_penalty = self.delta * (time_remaining / total_time) ** 2  # Quadratic scaling

        # Apply penalties based on scenario
        if self.scenario in ['small', 'small-medium']:
            small_timestep_penalty = 0 if timing_of_slice > 40 else 100
        elif self.scenario in ['medium', 'medium-large']:
            small_timestep_penalty = 0 if timing_of_slice > 20 else 50
        elif self.scenario == 'large':
            small_timestep_penalty = 0 if timing_of_slice > 10 else 10
        else:
            small_timestep_penalty = 0

        # Combine all the components to calculate the reward
        penalty = (slippage + transaction_costs + early_action_penalty + opportunity_cost+ small_timestep_penalty)

        # Adding utility theory in rewards
        reward = -penalty - (2 * kappa * (penalty ** 2))

        if math.isnan(reward):
            reward = self.min_reward
            slippage = 0
            transaction_costs = 0
            print("Reward is NaN!")
            print(f"Slippage: {slippage} TC: {transaction_costs} Rapid: {early_action_penalty} Time: {small_timestep_penalty}")
            print(f"Total time: {total_time} Time elapsed: {self.elapsed_time}, Time remaining: {time_remaining}, Time slice: {timing_of_slice}")
            print(f"Expected price: {expected_price}, Actual price: {actual_price}, Curent step: {self.current_step} Current Time: {timestamp}")
            print(f"Bid prices: {bid_prices}, Bid sizes: {bid_sizes}, ask prices: {ask_prices}, ask sizes: {ask_sizes}")
        return reward, slippage, transaction_costs

    def close(self):
        del self.data
        del self.trades
        del self.remaining_inventory
        del self.cumulative_reward
        del self.current_step

        self.observation_space = None
        self.action_space = None
    
    def render(self, mode='human', close=False):
        print('--------------------------------------------------')
        print(f'Steps: {self.current_step}')
        print(f'Remaining inventory: {self.remaining_inventory}')
        print(f'Cumulative reward: {self.cumulative_reward}')
        self.print_trades()
    
    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def print_trades(self):
        trades_df = pd.DataFrame(self.trades)
        for trade in self.trades:
            print(f"Step: {trade['step']}, Action: {trade['action']}, Price: {trade['price']}, Shares: {trade['shares']}, Reward: {trade['reward']}, Inventory: {trade['inventory']}, TimeLeft: {trade['time left']}")
        
        return self.trades

    def clip_reward(self, reward):
        return min(max(reward, self.min_reward), self.max_reward)

    def get_next_valid_market_timestamp(self, current_timestamp, time_slice_minutes):
        """
        Calculates the next valid market timestamp based on the current timestamp and time slice.

        Args:
        - current_timestamp (datetime, pd.Timestamp, or numpy.int64): Current market timestamp. ( Assuming the timestamp is in UTC )
        - time_slice_minutes (int): Minutes to add to the current timestamp.

        Returns:
        - datetime: The next valid market timestamp considering market hours, weekends, and holidays.
        """
        # Convert numpy.int64 (or any int) to datetime
        if isinstance(current_timestamp, (np.int64, int)):
            current_timestamp = datetime.utcfromtimestamp(current_timestamp)

        # Ensure current_timestamp is a single timestamp, not a DataFrame or Series
        if isinstance(current_timestamp, (pd.Series, pd.DataFrame)):
            current_timestamp = current_timestamp.squeeze()  # Convert to scalar if it's a Series with one element

        # Convert to datetime if it's a pandas Timestamp
        if isinstance(current_timestamp, pd.Timestamp):
            current_timestamp = current_timestamp.to_pydatetime()

        # Now it's safe to use replace
        market_start = current_timestamp.replace(hour=9, minute=30, second=0, microsecond=0)
        market_end = current_timestamp.replace(hour=16, minute=0, second=0, microsecond=0)

        # Add time slice to the current timestamp
        new_timestamp = current_timestamp + timedelta(minutes=time_slice_minutes)

        # If the new timestamp is beyond market hours
        if new_timestamp > market_end:
            # Move to the next market day's open
            new_timestamp = market_start + timedelta(days=1)

        # If the new timestamp is before market open, set it to the market start time
        if new_timestamp < market_start:
            new_timestamp = market_start

        # Skip weekends
        while new_timestamp.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            new_timestamp += timedelta(days=1)

        # Check if the new timestamp falls on a holiday
        cal = USFederalHolidayCalendar()
        holidays = cal.holidays(start=new_timestamp, end=new_timestamp + timedelta(days=365)).to_pydatetime()
        while new_timestamp in holidays:
            new_timestamp += timedelta(days=1)
            new_timestamp = new_timestamp.replace(hour=9, minute=30, second=0, microsecond=0)  # Reset to market open time

        return new_timestamp

# class TradingEnvironment_old_options(gym.Env):
#     metadata = {'render.modes': ['human']}
    
#     # Preferred timeframe: The number of steps that the user wants to complete the trade in
#     def __init__(self, data, action_space, preferred_timeframe=390, initial_inventory=10, scenario='medium', inference=False):
#         super(TradingEnvironment, self).__init__()
#         self.data = data
#         self.current_step = random.randint(0, len(self.data) - 1)
#         # self.prev_step = self.current_step
#         self.preferred_timeframe = preferred_timeframe
#         self.initial_inventory = initial_inventory
#         self.remaining_inventory = self.initial_inventory
#         self.elapsed_time = 0
#         self.trades = []
#         self.cumulative_reward = []
#         self.scenario = scenario
#         self.vwap_price_set_executed_prices =[]

#         # Define max and min rewards for clipping rewards, avoiding gradient overflow
#         self.max_reward = 1e12
#         self.min_reward = -1e12
        
#         # Define scenario-specific penalties
#         if self.scenario == 'large':
#             self.beta = 1
#             self.delta = 1
#         elif self.scenario == 'medium-large':
#             self.beta = 1e2
#             self.delta = 1e2
#         elif self.scenario == 'medium':
#             self.beta = 1e3
#             self.delta = 1e3
#         elif self.scenario == 'small-medium':
#             self.beta = 1e4
#             self.delta = 1e4
#         elif self.scenario == 'small':
#             self.beta = 1e5
#             self.delta = 1e5
#         else:
#             raise ValueError(f"Unknown scenario: {self.scenario}")

#         # Extract state columns - have to change according to requirement
#         self.state_columns = ['ask_price', 'ask_size', 'bid_price', 'bid_size', 'open', 'high', 'low',
#                                'close', 'volume', 'adj_close', 'time_to_maturity', 'mid_price', 'rfr',
#                                'implied_vol', 'delta', 'gamma', 'theta', 'vega', 'rho',
#                                'transaction_cost', 'forecast_3Hr_open', 'forecast_3Hr_high',
#                                'forecast_3Hr_low', 'forecast_3Hr_close',
#                                'forecast_3Hr_transaction_cost', 'forecast_3Hr_delta',
#                                'forecast_3Hr_gamma', 'forecast_3Hr_theta', 'forecast_3Hr_vega',
#                                'forecast_3Hr_rho', 'forecast_3Hr_implied_vol',
#                                'forecast_3Hr_time_to_maturity', 'forecast_3Hr_mid_price',
#                                'forecast_3Hr_rfr']

#         print("Length of state columns : ", len(self.state_columns))
        
#         # print("Initialized environment : State Columns : ", self.state_columns)
#         # Define action space - [%_slice, timing_of_next_slice] * Sequence_Length
#         self.action_space = action_space
#         self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(len(self.state_columns),), dtype=np.float32)

#         self.contract = self.data.iloc[0]["contract"]
#         self.is_inference = inference
#         self.timestamp = pd.to_datetime(self.data['timestamp'])
#         # random.seed(0)
#         self.seed(None)
    
#     def _get_state(self):
#         market_conditions = self._next_observation()
# #         state = np.append(market_conditions, self.remaining_inventory / self.initial_inventory)
#         return market_conditions
    
#     def _next_observation(self):
#         return self.data[self.state_columns].iloc[self.current_step].values
    
#     def reset(self, randomize=True):
#         # print('------------------------------------------------Class resetted------------------------------------------------')
#         if randomize:
#             self.current_step = random.randint(0, len(self.data) - 1)
#         else:
#             self.current_step = 0
#         self.cumulative_reward = []
#         self.remaining_inventory = self.initial_inventory
#         self.elapsed_time = 0
#         self.trades = []
#         # self.prev_step = self.current_step
#         if self.is_inference:
#             self.timestamp = pd.to_datetime(self.data.iloc[0]['timestamp'])
#         else:
#             self.timestamp = pd.to_datetime(self.data.iloc[self.current_step]['timestamp'])
#         return self._get_state()
    
#     def step(self, action):
#         # Adding some noise to the actions
#         action = self._add_noise_to_action(action)
#         # print(f'Action taken: {action}')

#         size_of_slice = action[0] * self.remaining_inventory
#         # Convert size of slice into whole number
#         size_of_slice = int(np.ceil(size_of_slice))

#         # Scale action[1] to a desired range, e.g., 1 to 10
#         timing_of_slice = int(np.ceil(action[1]))
#         # print(f'timing_of_slice: {timing_of_slice}')
        
#         self.elapsed_time += timing_of_slice
        
#         if self.elapsed_time >= self.preferred_timeframe:
#             size_of_slice = self.remaining_inventory

#         execution_price = self._take_action(size_of_slice)

#         # Print current and next step for debugging
#         # print(f'Current step: {self.current_step}')
#         self.current_step += timing_of_slice
#         # print(f'Next step: {self.current_step}')

#         # Ensure the index is sequential
#         # if self.current_step >= len(self.data):
#         #     self.current_step = len(self.data) - 1

#         truncated = False
#         done = self.remaining_inventory <= 0 or self.elapsed_time >= self.preferred_timeframe 
        
#         if not self.is_inference:
#             done = done or self.current_step >= len(self.data)
#             if self.current_step >= len(self.data):
#                 self.current_step = len(self.data) - 1
#             # print(f'Current step: {self.current_step}',file=sys.stderr)
#             rewards_data = self._calculate_reward(size_of_slice, execution_price, timing_of_slice)
#             while rewards_data is None:
#                 self.current_step += 1
#                 if self.current_step >= len(self.data):
#                     break
#                 rewards_data = self._calculate_reward(size_of_slice, execution_price, timing_of_slice)
                
            
#             if rewards_data is not None:
#                 reward, slippage, transaction_Costs = rewards_data  
#                 reward = self.clip_reward(reward)
#                 self.cumulative_reward.append(reward)
#             else:
#                 # current_timestamp = pd.to_datetime(self.data.iloc[self.current_step]['timestamp'])
#                 # next_timestamp = self.get_next_valid_market_timestamp(current_timestamp, timing_of_slice)
                
#                 reward, slippage, transaction_Costs = sum(self.cumulative_reward)/len(self.cumulative_reward) if len(self.cumulative_reward) > 0 else self.min_reward, 0, 0
#                 self.remaining_inventory += size_of_slice
#                 truncated = True
#                 done = True
#             # if done:
#             #     print(f'Cumulative Rewards: {self.cumulative_reward}')

#             trade_info = {
#                     'step': self.current_step,
#                     'timestamp': self.data.index[self.current_step],
#                     'action': action,
#                     'price': execution_price,
#                     'shares': size_of_slice,
#                     'reward': reward,
#                     'slippage' : slippage,
#                     'transaction_cost' : transaction_Costs,
#                     'inventory': self.remaining_inventory,
#                     'time left': self.preferred_timeframe - self.elapsed_time
#                 }
#         else:
#             current_timestamp = self.timestamp
#             next_timestamp = self.get_next_valid_market_timestamp(current_timestamp, timing_of_slice)
#             # print("current timestamp : ", current_timestamp, " next timestamp : ", next_timestamp)
#             trade_info = {
#                 'timestamp': next_timestamp,
#                 'action': action,
#                 'shares': size_of_slice,
#                 'inventory': self.remaining_inventory,
#                 'time left': self.preferred_timeframe - self.elapsed_time
#             }
#             self.timestamp = next_timestamp

        
#         self.trades.append(trade_info)

#         info = {
#             'step': self.current_step,
#             'action': action,
#             'price': execution_price
#         }
#         # print(f'Remaining inventory: {self.remaining_inventory}, Cumulative reward: {self.cumulative_reward}, shares: {size_of_slice}, timing of slice: {timing_of_slice}, done: {done}')
#         if self.is_inference:
#             return done, info
        
#         return self._get_state(), reward, done, info

            
#     def _add_noise_to_action(self, action):
#         # Add noise to the first action (percentage of inventory)
#         noise_action_0 = np.random.normal(0, 0.02, size=action[0].shape)  # Small noise for percentage
#         action[0] += noise_action_0
#         action[0] = np.clip(action[0], self.action_space.low[0], self.action_space.high[0])

#         # Add noise to the second action (timing of next slice)
#         noise_action_1 = np.random.normal(0, 5, size=action[1].shape)  # Setting SD to be 5% of the range (1-100)
#         action[1] += noise_action_1
#         action[1] = np.clip(action[1], self.action_space.low[1], self.action_space.high[1])

#         return action

    
#     def _take_action(self, size_of_slice):
#         self.remaining_inventory -= size_of_slice
#         # print(f'Remaining inventory: {self.remaining_inventory}')
#         if self.remaining_inventory < 0:
#             self.remaining_inventory = 0
#         if not self.is_inference: 
#             execution_price = self.data['close'].iloc[self.current_step]
#             return execution_price
#         return 0

#     def _calculate_transaction_cost(self, volume, daily_volume, volatility=None):
#         if volatility is None:
#             volatility = self.data['volatility'].iloc[self.current_step]
#         return volatility * np.sqrt(volume / daily_volume)
    
    
    
#     def get_expected_price(self, contract, timestamp):
#         # Initialize the client with your API key
#         # client = RESTClient(api_key)

#         # Convert timestamp to nanoseconds
#         end_timestamp = int(timestamp.timestamp() * 1_000_000_000)
#         start_timestamp = end_timestamp - (60 * 1_000_000_000)  # Subtract 1 minute from the timestamp for start time

#         client = db.Historical(databento_api_key)

#         data = client.timeseries.get_range(
#             dataset="OPRA.PILLAR", # for stocks which require MBO
#             schema="mbp-1",
#             stype_in="raw_symbol",
#             symbols=[contract],
#             start=start_timestamp,
#             end=end_timestamp,

#         )
#         df = data.to_df()
#         df.dropna(inplace=True)
#         # print(df.head())

#         # # Make the API call
#         # quotes = client.list_quotes(
#         #     contract,
#         #     timestamp_gte=start_timestamp,
#         #     timestamp_lte=end_timestamp,
#         #     limit=50000  # Adjust based on your needs
#         # )

#         # # Initialize variables to store maximum bid price and sizes
#         max_bid_price = float('-inf')
#         bid_sizes = []
#         ask_sizes = []
#         bid_prices = []
#         ask_prices = []
#         quotes = []
#         for index, row in df.iterrows():
#             bid_prices.append(row['bid_px_00'])
#             bid_sizes.append(row['bid_sz_00']*100)
#             ask_sizes.append(row['ask_sz_00']*100)
#             ask_prices.append(row['ask_px_00'])
#             if row['bid_px_00'] > max_bid_price:
#                 max_bid_price = row['bid_px_00']


#         # Check if max_bid_price was updated, otherwise handle no data case
#         if max_bid_price == float('-inf'):
#             print(f"No bid prices found for the given timestamp: {timestamp}")
#             print(f"{start_timestamp}, {end_timestamp}, {contract}")
#             return None, None, None, None, None
#         bid_prices = np.array(bid_prices)
#         bid_sizes = np.array(bid_sizes)
#         ask_sizes = np.array(ask_sizes)
#         ask_prices = np.array(ask_prices)

#         return max_bid_price, bid_sizes, ask_sizes, bid_prices, ask_prices
    
    
#     def calculate_vwap(self, bid_prices, bid_sizes):
#         # VWAP calculation: sum(price * size) / sum(size)
#         vwap = np.sum(bid_prices * bid_sizes) / np.sum(bid_sizes)
#         return vwap
            
#     def _calculate_reward(self, size_of_slice, execution_price, timing_of_slice):
#         # Constants
#         kappa = 0.1
#         order_size = size_of_slice
#         time_remaining = self.preferred_timeframe - self.elapsed_time
#         total_time = self.preferred_timeframe


#         # Convert current_timestamp to datetime object
#         # est_tz = pytz.timezone('America/New_York')
#         current_timestamp = self.data['datetime'].iloc[self.current_step]
#         timestamp = pd.to_datetime(current_timestamp)#.replace(tzinfo=est_tz)

#         # Fetch expected price, bid_sizes, ask_sizes, and bid_prices from the Polygon API
#         # expected_price, bid_sizes, ask_sizes, bid_prices, ask_prices = self.get_expected_price(self.contract, timestamp)
#         expected_price = self.data['expected_price'].iloc[self.current_step]
#         if expected_price is None:
#             # print("Expected price couldn't be fetched, returning no reward.")
#             return None

#         spread_cost = self.data['spread_cost'].iloc[self.current_step]

#         # if len(bid_sizes) != 0:
#             # spread_cost = np.min(ask_prices) - np.max(bid_prices)
#         # else:
#         #     spread_cost = 0
#         # Calculate VWAP based on bid prices and sizes
#         # actual_price = self.calculate_vwap(bid_prices, bid_sizes)
#         actual_price = self.data['actual_price'].iloc[self.current_step]


#         # Slippage: difference between expected price and actual execution price
#         slippage = (expected_price - actual_price) * size_of_slice

#         transaction_costs = self.data['transaction_cost'].iloc[self.current_step] 

#         # # VWAP for opportunity cost calculation
#         opportunity_cost = 0
#         if not hasattr(self, 'start_vwap_price'):
#             self.start_vwap_price = self.data.iloc[0]['VWAP']
#         self.vwap_price_set_executed_prices.append(self.data.iloc[self.current_step]['VWAP'])
#         opportunity_cost = self.start_vwap_price - sum(self.vwap_price_set_executed_prices) / len(self.vwap_price_set_executed_prices)
        
#         # if self.prev_step != self.current_step:
#         #     opportunity_cost = self.data.iloc[self.prev_step:self.current_step]["VWAP"].mean() - self.data.iloc[self.current_step]["VWAP"]
#         #     self.prev_step = self.current_step
#         # Penalize actions taken early in the timeframe (encourage spreading actions)
#         early_action_penalty = self.delta * (time_remaining / total_time) ** 2  # Quadratic scaling

#         # Apply penalties based on scenario
#         if self.scenario in ['small', 'small-medium']:
#             small_timestep_penalty = 0 if timing_of_slice > 40 else 100
#         elif self.scenario in ['medium', 'medium-large']:
#             small_timestep_penalty = 0 if timing_of_slice > 20 else 50
#         elif self.scenario == 'large':
#             small_timestep_penalty = 0 if timing_of_slice > 10 else 10
#         else:
#             small_timestep_penalty = 0

#         # Combine all the components to calculate the reward
#         penalty = (slippage + transaction_costs + early_action_penalty + opportunity_cost+ small_timestep_penalty)

#         # Adding utility theory in rewards
#         reward = -penalty - (2 * kappa * (penalty ** 2))

#         if math.isnan(reward):
#             reward = self.min_reward
#             slippage = 0
#             transaction_costs = 0
#             print("Reward is NaN!")
#             print(f"Slippage: {slippage} TC: {transaction_costs} Rapid: {early_action_penalty} Time: {small_timestep_penalty}")
#             print(f"Total time: {total_time} Time elapsed: {self.elapsed_time}, Time remaining: {time_remaining}, Time slice: {timing_of_slice}")
#             print(f"Expected price: {expected_price}, Actual price: {actual_price}, Curent step: {self.current_step} Current Time: {timestamp}")
#             print(f"Bid prices: {bid_prices}, Bid sizes: {bid_sizes}, ask prices: {ask_prices}, ask sizes: {ask_sizes}")
#         return reward, slippage, transaction_costs

#     def close(self):
#         del self.data
#         del self.trades
#         del self.remaining_inventory
#         del self.cumulative_reward
#         del self.current_step

#         self.observation_space = None
#         self.action_space = None
    
#     def render(self, mode='human', close=False):
#         print('--------------------------------------------------')
#         print(f'Steps: {self.current_step}')
#         print(f'Remaining inventory: {self.remaining_inventory}')
#         print(f'Cumulative reward: {self.cumulative_reward}')
#         self.print_trades()
    
#     def seed(self, seed=None):
#         self.np_random, seed = seeding.np_random(seed)
#         return [seed]

#     def print_trades(self):
#         trades_df = pd.DataFrame(self.trades)
#         for trade in self.trades:
#             print(f"Step: {trade['step']}, Action: {trade['action']}, Price: {trade['price']}, Shares: {trade['shares']}, Reward: {trade['reward']}, Inventory: {trade['inventory']}, TimeLeft: {trade['time left']}")
        
#         return self.trades

#     def clip_reward(self, reward):
#         return min(max(reward, self.min_reward), self.max_reward)

#     def get_next_valid_market_timestamp(self, current_timestamp, time_slice_minutes):
#         """
#         Calculates the next valid market timestamp based on the current timestamp and time slice.

#         Args:
#         - current_timestamp (datetime, pd.Timestamp, or numpy.int64): Current market timestamp. ( Assuming the timestamp is in UTC )
#         - time_slice_minutes (int): Minutes to add to the current timestamp.

#         Returns:
#         - datetime: The next valid market timestamp considering market hours, weekends, and holidays.
#         """
#         # Convert numpy.int64 (or any int) to datetime
#         if isinstance(current_timestamp, (np.int64, int)):
#             current_timestamp = datetime.utcfromtimestamp(current_timestamp)

#         # Ensure current_timestamp is a single timestamp, not a DataFrame or Series
#         if isinstance(current_timestamp, (pd.Series, pd.DataFrame)):
#             current_timestamp = current_timestamp.squeeze()  # Convert to scalar if it's a Series with one element

#         # Convert to datetime if it's a pandas Timestamp
#         if isinstance(current_timestamp, pd.Timestamp):
#             current_timestamp = current_timestamp.to_pydatetime()

#         # Now it's safe to use replace
#         market_start = current_timestamp.replace(hour=9, minute=30, second=0, microsecond=0)
#         market_end = current_timestamp.replace(hour=16, minute=0, second=0, microsecond=0)

#         # Add time slice to the current timestamp
#         new_timestamp = current_timestamp + timedelta(minutes=time_slice_minutes)

#         # If the new timestamp is beyond market hours
#         if new_timestamp > market_end:
#             # Move to the next market day's open
#             new_timestamp = market_start + timedelta(days=1)

#         # If the new timestamp is before market open, set it to the market start time
#         if new_timestamp < market_start:
#             new_timestamp = market_start

#         # Skip weekends
#         while new_timestamp.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
#             new_timestamp += timedelta(days=1)

#         # Check if the new timestamp falls on a holiday
#         cal = USFederalHolidayCalendar()
#         holidays = cal.holidays(start=new_timestamp, end=new_timestamp + timedelta(days=365)).to_pydatetime()
#         while new_timestamp in holidays:
#             new_timestamp += timedelta(days=1)
#             new_timestamp = new_timestamp.replace(hour=9, minute=30, second=0, microsecond=0)  # Reset to market open time

#         return new_timestamp