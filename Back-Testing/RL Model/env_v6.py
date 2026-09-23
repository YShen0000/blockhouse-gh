"""
Added Timestep Action on env_v4
"""

import gym
from gym import spaces
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

class TradingEnvironment(gym.Env):
    
    def __init__(self, data, inventory, preferred_timeframe, action = "sell", verbose=False, inference=False):
        """
        Initialize the TradingEnvironment
        Parameters:
            data (pandas.DataFrame): Market data
            inventory (int): Total number of shares to trade
            preferred_timeframe (int): Preferred time period to trade in
            verbose (bool): Whether to print out extra information
            inference (bool): Whether this is an inference environment
        """
        
        super(TradingEnvironment, self).__init__()
        
        self.data = data  # The pandas DataFrame containing price and other market information
        
        self.is_inference = inference  # Whether this is an inference environment
        self.start_step = 0  # Start of the episode
        self.twap_order_size = self._get_twap_order_size(
            inventory, preferred_timeframe
        )  # Calculate the order size for the TWAP strategy
        self.max_shares_per_step = inventory  #10 * self.twap_order_size
        self.current_step = 0  # Current time step
        self.total_shares_traded = 0  # Total number of shares traded
        self.execution_prices = []  # Store execution prices
        self.total_inventory = inventory  # Store total inventory
        self.preferred_timeframe = preferred_timeframe  # Store total timeframe
        self.time_elapsed = 0  # Time elapsed in the episode
        self.remaining_inventory = self.total_inventory  # Remaining shares to trade
        self.total_penalty = 0  # Total penalty for the episode
        self.trades_info = []  # Store information about each trade
        self.is_sell = True if action == "sell" else False

        # Only take processed columns as features/observations in the state
        self.state_columns = list(filter(lambda x: "processed" in x, self.data.columns.tolist()))

        self.action_space = spaces.Box(low=np.array([0,0]), high=np.array([1,1]), dtype=np.float32)  # Action (Number of shares) is later scaled from [0,1] to [0,2TWAP]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(len(self.state_columns) + 4,), dtype=np.float32) # Market info from row of data, remaining inventory, elapsed time
        
        self.T = len(data)  # Total number of time steps based on the length of the data


        # High and Low time which the action can be jumped to
        self.high_time = 40
        self.low_time = 5
        
        self.min_size = 0.05 * inventory
        self.max_size = inventory

        self.verbose = verbose


    def _unscale_timestep(self, action):
        """
        0-1 -> 1-preferred_timeframe
        """
        return int(self.low_time + ((action+0)*(self.high_time-self.low_time))/(1))

    def _unscale_size(self, action):
        """
        0-1 -> min_size-max_size
        """
        return int(self.min_size + ((action+0)*(self.max_size-self.min_size))/(1))


    def reset(self,randomize=True):
        """
        Resets the environment to a new random time step if randomize=True (default),
        otherwise sets the environment to the start of the episode.

        Args:
            randomize: If True, resets the environment to a random time step between 0 and
                len(data) - preferred_timeframe - 1. If False, resets the environment to the
                start of the episode (i.e. current_step = 0).

        Returns:
            The initial state of the environment, which is a combination of market data and
                private states (remaining inventory, time elapsed, etc.).
        """
        if randomize and not self.is_inference:
            self.current_step = np.random.randint(0, len(self.data) - self.preferred_timeframe-1)
        else:
            self.current_step = 0  # So that the model can explore all points instead of top data points
        
        self.start_step = self.current_step
        self.twap_order_size = self._get_twap_order_size(self.total_inventory, self.preferred_timeframe)
        self.remaining_inventory = self.total_inventory
        self.time_elapsed = 0
        self.total_shares_traded = 0
        self.execution_prices = []
        self.total_penalty = 0
        # self.max_shares_per_step = 2 * self.twap_order_size

        self.trades_info = []

        # self.initial_price = self.data['bid_price_1'].iloc[self.current_step]  # Best intial trading price

        if not self.is_inference:
            if self.is_sell:
                self.IS_twap, self.initial_price = self._calculate_IS_sell_twap()
            else:
                self.IS_twap, self.initial_price = self._calculate_IS_buy_twap()
        state = self.data[self.state_columns].iloc[self.current_step].values # commenting out .append(), i think it was put here by mistake
        return self.get_state(state,(0,0))
    
    def get_state(self, state, actions):
        obs = np.concatenate([state, np.array([self.remaining_inventory/self.total_inventory, self.time_elapsed/self.preferred_timeframe, actions[0]/self.max_shares_per_step, actions[1]/self.high_time])])
        # print(obs.shape)
        return obs

    def step(self, action):

        """
        Execute one step in the environment.

        Parameters
        ----------
        action : array_like
            A 2-element array where the first element is the proportion of the total inventory to trade at this step (0-1), and the second element is the proportion of the remaining time to spend at this step (0-1).

        Returns
        -------
        next_observation : array_like
            The next state of the environment.
        reward : float
            The reward for this step.
        done : bool
            Whether the episode is done.
        info : dict
            Additional information about the step.
        """
        # size_of_slice = int(action[0] * self.max_shares_per_step) # Actions scaled from [0, 1] to [0, 2TWAP]
        size_of_slice = self._unscale_size(action[0])
        size_of_slice = np.clip(size_of_slice, 0, min(self.max_shares_per_step, self.remaining_inventory))

        remaining_time = self.preferred_timeframe - self.time_elapsed
        time_slice = self._unscale_timestep(action[1])
        # time_slice = int(round(action[1] * self.preferred_timeframe)) #int(round(action[1])) # action[1] * self.preferred_timeframe
        time_slice = np.clip(time_slice, 0, remaining_time)

        # For micro inference # Not used in training, just for final blockhouse output which gives the market type 
        # limit / market , and price
        # it is important for inference
        order_type, price = "market", self.data['bid_price_1'].iloc[self.current_step]

        if self.is_inference:
            action_type = "sell" if self.is_sell else "buy"
            order_type, price = self.decide_order_type(action_type,future_minutes=time_slice)

        self.time_elapsed += time_slice
        self.current_step += time_slice

        # # Ensure the trade size doesn't exceed the remaining inventory
        # if size_of_slice > self.remaining_inventory:
        #     size_of_slice = self.remaining_inventory
        reward = 0
        # Get the penalty from executing the trade
        if self.time_elapsed < self.preferred_timeframe:
            if self.is_sell:
                penalty = self._execute_sell_trade(size_of_slice)
            else:
                penalty = self._execute_buy_trade(size_of_slice)
            self.total_penalty += penalty
        # Check if the episode is done
        if self.time_elapsed >= self.preferred_timeframe or self.remaining_inventory <= 0 or self.current_step >= self.T:
            if self.current_step >= self.T:
                self.current_step = min(self.current_step, self.T - 1)
            # Force liquidation of any remaining inventory
            extra_penalty = 0
            if self.remaining_inventory > 0:
                if self.is_sell:
                    extra_penalty = self._execute_sell_trade(self.remaining_inventory)
                else:
                    extra_penalty = self._execute_buy_trade(self.remaining_inventory)

                self.total_penalty += extra_penalty
            if not self.is_inference:
                IS_ppo, best_price = self._calculate_IS_ppo()
                reward = self._calculate_reward(IS_ppo, best_price)-np.sqrt(self.total_penalty)
            done = True
        else:
            if not self.is_inference:
                IS_ppo, best_price = self._calculate_IS_ppo()
                reward = 0  # Sparse reward
            done = False
        # done = (self.time_elapsed == self.preferred_timeframe) or (self.current_step == (self.T - 1))  # Check if episode is done

        next_observation = self.data[self.state_columns].iloc[self.current_step].values
        trade_info = {
            'inventory': self.remaining_inventory,
            "step": self.current_step,
            "timestamp" : pd.to_datetime(self.data.index[self.current_step]).replace(tzinfo=None),
            'time_elapsed': self.time_elapsed,
            "time_slice" : time_slice,
            "shares" : size_of_slice,
            "order_type" : order_type,
            "price" : price
        }

        if not self.is_inference:
            trade_info['IS'] = IS_ppo
            trade_info['IS_diff'] = IS_ppo - self.IS_twap
            trade_info['IS_twap'] = self.IS_twap
            trade_info['best_price'] = best_price
            trade_info['best_twap_price'] = self.initial_price
            trade_info['reward'] = reward
        self.trades_info.append(
            trade_info
        )

        if not self.is_inference:
            info = {
                'done' : done,
                'step': self.current_step,
                'remaining_inventory': self.remaining_inventory,
                'time_elapsed': self.time_elapsed,
                'reward': reward,
                'share' : size_of_slice,
                'time_slice' : time_slice,
                'IS' : IS_ppo,
                'IS_diff' :  IS_ppo - self.IS_twap,
                'IS_twap' : self.IS_twap,
                'best_price' : best_price
            }
        else:
            info = {}

        return self.get_state(next_observation,(size_of_slice, time_slice)), reward, done, info    

    def _execute_sell_trade(self, size_of_slice):
        # Initialize variables
        """
        Executes a trade by matching the given size of shares with available bid prices, 
        calculating the total executed shares and value, and handling any remaining shares 
        that couldn't be executed at the top 5 bids.

        Parameters:
        - size_of_slice (int): The number of shares intended to be executed.

        Returns:
        - penalty (int): The penalty applied for any unexecuted shares, calculated as a quadratic of remaining shares.
        """
        shares_left = size_of_slice
        total_executed_shares = 0
        total_executed_value = 0

        # Loop through the top 5 bid prices and their respective sizes
        for i in range(1, 6):
            bid_size = self.data[f'bid_size_{i}'].iloc[min(self.current_step, self.T - 1)]
            bid_price = self.data[f'bid_price_{i}'].iloc[min(self.current_step, self.T - 1)]

            trade_volume = min(shares_left, bid_size)
            total_executed_shares += trade_volume
            total_executed_value += trade_volume * bid_price
            shares_left -= trade_volume
            if self.verbose:
                print("step : ",self.current_step," Traded Shares: ", trade_volume, "Price: ", bid_price, "Total Executed Shares: ", total_executed_shares, "Total Executed Value: ", total_executed_value)
            if shares_left <= 0:
                break

        # Handle remaining shares that could not be sold at the top 5 bids
        penalty = 0
        if shares_left > 0:
            # Could not execute all shares
            # Apply a quadratic penalty
            penalty = shares_left ** 2
            # Remaining shares stay in the inventory for now
            worst_price = self.data[f'bid_price_5'].iloc[min(self.current_step, self.T - 1)]
            total_executed_shares += shares_left
            total_executed_value += shares_left * worst_price
            if self.verbose:
                print("Trading Share at Worst Bid: ", shares_left, "Price: ", worst_price, "Total Executed Shares: ", total_executed_shares, "Total Executed Value: ", total_executed_value)

        # Calculate the weighted average price
        if total_executed_shares > 0:
            weighted_avg_price = total_executed_value / total_executed_shares
        else:
            # No shares executed; use the worst bid price as an estimate
            weighted_avg_price = self.data['bid_price_5'].iloc[min(self.current_step, self.T - 1)]

        i = 1
        bid_size = self.data[f'bid_size_{i}'].iloc[min(self.current_step, self.T - 1)]
        bid_price = self.data[f'bid_price_{i}'].iloc[min(self.current_step, self.T - 1)]
        if self.verbose:
            print("Best Bid: ", bid_price, "total_executed_shares: ", total_executed_shares, "total_executed_value: ", total_executed_value, "weighted_avg_price: ", weighted_avg_price)
        # Log the executed trade
        self.execution_prices.append((total_executed_shares, weighted_avg_price, bid_size, bid_price))
        self.total_shares_traded += total_executed_shares
        self.remaining_inventory -= total_executed_shares

        return penalty

    def _execute_buy_trade(self, size_of_slice):
        # Initialize variables
        """
        Executes a trade by matching the given size of shares with available ask prices, 
        calculating the total executed shares and value, and handling any remaining shares 
        that couldn't be executed at the top 5 bids.

        Parameters:
        - size_of_slice (int): The number of shares intended to be executed.

        Returns:
        - penalty (int): The penalty applied for any unexecuted shares, calculated as a quadratic of remaining shares.
        """
        shares_left = size_of_slice
        total_executed_shares = 0
        total_executed_value = 0

        # Loop through the top 5 bid prices and their respective sizes
        for i in range(1, 6):
            ask_size = self.data[f'ask_size_{i}'].iloc[min(self.current_step, self.T - 1)]
            ask_price = self.data[f'ask_price_{i}'].iloc[min(self.current_step, self.T - 1)]

            trade_volume = min(shares_left, ask_size)
            total_executed_shares += trade_volume
            total_executed_value += trade_volume * ask_price
            shares_left -= trade_volume
            if self.verbose:
                print("step : ",self.current_step," Traded Shares: ", trade_volume, "Price: ", ask_price, "Total Executed Shares: ", total_executed_shares, "Total Executed Value: ", total_executed_value)
            if shares_left <= 0:
                break

        # Handle remaining shares that could not be sold at the top 5 bids
        penalty = 0
        if shares_left > 0:
            # Could not execute all shares
            # Apply a quadratic penalty
            penalty = shares_left ** 2
            # Remaining shares stay in the inventory for now
            worst_price = self.data[f'ask_price_5'].iloc[min(self.current_step, self.T - 1)]
            total_executed_shares += shares_left
            total_executed_value += shares_left * worst_price
            if self.verbose:
                print("Trading Share at Worst Ask: ", shares_left, "Price: ", worst_price, "Total Executed Shares: ", total_executed_shares, "Total Executed Value: ", total_executed_value)

        # Calculate the weighted average price
        if total_executed_shares > 0:
            weighted_avg_price = total_executed_value / total_executed_shares
        else:
            # No shares executed; use the worst bid price as an estimate
            weighted_avg_price = self.data['ask_price_5'].iloc[min(self.current_step, self.T - 1)]

        i = 1
        ask_size = self.data[f'ask_size_{i}'].iloc[min(self.current_step, self.T - 1)]
        ask_price = self.data[f'ask_price_{i}'].iloc[min(self.current_step, self.T - 1)]
        if self.verbose:
            print("Ask price: ", ask_price, "total_executed_shares: ", total_executed_shares, "total_executed_value: ", total_executed_value, "weighted_avg_price: ", weighted_avg_price)
        # Log the executed trade
        self.execution_prices.append((total_executed_shares, weighted_avg_price, ask_size, ask_price))
        self.total_shares_traded += total_executed_shares
        self.remaining_inventory -= total_executed_shares

        return penalty

    def _calculate_IS_ppo(self):
        """
        Calculates the Implementation Shortfall (IS) for the agent's execution using the PPO strategy.

        IS is calculated as the difference between the best possible price and the executed price, scaled by the total inventory.

        Returns:
        - IS_ppo (float): Implementation Shortfall for the agent using the PPO strategy.
        - best_price (float): The best possible price for the executed shares.
        """
        total_quantity = sum([trade[0] for trade in self.execution_prices])
        total_executed_value = sum([trade[0] * trade[1] for trade in self.execution_prices])

        best_price = sum([trade[3] for trade in self.execution_prices])/len(self.execution_prices)
        IS_ppo = (best_price * self.total_inventory) - total_executed_value
        if self.verbose:
            print("IS_ppo : ",IS_ppo, " best_price : ", best_price, " total_executed_value : ", total_executed_value)
        return IS_ppo, best_price

    def _calculate_IS_sell_twap(self):
        """
        Calculates the Implementation Shortfall (IS) for the TWAP (Time-Weighted Average Price) benchmark.

        Iterates through each time step within the preferred timeframe, executing trades at available bid prices.
        Accumulates the total traded volume and executed value. If shares remain untraded, assumes they are sold
        at the worst bid price. Computes the best price as the average of the top bid prices over all time steps.

        Returns:
        - IS_twap (float): The calculated Implementation Shortfall for the TWAP benchmark.
        - best_price (float): The average best bid price over the timeframe.
        """
        total_traded_volume = 0
        total_executed_value = 0

        twap_order_size = self.twap_order_size

        best_price = 0
        for step in range(self.start_step,self.preferred_timeframe+self.start_step):
            shares_left = twap_order_size

            for i in range(1, 6):
                bid_size = self.data[f'bid_size_{i}'].iloc[min(step, self.T - 1)]
                bid_price = self.data[f'bid_price_{i}'].iloc[min(step, self.T - 1)]
                # print("bid_size: ", bid_size, "bid_price: ", bid_price)
                if i==1:
                    best_price += bid_price
                trade_volume = min(shares_left, bid_size)
                total_traded_volume += trade_volume
                total_executed_value += trade_volume * bid_price
                shares_left -= trade_volume
                if self.verbose:
                    print("step : ",step," Traded Shares: ", trade_volume, "Price: ", bid_price, "Total Executed Shares: ", total_traded_volume, "Total Executed Value: ", total_executed_value)
                if shares_left <= 0:
                    break

            # Handle remaining shares
            if shares_left > 0:
                # Assume remaining shares are sold at the worst bid price
                worst_price = self.data[f'bid_price_5'].iloc[min(step, self.T - 1)]
                total_traded_volume += shares_left
                total_executed_value += shares_left * worst_price
                if self.verbose:
                    print("Trading Share at Worst Bid: ", shares_left, "Price: ", worst_price, "Total Executed Shares: ", total_traded_volume, "Total Executed Value: ", total_executed_value)

        best_price = best_price / self.preferred_timeframe

        IS_twap = (best_price * self.total_inventory) - total_executed_value
        if self.verbose:
            print("IS_twap : ",IS_twap, " best_price : ", best_price, " total_traded_volume : ",total_traded_volume, " total_executed_value : ",total_executed_value)
        # print("IS_twap : ",IS_twap)
        return IS_twap, best_price

    def _calculate_IS_buy_twap(self):
        """
        Calculates the Implementation Shortfall (IS) for the TWAP (Time-Weighted Average Price) benchmark.

        Iterates through each time step within the preferred timeframe, executing trades at available bid prices.
        Accumulates the total traded volume and executed value. If shares remain untraded, assumes they are sold
        at the worst bid price. Computes the best price as the average of the top bid prices over all time steps.

        Returns:
        - IS_twap (float): The calculated Implementation Shortfall for the TWAP benchmark.
        - best_price (float): The average best bid price over the timeframe.
        """
        total_traded_volume = 0
        total_executed_value = 0

        twap_order_size = self.twap_order_size

        best_price = 0
        for step in range(self.start_step,self.preferred_timeframe+self.start_step):
            shares_left = twap_order_size

            for i in range(1, 6):
                ask_size = self.data[f'ask_size_{i}'].iloc[min(step, self.T - 1)]
                ask_price = self.data[f'ask_price_{i}'].iloc[min(step, self.T - 1)]
                # print("ask_size: ", ask_size, "ask_price: ", ask_price)
                if i==1:
                    best_price += ask_price
                trade_volume = min(shares_left, ask_size)
                total_traded_volume += trade_volume
                total_executed_value += trade_volume * ask_price
                shares_left -= trade_volume
                if self.verbose:
                    print("step : ",step," Traded Shares: ", trade_volume, "Price: ", ask_price, "Total Executed Shares: ", total_traded_volume, "Total Executed Value: ", total_executed_value)
                if shares_left <= 0:
                    break

            # Handle remaining shares
            if shares_left > 0:
                # Assume remaining shares are sold at the worst bid price
                worst_price = self.data[f'ask_price_5'].iloc[min(step, self.T - 1)]
                total_traded_volume += shares_left
                total_executed_value += shares_left * worst_price
                if self.verbose:
                    print("Trading Share at Worst Bid: ", shares_left, "Price: ", worst_price, "Total Executed Shares: ", total_traded_volume, "Total Executed Value: ", total_executed_value)

        best_price = best_price / self.preferred_timeframe

        IS_twap = (best_price * self.total_inventory) - total_executed_value
        if self.verbose:
            print("IS_twap : ",IS_twap, " best_price : ", best_price, " total_traded_volume : ",total_traded_volume, " total_executed_value : ",total_executed_value)
        # print("IS_twap : ",IS_twap)
        return IS_twap, best_price

    def _calculate_reward(self, IS_ppo, best_price):

        
        """
        Calculate the reward based on the difference between TWAP and PPO prices

        Reward is calculated as the sum of two components:

        - IS_diff: the difference between IS_twap and IS_ppo, with a greater weight applied to IS_twap
        - price_diff: the difference between the best price and the initial price, with a greater weight applied to the best price

        The reward is then clipped to be between 0 and 10000

        Parameters
        ----------
        IS_ppo : float
            The IS calculated by the PPO algorithm
        best_price : float
            The best price achieved by the PPO algorithm

        Returns
        -------
        reward : float
            The calculated reward
        """

        IS_twap = self.IS_twap 
        if self.is_sell:
            IS_diff = np.exp((IS_twap - IS_ppo))*10 if IS_twap > IS_ppo else 0
            price_diff = np.exp(best_price - self.initial_price)*100 if best_price > self.initial_price else 0
        else:
            IS_diff = np.exp((IS_ppo - IS_twap)*10) if IS_ppo > IS_twap else 0
            price_diff = np.exp((self.initial_price - best_price)) if self.initial_price > best_price else 0

        return np.clip(price_diff+IS_diff,0,10000)
        # else:
        #     return 0
        
    def _get_twap_order_size(self, inventory, preferred_timeframe):
        return inventory/preferred_timeframe

    
    def decide_order_type(self, action='sell', future_minutes=25):
        # Method implementation as shown above
        # (Copy the decide_order_type method provided earlier)
        # [Include the complete method here]

        # Get the future data
        future_df = self.data.iloc[self.current_step+1 : self.current_step+1+future_minutes].copy()
        # print(len(future_df), )
        
        if future_df.empty or len(future_df) < 2:
            # print("future_df: ", future_df)
            # Not enough data ahead, default to market order
            return 'market', None
        
        # Calculate mid_prices
        # future_df['mid_price'] @= (future_df['open'] + future_df['close']) / 2
        
        # Fit linear regression
        X = np.arange(len(future_df)).reshape(-1,1)
        y = future_df['bid_price_1'].values.reshape(-1,1)
        reg = LinearRegression().fit(X, y)
        slope = reg.coef_[0][0]
        
        # Calculate volatility over that interval
        returns = future_df['bid_price_1'].pct_change().dropna()
        if len(returns) < 1:
            print("returns: ", returns)
            return 'market', None
        volatilities = returns.rolling(window=5).std().dropna()
        
        if len(volatilities) < 1:
            print("volatilities: ", volatilities)
            return 'market', None
        
        # Compute the 70th percentile of volatility over that interval
        volatility_threshold = np.percentile(volatilities, 70)
        current_volatility = volatilities.iloc[-1]  # use the last calculated volatility
        
        if current_volatility > volatility_threshold:
            # Volatility is high
            if action == 'sell':
                if slope > 0:
                    # For selling: if trend is up, set limit order
                    order_type = 'limit'
                    # Get the second highest mid_price in the interval
                    second_highest_mid_price = future_df['bid_price_1'].nlargest(2).iloc[-1]
                    price = second_highest_mid_price
                else:
                    # Trend is down
                    order_type = 'market'
                    price = None
            elif action == 'buy':
                if slope < 0:
                    # For buying: if trend is down, set limit order
                    order_type = 'limit'
                    # Get the second lowest mid_price in the interval
                    second_lowest_mid_price = future_df['bid_price_1'].nsmallest(2).iloc[-1]
                    price = second_lowest_mid_price
                else:
                    # Trend is up
                    order_type = 'market'
                    price = None
        else:
            # Volatility is low, execute market order
            order_type = 'market'
            price = None
        
        return order_type, price
