import gym
from gym import spaces
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

class TradingEnvironment(gym.Env):
    
    def __init__(self, data, inventory, preferred_timeframe, verbose=False):
        super(TradingEnvironment, self).__init__()
        
        self.data = data  # The pandas DataFrame containing price and other market information
        
        self.start_step = 0
        self.twap_order_size = self._get_twap_order_size(inventory, preferred_timeframe)
        self.max_shares_per_step = 2 * self.twap_order_size
        self.current_step = 0
        self.total_shares_traded = 0
        self.execution_prices = []  # Store execution prices
        self.total_inventory = inventory # Store total inventory
        self.preferred_timeframe = preferred_timeframe  # Store total timeframe
        self.time_elapsed = 0
        self.remaining_inventory = self.total_inventory
        self.total_penalty = 0
        self.trades_info = []

        self.state_columns = list(filter(lambda x: "processed" in x, self.data.columns.tolist()))

        self.action_space = spaces.Box(low=np.array([0]), high=np.array([1]), dtype=np.float32)  # Action (Number of shares) is later scaled from [0,1] to [0,2TWAP]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(len(self.state_columns) + 2,), dtype=np.float32) # Market info from row of data, remaining inventory, elapsed time
        
        self.initial_price = self.data['bid_price_1'].iloc[0]  # Best intial trading price
        self.T = len(data)  # Total number of time steps based on the length of the data
        self.verbose = verbose
        # self.IS_twap = self._calculate_IS_twap()
        # self.reset()


    def reset(self,randomize=True):
        # print("====Reset====")
        if randomize:
            self.current_step = np.random.randint(0, len(self.data) - self.preferred_timeframe-1)
        else:
            self.current_step = 0  # So that the model can explore all points instead of top data points
        
        self.start_step = self.current_step
        self.twap_order_size = self._get_twap_order_size(self.total_inventory, self.preferred_timeframe)
        self.remaining_inventory = self.total_inventory
        self.time_elapsed = 0
        self.total_shares_traded = 0
        self.execution_prices = []
        self.trades_info = []
        self.total_penalty = 0
        self.max_shares_per_step = 2 * self.twap_order_size

        self.initial_price = self.data['bid_price_1'].iloc[self.start_step]  # Reset initial price at t=0
        self.IS_twap = self._calculate_IS_twap()
        state = self.data[self.state_columns].iloc[self.current_step].values # commenting out .append(), i think it was put here by mistake
        return self.get_state(state)
    
    def get_state(self, state):
        obs = np.concatenate([state, np.array([self.remaining_inventory/self.total_inventory, self.time_elapsed/self.preferred_timeframe])])
        # print(obs.shape)
        return obs

    def step(self, action):

        size_of_slice = action[0] * 2 * self.twap_order_size # Actions scaled from [0, 1] to [0, 2TWAP]
        size_of_slice = np.clip(size_of_slice, 0, min(self.max_shares_per_step, self.remaining_inventory))

        self.time_elapsed += 1

        # # Ensure the trade size doesn't exceed the remaining inventory
        # if size_of_slice > self.remaining_inventory:
        #     size_of_slice = self.remaining_inventory
        
        # Get the penalty from executing the trade
        penalty = self._execute_trade(size_of_slice)
        self.total_penalty += penalty

        # Check if the episode is done
        if self.time_elapsed >= self.preferred_timeframe or self.remaining_inventory <= 0 or self.current_step == (self.T - 1):
            # Force liquidation of any remaining inventory
            if self.remaining_inventory > 0:
                extra_penalty = self._execute_trade(self.remaining_inventory)
                self.total_penalty += extra_penalty
            IS_ppo = self._calculate_IS_ppo()
            reward = self._calculate_reward(IS_ppo)# - self.total_penalty
            done = True
        else:
            IS_ppo = self._calculate_IS_ppo()
            reward = 0  # Sparse reward
            done = False

        self.current_step += 1
        if self.current_step >= self.T:
            self.current_step -= 1

        # done = (self.time_elapsed == self.preferred_timeframe) or (self.current_step == (self.T - 1))  # Check if episode is done

        next_observation = self.data[self.state_columns].iloc[self.current_step].values

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
        # print("==========")
        # print("current_step: ", self.current_step, "reward: ", reward, "IS_ppo: ", IS_ppo, "IS_twap: ", self.IS_twap, "IS_diff: ", IS_ppo - self.IS_twap)
        # print("Done: ", done, "====================")
        info = {
            'done' : done,
            'step' : self.current_step,
            'remaining_inventory': self.remaining_inventory,
            'time_elapsed': self.time_elapsed,
            'reward': reward,
            'share' : size_of_slice,
            'IS' : IS_ppo,
            'IS_diff' :  IS_ppo - self.IS_twap,
            'IS_twap' : self.IS_twap,
        }
        return self.get_state(next_observation), reward, done, info    

    def _execute_trade(self, size_of_slice):
        # Initialize variables
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
            # if shares_left > 0:
            # Assume remaining shares are sold at the worst bid price
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

        # Log the executed trade
        self.execution_prices.append((total_executed_shares, weighted_avg_price))
        self.total_shares_traded += total_executed_shares
        self.remaining_inventory -= total_executed_shares
        if self.verbose:
            print("weighted_avg_price: ", weighted_avg_price, "total_executed_shares: ", total_executed_shares, "remaining_inventory: ", self.remaining_inventory)
        return penalty
    def _calculate_IS_ppo(self):
        total_quantity = sum([trade[0] for trade in self.execution_prices])
        total_executed_value = sum([trade[0] * trade[1] for trade in self.execution_prices])

        # Account for any remaining inventory
        if self.remaining_inventory > 0:
            # Assume remaining shares are sold at the worst possible bid price
            worst_price = self.data['bid_price_5'].iloc[min(self.current_step - 1, self.T - 1)]
            total_quantity += self.remaining_inventory
            total_executed_value += self.remaining_inventory * worst_price

        IS_ppo = (self.initial_price * self.total_inventory) - total_executed_value
        return IS_ppo

    def _calculate_IS_twap(self):
        total_traded_volume = 0
        total_executed_value = 0

        twap_order_size = self.twap_order_size

        for step in range(self.start_step,self.preferred_timeframe+self.start_step):
            shares_left = twap_order_size

            for i in range(1, 6):
                
                bid_size = self.data[f'bid_size_{i}'].iloc[min(step, self.T - 1)]
                bid_price = self.data[f'bid_price_{i}'].iloc[min(step, self.T - 1)]

                trade_volume = min(shares_left, bid_size)
                total_traded_volume += trade_volume
                total_executed_value += trade_volume * bid_price
                shares_left -= trade_volume
                if self.verbose:
                    print("step : ", step, "Traded Shares: ", trade_volume, "Price: ", bid_price, "Total Executed Shares: ", total_traded_volume, "Total Executed Value: ", total_executed_value)
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
        if self.verbose:
            print("total_traded_volume: ",total_traded_volume, "total_executed_value: ", total_executed_value)
        IS_twap = (self.initial_price * self.total_inventory) - total_executed_value
        return IS_twap

    def _calculate_reward(self, IS_ppo):
        IS_twap = self.IS_twap  #self._calculate_IS_twap()

        # if IS_ppo > IS_twap:
        #     return -1
        # elif IS_ppo <= IS_twap < 1.1 * IS_ppo:
        #     return 0
        # elif IS_twap >= 1.1 * IS_ppo:
        #     return 1
        # else:
        #     return 0

        # if IS_ppo < IS_twap:
        #     return -1
        # elif IS_twap <= IS_ppo < 1.1 * IS_twap:
        #     return 0
        # elif IS_ppo >= 1.1 * IS_twap:
        #     return 1
        # else:
        #     return 0

        # if IS_ppo < IS_twap:
        #     return 1
        # elif IS_twap <= IS_ppo < 1.01 * IS_twap:
        #     return 0
        # elif IS_ppo >= 1.01 * IS_twap:
        #     return -1
        # else:
        #     return 0

        if IS_ppo > IS_twap:
            return -1
        elif IS_twap > IS_ppo:
            return IS_twap-IS_ppo
        else:
            return 0

    def _get_twap_order_size(self, inventory, preferred_timeframe):
        # twap_total_order_size = self.data['bid_price_2'].iloc[current_step:preferred_timeframe].sum()  # This is the TWAP order size
        
        # return twap_total_order_size/preferred_timeframe  # This variable will be inputted -- total_trades / total_timeframe (in mins)
        return inventory/preferred_timeframe