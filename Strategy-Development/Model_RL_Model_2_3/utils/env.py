import gym
from gym import spaces
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from datetime import datetime, timedelta

class CustomTradingEnvironment(gym.Env):
    metadata = {'render.modes': ['human']}
    
    def __init__(self, data, scenario, action_space, preferred_timeframe=390, initial_inventory=10):
        """
        Initializes the Custom Trading Environment.

        Args:
        - data (pd.DataFrame): Current input data row.
        - scenario (dict): Contains any scenario-specific parameters.
        - action_space (gym.spaces): The action space for the agent.
        - preferred_timeframe (int, optional): The number of steps in which the trade should be completed (default is 390).
        - initial_inventory (int, optional): Initial inventory of shares to be traded (default is 10).

        Returns:
        - None
        """
        super(CustomTradingEnvironment, self).__init__()
        self.data = data        
        self.preferred_timeframe = preferred_timeframe
        self.initial_inventory = initial_inventory
        self.remaining_inventory = self.initial_inventory
        self.elapsed_time = 0
        self.trades = []
        self.timestamp = pd.to_datetime(self.data['timestamp'], unit='ms')

        # State columns contain market data and technical indicators
        self.state_columns = ['open','high','low','close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist', 
                              'Stoch_k', 'Stoch_d', 'OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 'ATR_1', 'ADX', 
                              '+DI', '-DI', 'CCI', 'transaction_cost', 'forecast_6Hr_open','forecast_6Hr_close',
                              'forecast_6Hr_high','forecast_6Hr_low', 'forecast_6Hr_volatility', 
                              'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost']
        
        # Define the action space and observation space for the environment
        self.action_space = action_space
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(45,), dtype=np.float32)
        
    def reset(self):
        """
        Resets the environment to its initial state at the beginning of a new episode.

        Returns:
        - pd.Series: The last row of the data as the initial state.
        """
        print('------------------------------------------------Class resetted------------------------------------------------')
        self.remaining_inventory = self.initial_inventory
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


    def step(self, action):
        """
        Executes a step in the environment by performing the action provided by the agent.

        Args:
        - action (np.array): An array where action[0] is the percentage of inventory to trade and action[1] is the timing of the next trade.

        Returns:
        - bool: Whether the episode is done (i.e., inventory is depleted or time is up).
        - dict: Additional information about the step taken.
        """
        # Adding some noise to the actions
        action = self._add_noise_to_action(action)
        # print(f'Action taken: {action}')

        size_of_slice = action[0] * self.remaining_inventory
        size_of_slice = int(np.ceil(size_of_slice))

        # Scale action[1] to a desired range, e.g., 1 to 10
        timing_of_slice = int(np.ceil(action[1]))
        # print(f'timing_of_slice: {timing_of_slice}')

        self.elapsed_time += timing_of_slice

        if self.elapsed_time >= self.preferred_timeframe:
            size_of_slice = self.remaining_inventory

        # Take action
        self._take_action(size_of_slice)

        current_timestamp = self.timestamp
        # print(f"Current Timestamp: ", current_timestamp)
        next_timestamp = self.get_next_valid_market_timestamp(current_timestamp, timing_of_slice)

        # Print current and next step for debugging
        # print(f'Current Timestamp: {current_timestamp}')
        self.elapsed_time += timing_of_slice
        # print(f'Next step: {next_timestamp}')


        done = self.remaining_inventory <= 0 or self.elapsed_time >= self.preferred_timeframe

        # Record trade details
        trade_info = {
                'timestamp': next_timestamp,
                'action': action,
                'shares': size_of_slice,
                'inventory': self.remaining_inventory,
                'time left': self.preferred_timeframe - self.elapsed_time
            }
        self.trades.append(trade_info)

        info = {
            'step': next_timestamp,
            'action': action,
        }

        self.timestamp = next_timestamp

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

    
    def _take_action(self, size_of_slice):
        """
        Executes the trade by reducing the inventory based on the size of the slice.

        Args:
        - size_of_slice (int): The number of shares to trade.

        Returns:
        - None
        """
        self.remaining_inventory -= size_of_slice
        # print(f'Remaining inventory: {self.remaining_inventory}')
        if self.remaining_inventory < 0:
            self.remaining_inventory = 0
    
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
        return self.print_trades()

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



class TradingEnvironmentMicro(gym.Env):
    metadata = {'render.modes': ['human']}
    def __init__(self, data, preferred_timeframe=390, initial_inventory=100):
        super(TradingEnvironmentMicro, self).__init__()
        self.data = data
        self.results = []
        self.cumulative_reward = 0
        self.current_step = 0
        self.prev_mid_pricing = 0
        self.preferred_timeframe = preferred_timeframe
        self.initial_inventory = initial_inventory
        self.remaining_inventory = self.initial_inventory
        self.time_diff = 1  # Initialize time_diff
        self.macro_timestamps = self.data['Timestamp']
        # Define state columns
        self.state_columns = [
            'open','high','low','close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist', 
            'Stoch_k', 'Stoch_d', 'expected_price','OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 'ATR_1', 'ADX', 
            '+DI', '-DI', 'CCI', 'transaction_cost','shares', 'forecast_6Hr_open','forecast_6Hr_close','forecast_6Hr_high',
            'forecast_6Hr_low', 'forecast_6Hr_volatility', 'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost', 'shares'
        ]

        # Define flattened action space
        self.action_space = spaces.Box(low=np.array([0, 0]), high=np.array([1, 100000]), dtype=np.float32)

        # Define observation space
        self.observation_space = spaces.Box(
            low=-10000, high=10000, shape=(len(self.state_columns),), dtype=np.float32
        )
        
    def _add_noise_to_action(self, action):
        # Add noise to the first action (order type)
        noise_action_0 = np.random.normal(0, 0.02)  # Small noise for order type
        action[0] += noise_action_0
        action[0] = np.clip(action[0], self.action_space.low[0], self.action_space.high[0])

        # Add noise to the second action (limit price)
        noise_action_1 = np.random.normal(0, 1000)  # Noise for limit price
        action[1] += noise_action_1
        action[1] = np.clip(action[1], self.action_space.low[1], self.action_space.high[1])

        return action

    def step(self, action):
        """Execute one time step within the environment."""
        # Check if the environment is done
        action = self._add_noise_to_action(action)
        if self.current_step >= len(self.data):
            done = True
            return np.zeros(len(self.state_columns)), 0.0, done, {}  # Return default values when done

        order_type = action[0]  # 0: market order, 1: limit order
        #limit_price = action[1] 
        # print("dataasfdfsdgsdg", len(self.data), len(self.macro_timestamps))


        # Use 'market_price' from the data for market orders
        volume = self.data['shares'].iloc[self.current_step]
        market_price = self.data['close'].iloc[self.current_step]
        limit_price = 1.05*market_price
        execution_price = market_price if order_type < 0.5 else limit_price

        # Check if we are at the start of a new schedule/trade set
        if self.current_step > 0:
            current_trade_set = self.data['Trade_Set_ID'].iloc[self.current_step]
            previous_trade_set = self.data['Trade_Set_ID'].iloc[self.current_step - 1]
            if current_trade_set != previous_trade_set:
                # Print details of the completed trade set
                self.print_trades()
                # Reset alpha decay and time_diff for a new trade set
                self.total_alpha_decay = 0
                self.time_diff = 1  # Reset time_diff to 1 for the new schedule
                self.prev_mid_pricing = 0
            else:
                self.time_diff += 1  # Increment time_diff for each trade within the same schedule
        else:
            self.total_alpha_decay = 0
            self.time_diff = 1  # Initialize time_diff for the first trade

        # Calculate the reward using the new reward function
        trade_row = self.data.iloc[self.current_step]
        reward = self._calculate_reward(execution_price, trade_row)

        # Increment step and check if done
        

        macro_timestamp = self.data['Timestamp'].iloc[self.current_step]
        self.current_step += 1
    # Existing code to create trade_info
        trade_info = {
            'step': self.current_step,
            'timestamp': macro_timestamp,  # Now uses the appended 'Timestamp'
            'order_type': 'Market' if order_type < 0.5 else 'Limit',
            'volume': volume,
            'limit_price': execution_price,
        }
        self.results.append(trade_info)

        done = self.current_step >= len(self.data)

        return self._get_state(), reward, done, {}

    def _calculate_reward(self, execution_price, trade_row, alpha_decay_rate=0.01):
        # Constants
        kappa = 0.1
        expected_price = self.data['expected_price'].iloc[self.current_step]
        actual_price = execution_price
        # Calculating various components of the reward function
        slippage = expected_price - actual_price
        transaction_costs = self.data['transaction_cost'].iloc[self.current_step]
      

        # alpha decay component
        # total_alpha_decay = trade_row['shares'] * ((1-alpha_decay_rate) ** trade_row["time_active"])
        total_alpha_decay = trade_row['shares'] * ((1-alpha_decay_rate) ** self.time_diff)
        # opportunity cost component
        
        mid_pricing = (trade_row['high'] - trade_row['low']) / 2
        
        # opp_cost = (self.data['mid_price'][trade_row.name - trade_row['time_active']] - self.data['mid_price'][trade_row.name]) * (trade_row['shares']) / 2
        # Calculate mid-pricing as the average of the high and low prices
        # mid_pricing = (trade_row['high'] + trade_row['low']) / 2

        # Opportunity cost is the difference between the current mid-pricing and the previous mid-pricing
        # multiplied by the number of shares. This captures the missed opportunity if the price moves unfavorably.
        opp_cost = (mid_pricing - self.prev_mid_pricing) * trade_row['shares']

        # slippage to mid
        # mid_slippage = (self.data['mid_price'].iloc[self.current_step] - self.data['ask'].iloc[self.current_step]) * trade_row['shares']
        # Calculate the slippage to the mid-price
        # This measures how far the actual execution price is from the mid-price
        # multiplied by the number of shares, indicating potential losses from price movement.
        mid_slippage = (mid_pricing - self.data['low'].iloc[self.current_step]) * trade_row['shares']


        # # slippage to expected price
        # e_price_slippage = (self.data['expected_price'].iloc[self.current_step] - self.data['ask'].iloc[self.current_step]) * trade_row['shares']
        # Calculate slippage to the expected price
        # This measures the difference between the expected price and the ask price at the time of execution
        # multiplied by the number of shares, showing the loss from not achieving the expected price.
        e_price_slippage = (self.data['expected_price'].iloc[self.current_step] - self.data['low'].iloc[self.current_step]) * trade_row['shares']

        self.prev_mid_pricing = mid_pricing
#         # Combining all the components to calculate the reward
#         penalty = (slippage + transaction_costs + total_alpha_decay + opp_cost + mid_slippage + e_price_slippage)       
#         # Adding utility theory in rewards
#         reward = -penalty - (2 * kappa * (penalty ** 2))
        # Combining all the components (slippage, transaction costs, alpha decay, opportunity cost, and slippage calculations)
        # to compute the overall penalty. The reward is then the negative of the penalty, adjusted using a utility function.
        penalty = (slippage + transaction_costs + total_alpha_decay + opp_cost + mid_slippage + e_price_slippage)

        # Apply utility theory to adjust the penalty, making the reward more sensitive to larger penalties.
        reward = -penalty - (2 * kappa * (penalty ** 2))

    
        return reward

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
        return self._get_state()
    
    def _get_state(self):
        """Return the current state of the market based on state columns."""
        if self.current_step >= len(self.data):
            return np.zeros(len(self.state_columns))  # Return a zero array or some default value
        market_conditions = self.data[self.state_columns].iloc[self.current_step].values
        return market_conditions

    
    def render(self, mode='human', close=False):
        """Render the environment's current state."""
        print('--------------------------------------------------')
        print(f'Steps: {self.current_step}')
        print(f'Cumulative reward: {self.cumulative_reward}')
        self.print_trades()


class TradingEnvironmentMacroV2(gym.Env):
    metadata = {'render.modes': ['human']}
    
    # Preferred timeframe: The number of steps that the user wants to complete the trade in
    def __init__(self, data, action_space, original_action_space, eval = False, preferred_timeframe=390, initial_inventory=10, scenario='medium'):
        super(TradingEnvironmentMacroV2, self).__init__()
        self.data = data
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
        self.remaining_inventory_penalty = False

        # Extract state columns - have to change according to requirement
        self.state_columns = ['open', 'high', 'low', 'close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist',
                              'Stoch_k', 'Stoch_d', 'OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 'ATR_1', 'ADX',
                              '+DI', '-DI', 'CCI', 'ATR_2', 'ATR_5', 'ATR_10', 'ATR_20', 'ADX', '+DI', '-DI',
                              'CCI', 'DLR', 'transaction_cost', 'forecast_6Hr_open', 'market_liquidity',
                              'expected_price',
                              'log_return', 'volatility', 'mid_price', 'mean_vol', 'mean_liq',
                              '5_min_volatility', '5_min_volume', '5_min_TC', 'forecast_6Hr_close',
                              'forecast_6Hr_high', 'forecast_6Hr_low', 'forecast_6Hr_volatility',
                              'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost']

        self.state_columns_all_data = self.state_columns + ["ratio", "size_of_slice", "execution_price", "time_left"]


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

        self.observation_space = spaces.Box(low=-1, high=1, shape=(shape,), dtype=np.float32)        
        self.minimum_reward = -10000000
        self.reward_range = (10000, self.minimum_reward)
        self.size_of_slice = 0
        self.execution_price = 0
    
    
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

    def _next_observation(self):
        return self.data[self.state_columns].iloc[self.current_step].values

    def reset(self):
        # print('------------------------------------------------Class resetted------------------------------------------------')
        self.current_step = random.randint(0, len(self.data))
        self.cumulative_reward = 0
        self.remaining_inventory = self.initial_inventory
        self.elapsed_time = 0
        self.trades = []
        return self._get_state()

    def step(self, action):
        # Adding some noise to the actions
        # action = self._add_noise_to_action(action)
        # print(f'Action taken: {action}')

        action = self._unscale_action(action)

        size_of_slice = action[0]
        #size_of_slice = action[0] * self.remaining_inventory

        # Convert size of slice into whole number
        size_of_slice = int(np.ceil(size_of_slice))

        # Scale action[1] to a desired range, e.g., 1 to 10
        # print(f'timing_of_slice: {timing_of_slice}')

        self.elapsed_time += timing_of_slice

        if self.elapsed_time >= self.preferred_timeframe:
            size_of_slice = self.remaining_inventory

        #execution_price = self._take_action(size_of_slice)
        execution_price, size_of_slice = self._take_action_v2(size_of_slice)


        # Print current and next step for debugging
        # print(f'Current step: {self.current_step}')
        self.current_step += timing_of_slice
        # print(f'Next step: {self.current_step}')

        if self.remaining_inventory_penalty:
            inventory_flag = False
            last_step_inventory = 0
            if self.elapsed_time >= self.preferred_timeframe:
                size_of_slice = self.remaining_inventory
                inventory_flag = True
                last_step_inventory = self.remaining_inventory


        # Ensure the index is sequential
        if self.current_step >= len(self.data):
            self.current_step = len(self.data) - 1

        done = self.remaining_inventory <= 0 or self.elapsed_time >= self.preferred_timeframe

        reward, slippage, transaction_Costs, opportunity_cost = self._calculate_reward(size_of_slice, execution_price,
                                                                                       timing_of_slice)
        
        if inventory_flag and self.remaining_inventory_penalty:
            ratio = (last_step_inventory / self.initial_inventory)
            reward = reward - 10
            print('remaining inventory penalty')
            # print(30 * (last_step_inventory / self.initial_inventory))
        #
        if self.remaining_inventory == 0 and self.preferred_timeframe - self.elapsed_time > 0:
            ratio = ((self.preferred_timeframe - self.elapsed_time) / self.preferred_timeframe)
            print('remaining inventory reward')
            reward += 10
        
        self.cumulative_reward += reward

        
        # if done:
        #     print(f'Cumulative Rewards: {self.cumulative_reward}')
        # ic(reward)
        # ic(slippage)
        # ic(transaction_Costs)
        # ic(opportunity_cost)

        trade_info = {
            'step': self.current_step,
            #                 'timestamp': self.data.index[self.current_step],
            'action': action,
            'price': execution_price,
            'shares': size_of_slice,
            'timestamp': self.data['datetime'].iloc[self.current_step],
            'reward': reward,
            'slippage': slippage,
            'transaction_cost': transaction_Costs,
            "opportunity_cost": opportunity_cost,
            'inventory': self.remaining_inventory,
            'time left': self.preferred_timeframe - self.elapsed_time,
        }
        self.trades.append(trade_info)
        # ic(trade_info)

        info = {
            'step': self.current_step,
            'action': action,
            'price': execution_price
        }

        return self._get_state(), reward, done, info


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
        print(f'Remaining inventory: {self.remaining_inventory}')
        execution_price = self.data['close'].iloc[self.current_step]
        return execution_price, size_of_slice

    def _calculate_transaction_cost(self, volume, daily_volume, volatility=None):
        if volatility is None:
            volatility = self.data['volatility'].iloc[self.current_step]
        return volatility * np.sqrt(volume / daily_volume)

    @staticmethod
    def databento_expected_price(symbol, timestamp):
        # Initialize the client with your API key
        api_key = "db-s8TQsSX8JF539yQSeBWFGPNyDx4m3"

        client = db.Historical(api_key)
        # Convert timestamp to nanoseconds
        end_timestamp = int(timestamp.timestamp() * 1_000_000_000)
        start_timestamp = end_timestamp - (60 * 1_000_000_000)  # Subtract 1 minute from the timestamp for start time
        # Convert timestamps to datetime strings for the query
        start_date = datetime.utcfromtimestamp(start_timestamp / 1_000_000_000).strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date = datetime.utcfromtimestamp(end_timestamp / 1_000_000_000).strftime('%Y-%m-%dT%H:%M:%SZ')
        try:
            # Fetching Market by Price (MBP) data
            data = client.timeseries.get_range(
                dataset="XNAS.ITCH",  # Correct dataset for NASDAQ equities
                schema="mbp-1",  # Schema for Market by Price, top level only
                symbols=[symbol],
                start=start_date,
                end=end_date,
            )
            # Convert the data to a pandas DataFrame for processing
            df_mbp = data.to_df()
            if df_mbp.empty:
                print(f"No data found for the given timestamp: {timestamp}")
                return None, None, None, None, None, None, None
            # Drop rows with NaN values in the relevant columns
            df_mbp_cleaned = df_mbp.dropna(subset=['bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00'])
            if df_mbp_cleaned.empty:
                print(f"All data rows contained NaN values and were dropped for the given timestamp: {timestamp}")
                return None, None, None, None, None, None, None
            # Initialize variables to store maximum bid price and minimum ask price, and their sizes
            max_bid_price = float('-inf')
            min_ask_price = float('inf')

            max_bid_price = df_mbp_cleaned['bid_px_00'].mean()

            avg_bid_price = df_mbp_cleaned['bid_px_00'].mean()
            avg_ask_price = df_mbp_cleaned['ask_px_00'].mean()

            ask_prices = df_mbp_cleaned['ask_px_00'].to_numpy()
            bid_prices = df_mbp_cleaned['bid_px_00'].to_numpy()
            bid_sizes = df_mbp_cleaned['bid_sz_00'].to_numpy()
            ask_sizes = df_mbp_cleaned['ask_sz_00'].to_numpy()
            # Check if max_bid_price was updated, otherwise handle no data case
            if max_bid_price == float('-inf') or min_ask_price == float('inf'):
                print(f"No valid bid or ask prices found after cleaning the data for the given timestamp: {timestamp}")
                return None, None, None, None, None, None, None
            return max_bid_price, avg_bid_price, avg_ask_price, bid_sizes, ask_sizes, bid_prices, ask_prices
        except Exception as e:
            print(f"An error occurred: {e}")
            return None, None, None, None, None, None, None

    @staticmethod
    @lru_cache(maxsize=1024)
    def polygon_expected_price(symbol, timestamp):
        # Initialize the client with your API key
        api_key = 'r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc'

        client = RESTClient(api_key)

        # Convert timestamp to nanoseconds
        end_timestamp = int(timestamp.timestamp() * 1_000_000_000)
        start_timestamp = end_timestamp - (60 * 1_000_000_000)  # Subtract 1 minute from the timestamp for start time

        # Make the API call
        quotes = client.list_quotes(
            symbol,
            timestamp_gte=start_timestamp,
            timestamp_lte=end_timestamp,
            limit=50000  # Adjust based on your needs
        )

        # Initialize variables to store maximum bid price and sizes
        max_bid_price = float('-inf')
        min_ask_price = float('inf')
        bid_sizes = []
        ask_sizes = []
        bid_prices = []
        ask_prices = []

        # Process the results to find the maximum bid price and collect sizes
        for quote in quotes:
            if quote.bid_price > max_bid_price:
                max_bid_price = quote.bid_price
            if quote.ask_price < min_ask_price:
                min_ask_price = quote.ask_price
            bid_prices.append(quote.bid_price)
            bid_sizes.append(quote.bid_size * 100)
            ask_sizes.append(quote.ask_size * 100)
            ask_prices.append(quote.ask_price)

        # Check if max_bid_price was updated, otherwise handle no data case
        if max_bid_price == float('-inf'):
            print(f"No bid prices found for the given timestamp: {timestamp}")
            return None, None, None, None, None, None, None

        return max_bid_price, sum(bid_prices) / len(bid_prices), sum(ask_prices) / len(ask_prices), np.array(
            bid_sizes), ask_sizes, np.array(bid_prices), ask_prices

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
    
    def _calculate_reward(self, size_of_slice, execution_price, timing_of_slice):
        # Constants
        kappa = 0.1
        order_size = size_of_slice
        market_liquidity = self.data['market_liquidity'].iloc[self.current_step]
        time_remaining = self.preferred_timeframe - self.elapsed_time
        total_time = self.preferred_timeframe

        # Convert current_timestamp to datetime object
        current_timestamp = self.data['datetime'].iloc[self.current_step]
        timestamp = pd.to_datetime(current_timestamp).replace(tzinfo=pytz.UTC)

        # Fetch expected price, bid_sizes, ask_sizes, and bid_prices from the Polygon API
        expected_price, avg_bid_price, avg_ask_price, bid_sizes, ask_sizes, bid_prices, ask_prices = self.polygon_expected_price(
            self.data[
                'ticker'].iloc[
                self.current_step],
            timestamp)
        # print((expected_price, avg_bid_price, avg_ask_price, bid_sizes, ask_sizes, bid_prices, ask_prices))
        # max bid price is the same as expected price; new variable for clarity
        max_bid_price = expected_price
        if expected_price is None:
            # print("Expected price couldn't be fetched, returning no reward.")
            return 0, 0, 0, 0
        else:
            spread_cost = (avg_ask_price - avg_bid_price) * size_of_slice

        # Calculate VWAP based on bid prices and sizes
        actual_price = self.calculate_vwap(bid_prices, bid_sizes)

        # Slippage: difference between expected price and actual execution price
        slippage = (expected_price - actual_price) * size_of_slice
        # print(f"slippage {slippage}")
        # print(f"transaction_cost - {tran}")
        # Transaction costs (referred to as Price Impact)
        transaction_costs = self.data['transaction_cost'].iloc[self.current_step] * size_of_slice

        # VWAP for opportunity cost calculation
        if not hasattr(self, 'start_vwap_price'):
            self.start_vwap_price = self.data.iloc[0]['VWAP']
        self.vwap_price_set_executed_prices.append(self.data.iloc[self.current_step]['VWAP'])
        opportunity_cost = self.start_vwap_price - sum(self.vwap_price_set_executed_prices) / len(
            self.vwap_price_set_executed_prices)

        # Penalize actions taken early in the timeframe (encourage spreading actions)
        # early_action_penalty = self.delta * (time_remaining / total_time) ** 2  # Quadratic scaling

        second_reward_formulation = True

        if second_reward_formulation:
            volume_traded = size_of_slice
            available_liquidity = self.data['market_liquidity'].iloc[self.current_step]
            liquidity_ratio = volume_traded / available_liquidity if available_liquidity > 0 else 1
            slippage_penalty = abs(actual_price - expected_price) * liquidity_ratio
            transaction_costs_penalty = transaction_costs * (1 + (liquidity_ratio))
            # small_timestep_penalty = base_penalty * (1 + (1 / available_liquidity))
            market_impact_penalty = (liquidity_ratio) ** 2
            penalty = (
                    market_impact_penalty + transaction_costs_penalty + slippage_penalty + liquidity_ratio)

        else:
            # Combine all the components to calculate the reward
            penalty = (
                    slippage + transaction_costs + opportunity_cost + spread_cost)

        # Adding utility theory in rewards
        reward = -penalty - (2 * kappa * (penalty ** 2))
        
        if math.isnan(reward):
            slippage = 0
            transaction_costs = 0
            print("Reward is NaN!")
            print(
                f"Total time: {total_time} Time elapsed: {self.elapsed_time}, Time remaining: {time_remaining}, Time slice: {timing_of_slice}")
            print(
                f"Expected price: {expected_price}, Actual price: {actual_price}, Curent step: {self.current_step} Current Time: {timestamp}")
            print(f"Bid prices: {bid_prices}, Bid sizes: {bid_sizes}, ask prices: {ask_prices}, ask sizes: {ask_sizes}")

        reward = reward * 0.1

        return reward, slippage, transaction_costs, opportunity_cost

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
