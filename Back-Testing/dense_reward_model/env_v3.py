import gym
from gym import spaces
import numpy as np
import pandas as pd

class TradingEnvironment(gym.Env):


    def __init__(self, data, inventory, preferred_timeframe, 
                 slippage_factor=0.95, penalty_factor=0.01, 
                 verbose=False):

        super(TradingEnvironment, self).__init__()

        self.data = data.reset_index(drop=True)  # Ensure the data is zero-indexed
        self.total_inventory = inventory
        self.preferred_timeframe = preferred_timeframe
        self.slippage_factor = slippage_factor
        self.penalty_factor = penalty_factor
        self.verbose = verbose

        self.trades_info = []

        # Calculate TWAP order size
        self.twap_order_size = self.total_inventory / self.preferred_timeframe

        # Dynamically set max_shares_per_step based on available liquidity
        max_bid_size = self.data[[f'bid_size_{i}' for i in range(1, 6)]].max().max()
        self.max_shares_per_step = min(2 * self.twap_order_size, max_bid_size)

        # Define action and observation spaces
        # Action: Continuous value between 0 and 1, scaled to [0, 2 * TWAP_order_size]
        self.action_space = spaces.Box(low=np.array([0.0]), 
                                       high=np.array([1.0]), 
                                       dtype=np.float32)

        # Observation: Market features + remaining inventory (normalized) + time elapsed (normalized)
        num_market_features = self.data.filter(regex='processed').shape[1]
        self.observation_space = spaces.Box(low=-np.inf,
                                            high=np.inf,
                                            shape=(num_market_features + 2,),
                                            dtype=np.float32)

        # Initialize episode-specific variables
        self.reset()

    def reset(self, randomize=True):
        """
        Resets the environment to start a new episode.

        Parameters:
        - randomize (bool): If True, starts at a random step within the data range.

        Returns:
        - state (np.array): Initial observation.
        """
        if randomize:
            self.current_step = np.random.randint(0, len(self.data) - self.preferred_timeframe - 1)
        else:
            self.current_step = 0

        self.start_step = self.current_step
        self.remaining_inventory = self.total_inventory
        self.time_elapsed = 0
        self.total_shares_traded = 0
        self.execution_prices = []  # List of tuples: (shares_executed, price)
        self.total_penalty = 0
        self.trades_info = []

        # Initial price based on best bid at start
        self.initial_price = self.data['bid_price_1'].iloc[self.current_step]

        # Calculate TWAP IS at initialization
        self.IS_twap = self._calculate_IS_twap()

        # Extract market features for the initial step
        state = self.data.filter(regex='processed').iloc[self.current_step].values
        return self.get_state(state)

    def get_state(self, state):
        """
        Constructs the state representation.

        Parameters:
        - state (np.array): Market features for the current step.

        Returns:
        - obs (np.array): Complete state including private information.
        """
        normalized_inventory = self.remaining_inventory / self.total_inventory
        normalized_time = self.time_elapsed / self.preferred_timeframe
        obs = np.concatenate([state, [normalized_inventory, normalized_time]])
        return obs.astype(np.float32)

    def step(self, action):
        """
        Executes one time step within the environment.

        Parameters:
        - action (np.array): Action taken by the agent.

        Returns:
        - next_observation (np.array): Observation after the action.
        - reward (float): Reward obtained from the action.
        - done (bool): Whether the episode has ended.
        - info (dict): Additional information.
        """
        # Scale action to determine number of shares to trade
        size_of_slice = np.ceil(action[0] * 2 * self.twap_order_size)
        size_of_slice = np.clip(size_of_slice, 0, min(self.max_shares_per_step, self.remaining_inventory))

        self.time_elapsed += 1

        # Execute the trade and accumulate penalties if any
        penalty = self._execute_trade(size_of_slice)
        self.total_penalty += penalty

        # Determine if the episode has ended
        done = False
        reward = 0.0

        if (self.time_elapsed >= self.preferred_timeframe) or (self.remaining_inventory <= 0) or (self.current_step >= len(self.data) - 1):
            done = True

            # Force liquidation of any remaining inventory at a worse price
            if self.remaining_inventory > 0:
                extra_penalty = self._execute_trade(self.remaining_inventory)
                self.total_penalty += extra_penalty

            # Calculate final IS and reward
            IS_ppo = self._calculate_IS_ppo()
            reward = self._calculate_reward(IS_ppo)
        else:
            # Sparse reward: No reward until the end of the episode
            IS_ppo = self._calculate_IS_ppo()
            reward = 0.0

        # Advance to the next time step
        self.current_step += 1
        self.current_step = min(self.current_step, len(self.data) - 1)  # Prevent overflow

        # Prepare the next observation
        if not done:
            next_state = self.data.filter(regex='processed').iloc[self.current_step].values
            next_observation = self.get_state(next_state)
        else:
            # Terminal state: Return zeros or any fixed value
            next_observation = np.zeros(self.observation_space.shape, dtype=np.float32)

        # Optional: Log trade information for debugging
        if self.verbose:
            print(f"Step: {self.current_step}, Action: {size_of_slice}, "
                  f"Penalty: {penalty}, Remaining Inventory: {self.remaining_inventory}, "
                  f"IS_ppo: {IS_ppo}, IS_twap: {self.IS_twap}, Reward: {reward}, Done: {done}")

        
        self.trades_info.append(
            {
                'remaining_inventory': self.remaining_inventory,
                'time_elapsed': self.time_elapsed,
                'reward': reward,
                'share' : size_of_slice,
                'IS' : IS_ppo,
                'IS_diff' : IS_ppo - self.IS_twap,
                'IS_twap' : self.IS_twap,
            }
        )

        # Additional info for debugging
        info = {
            'done': done,
            'remaining_inventory': self.remaining_inventory,
            'time_elapsed': self.time_elapsed,
            'reward': reward,
            'share': size_of_slice,
            'IS': IS_ppo,
            'IS_twap': self.IS_twap,
            'IS_diff': IS_ppo - self.IS_twap,
            'total_penalty': self.total_penalty
        }

        return next_observation, reward, done, info

    def _execute_trade(self, size_of_slice):
        """
        Executes a trade of the specified size, handling overflow beyond top 5 bids.

        Parameters:
        - size_of_slice (float): Number of shares to execute.

        Returns:
        - penalty (float): Penalty incurred for unexecuted shares.
        """
        shares_left = size_of_slice
        total_executed_shares = 0
        total_executed_value = 0
        step_index = min(self.current_step, len(self.data) - 1)

        # Execute trades against the top 5 bids
        for i in range(1, 6):
            bid_size = self.data[f'bid_size_{i}'].iloc[step_index]
            bid_price = self.data[f'bid_price_{i}'].iloc[step_index]
            trade_volume = min(shares_left, bid_size)

            if trade_volume > 0:
                total_executed_shares += trade_volume
                total_executed_value += trade_volume * bid_price
                shares_left -= trade_volume

                if self.verbose:
                    print(f"Executed {trade_volume} shares at bid {i} price {bid_price}")

            if shares_left <= 0:
                break

        penalty = 0.0

        # Handle remaining shares by executing at a worse price
        if shares_left > 0:
            # Option 1: Execute at a static worse price
            worse_price = self.initial_price * self.slippage_factor

            # Option 2: Apply a slippage factor to bid 5's price
            # worse_price = self.data['bid_price_5'].iloc[step_index] * self.slippage_factor

            total_executed_shares += shares_left
            total_executed_value += shares_left * worse_price
            penalty = (shares_left ** 2) * self.penalty_factor

            if self.verbose:
                print(f"Executed remaining {shares_left} shares at worse price {worse_price} with penalty {penalty}")

        # Calculate weighted average price for the executed shares
        if total_executed_shares > 0:
            weighted_avg_price = total_executed_value / total_executed_shares
        else:
            # If no shares were executed, assume worst price
            weighted_avg_price = self.initial_price * self.slippage_factor

        # Log the executed trade
        self.execution_prices.append((total_executed_shares, weighted_avg_price))
        self.total_shares_traded += total_executed_shares
        self.remaining_inventory -= total_executed_shares

        return penalty

    def _calculate_IS_ppo(self):
        """
        Calculates the Implementation Shortfall (IS) for the agent's execution.

        Returns:
        - IS_ppo (float): Implementation Shortfall for the agent.
        """
        total_executed_value = sum([trade[0] * trade[1] for trade in self.execution_prices])

        # Account for any remaining inventory by assuming they are sold at the worse price
        if self.remaining_inventory > 0:
            worse_price = self.initial_price * self.slippage_factor
            total_executed_value += self.remaining_inventory * worse_price

        # IS Calculation: (Arrival Price * Total Inventory) - Executed Value
        IS_ppo = (self.initial_price * self.total_inventory) - total_executed_value
        return IS_ppo

    def _calculate_IS_twap(self):
        """
        Calculates the Implementation Shortfall (IS) for the TWAP benchmark.

        Returns:
        - IS_twap (float): Implementation Shortfall for the TWAP benchmark.
        """
        total_executed_value = 0.0
        twap_order_size = self.twap_order_size

        for step in range(self.start_step, self.start_step + self.preferred_timeframe):
            if step >= len(self.data):
                break  # Prevent out-of-bounds

            shares_left = twap_order_size

            for i in range(1, 6):
                bid_size = self.data[f'bid_size_{i}'].iloc[step]
                bid_price = self.data[f'bid_price_{i}'].iloc[step]
                trade_volume = min(shares_left, bid_size)

                if trade_volume > 0:
                    total_executed_value += trade_volume * bid_price
                    shares_left -= trade_volume

                if shares_left <= 0:
                    break

            # Handle remaining shares by executing at a worse price to simulate slippage
            if shares_left > 0:
                worse_price = self.initial_price * self.slippage_factor
                total_executed_value += shares_left * worse_price

        # IS Calculation for TWAP: (Arrival Price * Total Inventory) - Executed Value
        IS_twap = (self.initial_price * self.total_inventory) - total_executed_value
        return IS_twap

    def _calculate_reward(self, IS_ppo):
        """
        Calculates the reward based on the agent's Implementation Shortfall (IS).

        Parameters:
        - IS_ppo (float): Implementation Shortfall of the agent.

        Returns:
        - reward (float): Calculated reward.
        """
        improvement = self.IS_twap - IS_ppo  # Positive if agent is better
        normalized_improvement = improvement / self.total_inventory

        # Combine improvement with penalty
        normalized_penalty = self.total_penalty / self.total_inventory
        reward = normalized_improvement - normalized_penalty

        # Clip the reward to ensure it's within [-1, 1]
        reward = np.clip(reward, -1, 1)

        if self.verbose and self.done:
            print(f"Final IS_ppo: {IS_ppo}, IS_twap: {self.IS_twap}, "
                  f"Improvement: {improvement}, Penalty: {normalized_penalty}, Reward: {reward}")

        return reward

    def render(self, mode='human'):
        """
        Renders the current state of the environment.
        """
        print(f"Step: {self.current_step}, Remaining Inventory: {self.remaining_inventory}, "
              f"Time Elapsed: {self.time_elapsed}")

    def close(self):
        """
        Closes the environment.
        """
        pass