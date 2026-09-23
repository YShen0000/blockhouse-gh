import gym
from gym import spaces
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from datetime import datetime, timedelta
import pytz
import databento as db
import math
import random
from polygon import RESTClient
from gym import Env


class CustomTradingEnvironment(gym.Env):
    metadata = {'render.modes': ['human']}
    
    def __init__(self, data, scenario, action_space,original_action_space, preferred_timeframe=390, target_shares=10):
        """
        Initializes the Custom Trading Environment for buying shares.

        Args:
        - data (pd.DataFrame): Current input data row.
        - scenario (dict): Contains any scenario-specific parameters.
        - action_space (gym.spaces): The action space for the agent.
        - preferred_timeframe (int, optional): The number of steps in which the trade should be completed (default is 390).
        - target_shares (int, optional): Target number of shares to be bought (default is 10).

        Returns:
        - None
        """
        super(CustomTradingEnvironment, self).__init__()
        self.data = data        
        self.preferred_timeframe = preferred_timeframe
        self.target_shares = target_shares
        self.shares_bought = 0
        self.elapsed_time = 0
        self.trades = []
        self.timestamp = pd.to_datetime(self.data['timestamp'], unit='ms').iloc[0]

        # State columns contain market data and technical indicators
        self.state_columns = ['open', 'high', 'low', 'close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist', 
                              'Stoch_k', 'Stoch_d', 'OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 'ATR_1', 'ADX', 
                              '+DI', '-DI', 'CCI', 'transaction_cost', 'forecast_6Hr_open','forecast_6Hr_close',
                              'forecast_6Hr_high','forecast_6Hr_low', 'forecast_6Hr_volatility', 
                              'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost']
        
        # Define the action space and observation space for the environment
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
        # print(f"low {self.low}")
        # print(f"high{self.high}")
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(45,), dtype=np.float32)
        
    def reset(self):
        """
        Resets the environment to its initial state at the beginning of a new episode.

        Returns:
        - pd.Series: The last row of the data as the initial state.
        """
        print('------------------------------------------------Class resetted------------------------------------------------')
        self.shares_bought = 0
        self.elapsed_time = 0
        self.trades = []
        row_values = self.data.iloc[-1][self.state_columns].values
        state = self.data[self.state_columns].iloc[-1].values
        return state
    
    def get_next_valid_market_timestamp(self, current_timestamp, time_slice_minutes):
        """
        Calculates the next valid market timestamp based on the current timestamp and time slice.

        Args:
        - current_timestamp (datetime, pd.Timestamp, or numpy.int64): Current market timestamp.
        - time_slice_minutes (int): Minutes to add to the current timestamp.

        Returns:
        - datetime: The next valid market timestamp considering market hours, weekends, and holidays.
        """
        # Convert numpy.int64 (or any int) to datetime
        if isinstance(current_timestamp, (np.int64, int)):
            current_timestamp = pd.to_datetime(current_timestamp, unit='ms')

        # Ensure current_timestamp is a single timestamp, not a DataFrame or Series
        if isinstance(current_timestamp, (pd.Series, pd.DataFrame)):
            current_timestamp = current_timestamp.squeeze()  # Convert to scalar if it's a Series with one element

        # Convert to datetime if it's a pandas Timestamp
        if isinstance(current_timestamp, pd.Timestamp):
            current_timestamp = current_timestamp.to_pydatetime()

        # Define market hours (assumed to be 9:30 AM to 4:00 PM)
        market_start = current_timestamp.replace(hour=9, minute=30, second=0, microsecond=0)
        market_end = current_timestamp.replace(hour=16, minute=0, second=0, microsecond=0)

        # Add the time slice to the current timestamp
        new_timestamp = current_timestamp + timedelta(minutes=time_slice_minutes)

        # If the new timestamp exceeds market hours, move to the next day's open
        if new_timestamp > market_end:
            new_timestamp = market_start + timedelta(days=1)

        # If the new timestamp is before market open, set it to the market start time
        if new_timestamp < market_start:
            new_timestamp = market_start

        # Skip weekends (Saturday and Sunday)
        while new_timestamp.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            new_timestamp += timedelta(days=1)

        # Check for holidays and move to the next valid day if necessary
        cal = USFederalHolidayCalendar()
        holidays = cal.holidays(start=new_timestamp, end=new_timestamp + timedelta(days=365)).to_pydatetime()
        while new_timestamp in holidays:
            new_timestamp += timedelta(days=1)
            new_timestamp = new_timestamp.replace(hour=9, minute=30, second=0, microsecond=0)  # Reset to market open time

        return new_timestamp
    def _unscale_action(self, scaled_action: np.ndarray) -> np.ndarray:
        """
        Rescale the action from [-1, 1] to [low, high]
        (no need for symmetric action space)

        :param scaled_action: Action to un-scale
        """
        return self.low + (0.5 * (scaled_action + 1.02) * (self.high - self.low))
    
    def step(self, action):
        """
        Executes a step in the environment by performing the action provided by the agent.

        Args:
        - action (np.array): An array where action[0] is the percentage of shares to buy and action[1] is the timing of the next trade.

        Returns:
        - bool: Whether the episode is done (i.e., target shares bought or time is up).
        - dict: Additional information about the step taken.
        """
        # print("In step functions")
        # Adding some noise to the actions
        # action = self._add_noise_to_action(action)
        action = self._unscale_action(action)
        # print(f"action for the step{action}")

        # Calculate the size of the slice to buy
        size_of_slice = action[0] * (self.target_shares - self.shares_bought)
        size_of_slice = int(np.ceil(size_of_slice))

        # Scale action[1] to a desired range, e.g., 1 to 10
        timing_of_slice = int(np.ceil(action[1]))

        self.elapsed_time += timing_of_slice

        # If time is running out, buy the remaining shares
        if self.elapsed_time >= self.preferred_timeframe:
            size_of_slice = self.target_shares - self.shares_bought

        # Take action
        self.shares_bought += size_of_slice

        # Check if the episode is done
        done = self.shares_bought >= self.target_shares or self.elapsed_time >= self.preferred_timeframe

        # Calculate the time left and ensure it doesn't go negative
        time_left = max(0, self.preferred_timeframe - self.elapsed_time)

        # Record trade details
        trade_info = {
            'timestamp': self.timestamp,
            'action': action,
            'shares': size_of_slice,
            'inventory': self.shares_bought,
            'time left': time_left  # Ensure time left doesn't go negative
        }
        self.trades.append(trade_info)

        # Get the next market timestamp
        next_timestamp = self.get_next_valid_market_timestamp(self.timestamp, timing_of_slice)
        self.timestamp = next_timestamp

        info = {
            'step': next_timestamp,
            'action': action,
        }

        return done, info


    def _add_noise_to_action(self, action):
        """
        Adds noise to the agent's actions to simulate real-world uncertainties.

        Args:
        - action (np.array): An array containing the actions from the agent.

        Returns:
        - np.array: The action array with added noise.
        """
        # Add noise to the first action (percentage of inventory)
        noise_action_0 = np.random.normal(0, 0.02, size=action[0].shape)  # Small noise for percentage
        action[0] += noise_action_0
        action[0] = np.clip(action[0], self.action_space.low[0], self.action_space.high[0])

        # Add noise to the second action (timing of next slice)
        noise_action_1 = np.random.normal(0, 5, size=action[1].shape)  # Setting SD to be 5% of the range (1-100)
        action[1] += noise_action_1
        action[1] = np.clip(action[1], self.action_space.low[1], self.action_space.high[1])

        return action

    def render(self, mode='human', close=False):
        """
        Renders the current state of the environment, including all trades executed so far.

        Args:
        - mode (str, optional): The mode of rendering (default is 'human').
        - close (bool, optional): Whether to close the render window (default is False).

        Returns:
        - None
        """
        print('--------------------------------------------------')
        self.print_trades()

    def print_trades(self):
        """
        Prints a summary of all trades executed so far.

        Returns:
        - list: A list of dictionaries, each containing details of a trade.
        """
        trades_df = pd.DataFrame(self.trades)
        for trade in self.trades:
            print(f"Timestamp: {trade['timestamp']}, Action: {trade['action']}, Shares: {trade['shares']}, Inventory: {trade['inventory']}, TimeLeft: {trade['time left']}")
        
        return self.trades




        
        
        
class TradingEnvironmentMacroV2(gym.Env):
    metadata = {'render.modes': ['human']}

    # Preferred timeframe: The number of steps that the user wants to complete the trade in
    def __init__(self, data, action_space,original_action_space, preferred_timeframe=390, target_shares=10, scenario='medium'):
        super(TradingEnvironmentMacroV2, self).__init__()
        self.data = data
        self.current_step = 0
        # self.epsilon = 1.0  # Initial exploration rate
        # self.epsilon_decay = 0.99  # Epsilon decay rate
        # self.epsilon_min = 0.05  # Minimum exploration rate
        # # self.original_action_space = action_space
        self.preferred_timeframe = preferred_timeframe
        self.target_shares = target_shares  # Total shares to buy
        self.shares_bought = 0  # Accumulated shares
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

        # Extract state columns - Modify according to your data and indicators
        self.state_columns = ['open', 'high', 'low', 'close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist',
                              'Stoch_k', 'Stoch_d', 'OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 'ATR_1', 'ADX',
                              '+DI', '-DI', 'CCI', 'transaction_cost', 'forecast_6Hr_open', 'forecast_6Hr_close',
                              'forecast_6Hr_high', 'forecast_6Hr_low', 'forecast_6Hr_volatility', 'forecast_6Hr_volume',
                              'forecast_6Hr_transaction_cost']

        # Define action space - [%_slice, timing_of_next_slice] * Sequence_Length
        # self.action_space = action_space
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
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(len(self.state_columns),),
                                            dtype=np.float32)
        
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


    def _get_state(self):
        market_conditions = self._next_observation()
        return market_conditions

    def _next_observation(self):
        return self.data[self.state_columns].iloc[self.current_step].values

    def reset(self):
        self.current_step = random.randint(0,500) 
        self.cumulative_reward = 0
        self.shares_bought = 0  # Reset accumulated shares
        self.elapsed_time = 0
        self.trades = []
        return self._get_state()

    def step(self, action):
        # Adding some noise to the actions
        action = self._add_noise_to_action(action)
        action = self._unscale_action(action)
        # if np.random.rand() < self.epsilon:
        #     print("Taking random action (epsilon-greedy)")
        #     action = self.action_space.sample()  # Take a random action
        # else:
        # action = self._add_noise_to_action(action)  # Take the predicted action with added noise

        # Decay epsilon after each step (gradually shift from exploration to exploitation)
        # self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        

        # Calculate the size of the slice to buy
        size_of_slice = action[0] * (self.target_shares - self.shares_bought)
        size_of_slice = int(np.ceil(size_of_slice))

        # Scale action[1] to a desired range, e.g., 1 to 10
        timing_of_slice = int(np.ceil(action[1]))

        self.elapsed_time += timing_of_slice

        # If time is running out, buy the remaining shares
        if self.elapsed_time >= self.preferred_timeframe:
            size_of_slice = self.target_shares - self.shares_bought

        # Update the accumulated shares
        self.shares_bought += size_of_slice

        # If accumulated shares reach the target, cap it
        if self.shares_bought >= self.target_shares:
            self.shares_bought = self.target_shares

        # Execute the trade and get the execution price
        execution_price = self._take_action(size_of_slice)

        self.current_step += timing_of_slice

        # Ensure the index is sequential
        if self.current_step >= len(self.data):
            self.current_step = len(self.data) - 1

        # Check if the episode is done
        done = self.shares_bought >= self.target_shares or self.elapsed_time >= self.preferred_timeframe

        # Calculate the reward
        reward, slippage, transaction_costs, opportunity_cost = self._calculate_reward(size_of_slice, execution_price, timing_of_slice)
        self.cumulative_reward += reward

        # Record the trade
        trade_info = {
            'step': self.current_step,
            'action': action,
            'price': execution_price,
            'shares': size_of_slice,
            'timestamp': self.data['datetime'].iloc[self.current_step],
            'reward': reward,
            'slippage': slippage,
            'transaction_cost': transaction_costs,
            'opportunity_cost': opportunity_cost,
            'inventory': self.shares_bought,  # Updated to show accumulated shares
            'time left': self.preferred_timeframe - self.elapsed_time,
        }
        self.trades.append(trade_info)

        info = {
            'step': self.current_step,
            'action': action,
            'price': execution_price
        }

        return self._get_state(), reward, done, info

    def _add_noise_to_action(self, action):
        # Add noise to the first action (percentage of target shares)
        noise_action_0 = np.random.normal(0, 0.02, size=action[0].shape)  # Small noise for percentage
        action[0] += noise_action_0
        action[0] = np.clip(action[0], self.action_space.low[0], self.action_space.high[0])

        # Add noise to the second action (timing of next slice)
        noise_action_1 = np.random.normal(0, 5, size=action[1].shape)  # Setting SD to be 5% of the range (1-100)
        action[1] += noise_action_1
        action[1] = np.clip(action[1], self.action_space.low[1], self.action_space.high[1])

        return action

    def _take_action(self, size_of_slice):
        self.shares_bought += size_of_slice
        if self.shares_bought > self.target_shares:
            self.shares_bought = self.target_shares
        execution_price = self.data['close'].iloc[self.current_step] 
        return execution_price
    
    def _take_action_v2(self, size_of_slice):
        if size_of_slice >= self.remaining_inventory:
            size_of_slice = self.remaining_inventory
        self.remaining_inventory -= size_of_slice
        print(f'Remaining inventory: {self.remaining_inventory}')
        execution_price = self.data['close'].iloc[self.current_step]
        return execution_price, size_of_slice

    
    def _calculate_transaction_cost(self, volume, daily_volume, volatility=None):
        if volatility is None:
            volatility = self.data['volatility'].iloc[self.current_step]
        return volatility * np.sqrt(volume / daily_volume)
    

    
    
    def get_expected_price(self, api_key, symbol, timestamp):
        # Initialize the client with your API key
        client = db.Historical(api_key)
        # print(timestamp)
        # Convert timestamp to nanoseconds
        end_timestamp = int(timestamp.timestamp() * 1_000_000_000)
        start_timestamp = end_timestamp - (60 * 1_000_000_000)  # Subtract 1 minute from the timestamp for start time

        # Convert timestamps to datetime strings for the query
        # start_date = datetime.utcfromtimestamp(start_timestamp / 1_000_000_000).strftime('%Y-%m-%dT%H:%M:%SZ')
        # end_date = datetime.utcfromtimestamp(end_timestamp / 1_000_000_000).strftime('%Y-%m-%dT%H:%M:%SZ')

        try:
            # Fetching Market by Price (MBP) data
            data = client.timeseries.get_range(
                dataset="XNAS.ITCH",  # Correct dataset for NASDAQ equities
                schema="mbp-1",       # Schema for Market by Price, top level only
                symbols=[symbol],
                start=start_timestamp,
                end=end_timestamp,
            )

            # Convert the data to a pandas DataFrame for processing
            df_mbp = data.to_df()

            if df_mbp.empty:
                print(f"No data found for the given timestamp: {timestamp}")
                return None, None, None, None, None, None

            # Drop rows with NaN values in the relevant columns
            df_mbp_cleaned = df_mbp.dropna(subset=['bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00'])

            if df_mbp_cleaned.empty:
                print(f"All data rows contained NaN values and were dropped for the given timestamp: {timestamp}")
                return None, None, None, None, None, None

            # Initialize variables to store maximum bid price and minimum ask price, and their sizes
            max_bid_price = float('-inf')
            min_ask_price = float('inf')
            bid_sizes = []
            ask_sizes = []
            bid_prices = []
            ask_prices = []

            # Process the cleaned data to find the maximum bid price and collect sizes
            for index, row in df_mbp_cleaned.iterrows():
                if row['bid_px_00'] > max_bid_price:
                    max_bid_price = row['bid_px_00']
                if row['ask_px_00'] < min_ask_price:
                    min_ask_price = row['ask_px_00']

                bid_prices.append(row['bid_px_00'])
                bid_sizes.append(row['bid_sz_00']*100)
                ask_prices.append(row['ask_px_00'] )
                ask_sizes.append(row['ask_sz_00'] *100)

            # Check if max_bid_price was updated, otherwise handle no data case
            if max_bid_price == float('-inf') or min_ask_price == float('inf'):
                print(f"No valid bid or ask prices found after cleaning the data for the given timestamp: {timestamp}")
                return None, None, None, None, None, None

            return max_bid_price, min_ask_price, bid_sizes, ask_sizes, bid_prices, ask_prices

        except Exception as e:
            print(f"An error occurred: {e}")
            return None, None, None, None, None, None
    
    
    @staticmethod
    def calculate_vwap(bid_prices, bid_sizes, size_of_slice):
        # VWAP calculation: sum(price * size) / sum(size)
        cum_sum_size = 0
        for idx, size in enumerate(bid_sizes):
            # print(idx)
            cum_sum_size += size
            if cum_sum_size >= size_of_slice:
                break

        # Only consider elements before order is filled
        bid_prices = np.array(bid_prices[:idx+1])
        bid_sizes = np.array(bid_sizes[:idx+1])

        # Ensure bid_sizes is not zero to avoid division by zero
        if np.sum(bid_sizes) == 0:
            print("ask_size zero")
            return 0.0  # Handle edge case

        vwap = np.sum(bid_prices * bid_sizes) / np.sum(bid_sizes)
        # print(f"Calculated VWAP: {vwap}")
        return vwap

    
    
    
    def _calculate_reward(self, size_of_slice, execution_price, timing_of_slice):
        # Constants
        kappa = 0.1
        order_size = size_of_slice
        market_liquidity = self.data['market_liquidity'].iloc[self.current_step]
        time_remaining = self.preferred_timeframe - self.elapsed_time
        total_time = self.preferred_timeframe
        api_key = 'db-s8TQsSX8JF539yQSeBWFGPNyDx4m3'#'r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc'

        # Convert current timestamp to datetime object
        current_timestamp = self.data['datetime'].iloc[self.current_step]
        timestamp = pd.to_datetime(current_timestamp).replace(tzinfo=pytz.UTC)
        # curr_ticker =self.data['ticker'].iloc[self.current_step]
        curr_ticker = 'AAPL'
        # Fetch expected price, bid_sizes, ask_sizes, and bid_prices from the Polygon API
        max_bid_price, min_ask_price, bid_sizes, ask_sizes, bid_prices, ask_prices = self.get_expected_price(api_key,curr_ticker,timestamp)

        expected_price = min_ask_price

        if expected_price is None:
            print("Expected price couldn't be fetched, returning no reward.")
            return 0, 0, 0, 0
        else:
            avg_bid_price = sum(bid_prices) / len(bid_prices) if bid_prices else 0

            # Calculate the average ask price
            avg_ask_price = sum(ask_prices) / len(ask_prices) if ask_prices else 0

            spread_cost = (avg_ask_price - avg_bid_price) * size_of_slice
            # spread_cost = (min_ask_price - max_bid_price) * size_of_slice

        # Calculate VWAP based on bid prices and sizes
        # print(ask_sizes)
        actual_price = self.calculate_vwap(ask_prices, ask_sizes, size_of_slice)

        # Slippage: difference between expected price and actual execution price
        slippage = (actual_price - expected_price) * size_of_slice

        # Transaction costs (referred to as Price Impact)
        transaction_costs = self.data['transaction_cost'].iloc[self.current_step]# * size_of_slice

        # VWAP for opportunity cost calculation
        if not hasattr(self, 'start_vwap_price'):
            self.start_vwap_price = self.data.iloc[0]['VWAP']
        self.vwap_price_set_executed_prices.append(self.data.iloc[self.current_step]['VWAP'])
        # opportunity_cost = (self.start_vwap_price - sum(self.vwap_price_set_executed_prices) / len(
        #     self.vwap_price_set_executed_prices))* size_of_slice
        opportunity_cost = ((sum(self.vwap_price_set_executed_prices) / len(
            self.vwap_price_set_executed_prices)) - self.start_vwap_price)* size_of_slice

        # Penalize actions taken early in the timeframe (encourage spreading actions)
        early_action_penalty = self.delta * (time_remaining / total_time) ** 2  # Quadratic scaling

        # Apply penalties based on scenario
        # if self.scenario in ['small', 'small-medium']:
        #     small_timestep_penalty = 0 if timing_of_slice > 40 else 100
        # elif self.scenario in ['medium', 'medium-large']:
        #     small_timestep_penalty = 0 if timing_of_slice > 20 else 50
        # elif self.scenario == 'large':
        #     small_timestep_penalty = 0 if timing_of_slice > 10 else 10
        # else:
        #     small_timestep_penalty = 0

        # Combine all the components to calculate the reward
        penalty = (
                    slippage + transaction_costs + early_action_penalty + opportunity_cost + spread_cost)# + small_timestep_penalty

        # Adding utility theory in rewards
        reward = -penalty - (2 * kappa * (penalty ** 2))
        if math.isnan(reward):
            print("Reward is NaN!")
            print(f"Slippage: {slippage}, Transaction Costs: {transaction_costs}, Early Action Penalty: {early_action_penalty}")
            print(f"Opportunity Cost: {opportunity_cost}, Small Timestep Penalty: {small_timestep_penalty}, Spread Cost: {spread_cost}")
            print(f"Total Time: {total_time}, Time Elapsed: {self.elapsed_time}, Time Remaining: {time_remaining}")
            print(f"Expected Price: {expected_price}, Actual Price: {actual_price}")
            print(f"Current Step: {self.current_step}, Current Time: {timestamp}")
            print(f"Bid Prices: {bid_prices}, Bid Sizes: {bid_sizes}, Ask Prices: {ask_prices}, Ask Sizes: {ask_sizes}")

        return reward, slippage, transaction_costs, opportunity_cost

    def render(self, mode='human', close=False):
        print('--------------------------------------------------')
        print(f'Steps: {self.current_step}')
        print(f'Shares Bought: {self.shares_bought}')
        print(f'Cumulative reward: {self.cumulative_reward}')
        self.print_trades()

    def print_trades(self):
        trades_df = pd.DataFrame(self.trades)
        for trade in self.trades:
            print(
                f"Step: {trade['step']}, Action: {trade['action']}, Price: {trade['price']}, Shares: {trade['shares']}, Reward: {trade['reward']}, Shares Bought: {trade['inventory']}, Time Left: {trade['time left']}")

        return self.trades

        
        

class TradingEnvironmentMicro(Env):
    metadata = {'render.modes': ['human']}
    
    def __init__(self, data, api_key, preferred_timeframe=390, target_shares=100, max_orders=5):
        super(TradingEnvironmentMicro, self).__init__()
        self.data = data
        self.results = []
        self.cumulative_reward = 0
        self.current_step = 0
        self.preferred_timeframe = preferred_timeframe
        self.target_shares = target_shares
        self.remaining_shares_to_buy = self.target_shares
        self.max_orders = max_orders
        self.live_orders = []
        self.time_diff = 1
        self.canceled_orders = []
        self.executed_trades = []
        self.start_trade_price = None
        self.current_average_trade_price = 0

        self.api_key = "db-UVp9SCqXjLpm5qprthxS335uppKae"
        self.api_client = RESTClient(self.api_key)

        # Initialize start trade price at the beginning
        self.initialize_start_trade_price()

        # Define state columns
        self.state_columns = [
            'open', 'high', 'low', 'close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist', 
            'Stoch_k', '+DI', '-DI', 'Stoch_d', 'expected_price', 'OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 
            'ATR_1', 'ADX', 'CCI', 'transaction_cost', 'shares', 
            'forecast_6Hr_open', 'forecast_6Hr_close', 'forecast_6Hr_high', 'forecast_6Hr_low', 
            'forecast_6Hr_volatility', 'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost'
        ]

        # Define action space
        self.action_space = spaces.Box(
            low=np.array([0] * (2 + self.max_orders)),
            high=np.array([1] * (2 + self.max_orders)),
            dtype=np.float32
        )

        # Define observation space
        self.observation_space = spaces.Box(
            low=-10000, high=10000, shape=(len(self.state_columns),), dtype=np.float32
        )

    def initialize_start_trade_price(self):
        """Calculate and store the start_trade_price based on VWAP at the first time step for buying."""
        self.start_trade_price = np.sum(self.data['close'] * self.data['volume']) / np.sum(self.data['volume'])

    def update_current_average_trade_price(self):
        """Calculate the VWAP for all executed buy trades so far."""
        if len(self.executed_trades) > 0:
            total_volume = np.sum([trade['volume'] for trade in self.executed_trades])
            total_value = np.sum([trade['execution_price'] * trade['volume'] for trade in self.executed_trades])

            self.current_average_trade_price = total_value / total_volume if total_volume > 0 else 0
        else:
            self.current_average_trade_price = 0
            print("No trades executed yet.")

    def calculate_vwap(self, bid_prices, bid_sizes, size_of_slice):
        """VWAP calculation: sum(price * size) / sum(size)."""
        cum_sum_size = 0
        for idx, size in enumerate(bid_sizes):
            cum_sum_size += size
            if cum_sum_size >= size_of_slice:
                break

        bid_prices = bid_prices[:idx+1]
        bid_sizes = bid_sizes[:idx+1]
        return np.sum(np.array(bid_prices) * np.array(bid_sizes)) / np.sum(bid_sizes)

    def calculate_twap(self):
        """Calculate TWAP using close prices from the dataset."""
        close_prices = self.data['close'].iloc[:self.current_step] if self.current_step > 0 else self.data['close'].iloc[0:1]
        return close_prices.mean()


    def get_expected_price(self, symbol, timestamp):
        # Initialize the client with your API key
        try:
            timestamp = pd.to_datetime(timestamp)
        except Exception as e:
            print(f"Error parsing timestamp: {e}")
            return None, None, None, None, None

        client = db.Historical(self.api_key)

        # Convert timestamp to nanoseconds
        end_timestamp = int(timestamp.timestamp() * 1_000_000_000)
        start_timestamp = end_timestamp - (60 * 1_000_000_000)  # Subtract 1 minute from the timestamp for start time

        try:
            # Fetching Market by Price (MBP) data
            data = client.timeseries.get_range(
                dataset="XNAS.ITCH",  # Correct dataset for NASDAQ equities
                schema="mbp-1",       # Schema for Market by Price, top level only
                symbols=[symbol],
                start=start_timestamp,
                end=end_timestamp,
            )

            # Convert the data to a pandas DataFrame for processing
            df_mbp = data.to_df()

            if df_mbp.empty:
                print(f"No data found for the given timestamp: {timestamp}")
                return None, None, None, None, None

            # Drop rows with NaN values in the relevant columns
            df_mbp_cleaned = df_mbp.dropna(subset=['bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00'])

            if df_mbp_cleaned.empty:
                print(f"All data rows contained NaN values and were dropped for the given timestamp: {timestamp}")
                return None, None, None, None, None

            # Initialize variables to store maximum bid price and minimum ask price, and their sizes
            max_bid_price = float('-inf')
            min_ask_price = float('inf')
            bid_sizes = []
            ask_sizes = []
            bid_prices = []
            ask_prices = []

            # Process the cleaned data to find the maximum bid price and collect sizes
            for index, row in df_mbp_cleaned.iterrows():
                if row['bid_px_00'] > max_bid_price:
                    max_bid_price = row['bid_px_00']
                if row['ask_px_00'] < min_ask_price:
                    min_ask_price = row['ask_px_00']

                bid_prices.append(row['bid_px_00'])
                bid_sizes.append(row['bid_sz_00'] * 100)
                ask_prices.append(row['ask_px_00'])
                ask_sizes.append(row['ask_sz_00'] * 100)

            # Check if max_bid_price or min_ask_price was updated, otherwise handle no data case
            if max_bid_price == float('-inf') or min_ask_price == float('inf'):
                print(f"No valid bid or ask prices found after cleaning the data for the given timestamp: {timestamp}")
                return None, None, None, None, None

            # Return five values: min_ask_price, bid_sizes, ask_sizes, bid_prices, ask_prices
            return min_ask_price, bid_sizes, ask_sizes, bid_prices, ask_prices

        except Exception as e:
            print(f"An error occurred: {e}")
            return None, None, None, None, None


    def _get_state(self):
        """Return the current state of the market based on state columns."""
        if self.current_step >= len(self.data):
            return np.zeros(len(self.state_columns))
        market_conditions = self.data[self.state_columns].iloc[self.current_step].fillna(0).values
        return market_conditions

    
    def step(self, action):
        """Execute one time step within the environment."""
        action = self._add_noise_to_action(action)

        if self.current_step >= len(self.data):
            done = True
            return np.zeros(len(self.state_columns)), 0.0, done, {}

        ticker_symbol = self.data['Ticker'].iloc[self.current_step]
        timestamp_str = self.data['Timestamp'].iloc[self.current_step]

        expected_price, bid_sizes, ask_sizes, bid_prices, ask_prices = self.get_expected_price(ticker_symbol, timestamp_str)

        if expected_price is None or not bid_prices or not bid_sizes:
            print(f"Skipping step {self.current_step} due to lack of data.")
            self.current_step += 1
            return self._get_state(), 0.0, False, {}

        # Calculate VWAP price for this step
        vwap_price = self.calculate_vwap(ask_prices, ask_sizes, self.remaining_shares_to_buy)

        order_type = action[0]  # 0: market order, 1: limit order
        limit_price_scale = action[1]  # Scale factor for adjusting the limit price
        cancel_actions = action[2:2 + self.max_orders]  # Extract cancel actions

        volume = self.data['shares'].iloc[self.current_step]
        market_price = self.data['close'].iloc[self.current_step]
        limit_price = market_price - limit_price_scale * (0.02 * market_price)

        execution_price = vwap_price if order_type < 0.5 else limit_price

        # Handle limit order execution
        if order_type >= 0.5 and market_price <= limit_price:
            execution_price = limit_price
            volume_executed = min(volume, self.remaining_shares_to_buy)
            self.remaining_shares_to_buy -= volume_executed
            self.executed_trades.append({
                'execution_price': execution_price,
                'volume': volume_executed
            })
        else:
            if not any(order['price'] == limit_price for order in self.live_orders):
                self.live_orders.append({'volume': volume, 'price': limit_price, 'time_active': 0})

        # Apply cancellations with stricter conditions
        new_live_orders = []
        # max_time_active = 10  # Max steps before an order is considered stale and canceled
        for i, order in enumerate(self.live_orders[:len(cancel_actions)]):
            if cancel_actions[i] > 0.5: #or order['time_active'] >= max_time_active:
                print(f"Cancelling order: {order}")
                self.remaining_shares_to_buy += order['volume']
            else:
                order['time_active'] += 1
                new_live_orders.append(order)

        self.live_orders = new_live_orders
        self.update_current_average_trade_price()

        # Reward calculation
        reward = self._calculate_reward(execution_price, self.data.iloc[self.current_step], expected_price, order_type, volume)
        self.current_step += 1
        done = self.current_step >= len(self.data) or self.remaining_shares_to_buy <= 0

        # Store trade info
        trade_info = {
            'step': self.current_step,
            'timestamp': timestamp_str,
            'order_type': 'Market' if order_type < 0.5 else 'Limit',
            'volume': volume,
            'execution_price': execution_price,
            'reward': reward
        }
        self.results.append(trade_info)

        # Check for completed trade set and print the trades
        current_trade_set = self.data['Trade_Set_ID'].iloc[self.current_step - 1]
        previous_trade_set = self.data['Trade_Set_ID'].iloc[self.current_step - 2] if self.current_step > 1 else None

        if current_trade_set != previous_trade_set:
            self.print_trades()
            self.time_diff = 1  # Reset time_diff to 1 for the new schedule
            self.prev_mid_pricing = 0
            self.remaining_shares_to_buy = self.target_shares  # Reset inventory for new trade set
            self.executed_trades = []  # Clear executed trades for the new trade set
            self.live_orders = []  # Clear live orders for the new trade set
            self.initialize_start_trade_price()
            self.current_average_trade_price = 0
            # self.executed_trades = []
        else:
            self.time_diff += 1  # Increment time_diff for each trade within the same schedule

        return self._get_state(), reward, done, {}


    # original from  NImit
    def _calculate_reward(self, execution_price, trade_row, expected_price, order_type, volume_traded):
        # Constants
        kappa = 0.1
        actual_price = execution_price
        available_liquidity = trade_row['volume']  # Market liquidity at the time of the trade
        expected_price_movement = expected_price - actual_price

        # Volume-based slippage penalty for market orders
        if order_type < 0.5:  # Market order
            if available_liquidity > 0:
                # Slippage increases gradually based on the volume traded relative to available liquidity
                volume_ratio = volume_traded / available_liquidity
            else:
                # If available liquidity is 0, assume high slippage
                volume_ratio = 1.5  # You can adjust this factor as needed to represent high slippage due to no liquidity

            slippage_penalty = abs(actual_price - expected_price) * volume_ratio
            # print(f"Slippage Penalty before adjustment: {slippage_penalty}")
            # Reward for fast execution (market orders reduce uncertainty)
            execution_speed_reward = 0.02 * volume_traded  # Reward for quick fills
            reward = -slippage_penalty + execution_speed_reward

        else:  # Limit order
            # Slippage penalty is based on limit order execution price vs expected price
            slippage_penalty = actual_price - expected_price

            # Add reward for filling the order at a better price than expected for a long/buy position
            if expected_price < actual_price:
                slippage_penalty *= 1.5  # Reduce the penalty for limit orders if actual price is better than expected

            # Reward if limit order captures better price
            price_improvement_reward = 0.01 * volume_traded if actual_price < expected_price else 0
            # print(f"Price Improvement Reward: {price_improvement_reward}")
            reward = -slippage_penalty + price_improvement_reward

        # Calculate opportunity cost
        # print("abg current prive", self.current_average_trade_price)
        opp_cost = self.start_trade_price - self.current_average_trade_price
        # print(f"Opportunity Cost: {opp_cost}")
        # Decaying penalty for active limit orders
        decay_rate = 0.90
        # active_order_penalty = sum(order['volume'] * order['time_active'] * (decay_rate ** order['time_active']) for order in self.live_orders)
        # print(f"Active Order Penalty: {active_order_penalty}")
        
        
        # Final reward calculation combining all components
        penalty = slippage_penalty + opp_cost# + active_order_penalty
        # print(f"slippage_penalty + opp_cost + active_order_penalty+ reward: {slippage_penalty},{opp_cost}, {reward}")

        # Apply utility theory to adjust the penalty
        total_reward = -penalty - (2 * kappa * (penalty ** 2)) + reward
        # print(f"Total Reward: {total_reward}")

        return total_reward


    def _add_noise_to_action(self, action):
        """Add noise to the actions to simulate real-world uncertainties."""
        noise_action_0 = np.random.normal(0, 0.02)
        action[0] += noise_action_0
        action[0] = np.clip(action[0], self.action_space.low[0], self.action_space.high[0])

        noise_action_1 = np.random.normal(0, 0.02)
        action[1] += noise_action_1
        action[1] = np.clip(action[1], self.action_space.low[1], self.action_space.high[1])

        return action

    def print_trades(self):
        """Print the details of all trades executed in the completed trade set."""
        if self.results:
            trades_df = pd.DataFrame(self.results)
            print('--------------------------------------------------')
            print(f'Trade Set Completed: {self.data["Trade_Set_ID"].iloc[self.current_step - 1]}')
            print(trades_df.to_string(index=False))
            self.results = []  # Clear results after printing to avoid duplicate printing



    def reset(self):
        """Reset the environment to the initial state."""
        self.current_step = 0
        self.cumulative_reward = 0
        self.results = []
        self.executed_trades = []  
        self.initialize_start_trade_price()
        self.current_average_trade_price = 0
        return self._get_state()


    def render(self, mode='human', close=False):
        """Render the environment's current state."""
        print('--------------------------------------------------')
        print(f'Steps: {self.current_step}')
        print(f'Cumulative reward: {self.cumulative_reward}')
        self.print_trades()


