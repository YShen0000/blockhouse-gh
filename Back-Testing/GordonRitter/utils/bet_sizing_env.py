
import gym
from gym import spaces
import numpy as np
import pandas as pd

from GordonRitter.utils.benchmark_utils import calculate_vwap
from blockhouse_ml.equities.sell.utils.data_handler import TechnicalIndicators

class TradingEnvironment(gym.Env):
    def __init__(self,
                 data: pd.DataFrame,
                 reset_count=80,
                 initial_inventory=10,
                 state_columns=[]):
        super(TradingEnvironment, self).__init__()
        self.data = data
        self.current_step = 0 # Data index
        
        self.initial_inventory = initial_inventory
        self.remaining_inventory = self.initial_inventory
        self.trades = [] # Bid size prediction: Timestamp and Volume.
        self.cumulative_reward = 0 # Total reward in an episode.
        self.reset_count = reset_count # Length of episode in number of optm points.
        self.actions_ct = 0 # Count of non-zero actions
        self.progress = 0 # Progress of the episode 
        self.initial_inventory_log = [] # Amount of inventory remaining at of episodes.
        self.tradelist = [] # List of self.trade for each episode. 
        self.cycle_complete = False # End of data

        # Calculation of indicators
        if 'transaction_cost' not in data.columns:
            ti = TechnicalIndicators(self.data)
            ti.add_TC()

        self.data = ti.data
        self.data.bfill(inplace=True)
        
        # State columns form data: 'bid_price_1', 'bid_size_1', 'open', 'volume','daily_volume', 'volatility'
        if not state_columns:
            self.state_columns = data.columns
        else:
            self.state_columns = state_columns
        
        # Extracting bid_size and bid_price columns
        self.bid_prices_clms = []
        self.bid_size_clms = []
        for clm in self.data.columns:
            if 'bid_price' in clm:
                self.bid_prices_clms.append(clm)
            elif 'bid_size' in clm:
                self.bid_size_clms.append(clm)

        self.action_space = spaces.Box(low=0.0, high=1.0, dtype=np.float32)
        # Extra state columns:
        # progress: ranges 0 - 1 represents amount of point passed
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(len(self.state_columns)+2,), dtype=np.float32)
        self.reward_trajectory = []

    def _get_state(self):
        market_conditions = self._next_observation()
        return market_conditions
    
    def _next_observation(self):
        row = self.data[self.state_columns].iloc[self.current_step].to_list()
        row.append(self.progress/self.reset_count)
        row.append(self.remaining_inventory/self.initial_inventory)
        return np.array(row)
    
    def hard_reset(self):
        self.cumulative_reward = 0
        self.reward_trajectory = []
        self.initial_inventory_log = []

    def reset(self):
        # print('------------------------------------------------Class resetted------------------------------------------------')
        if self.progress and (self.current_step)%(self.reset_count*10) == 0:
            self.render()
        self.cumulative_reward = 0
        self.remaining_inventory = self.initial_inventory
        if self.trades:
            self.tradelist.append(self.trades)
        self.trades = []
        self.actions_ct = 0
        self.progress = 0
        state = self._get_state()
        return state
    
    def is_final_state(self):
        return (self.current_step+1)%self.reset_count == 0

    def step(self, action):
        self.cycle_complete = False
        self.progress += 1
        self.actions_ct += 1 if action else 0
        size_of_slice = min(action.item() * self.initial_inventory, self.remaining_inventory)
        size_of_slice = int(np.ceil(size_of_slice))
        
        self.trades.append([self.data['timestamp'].iloc[self.current_step], size_of_slice])
        
        execution_price = self._take_action(size_of_slice)

        reward = self._calculate_reward(execution_price, action.item())
        self.current_step += 1
        done = self.remaining_inventory <= 0 or self.is_final_state()
        if done:
            self.reward_trajectory.append(self.cumulative_reward)
            self.current_step = self.current_step//self.reset_count + 1
            self.current_step = self.current_step * self.reset_count
            self.initial_inventory_log.append(self.remaining_inventory)
        if self.current_step >= self.data.shape[0]:
            self.current_step = 0
            self.cycle_complete = True
        return self._get_state(), reward, done, {'cycle':self.cycle_complete}
        
    
    def _take_action(self, size_of_slice):
        self.remaining_inventory -= size_of_slice
        # print(f'Remaining inventory: {self.remaining_inventory}')
        if self.remaining_inventory < 0:
            self.remaining_inventory = 0
        current_row = self.data.iloc[self.current_step]
        execution_price = calculate_vwap(
            bid_prices = current_row[self.bid_prices_clms],
            bid_sizes = current_row[self.bid_size_clms],
            size_of_slice=size_of_slice
        )
        return execution_price
            
    def _calculate_reward(self, execution_price, action):
        # Constants
        kappa = 1e-4

        expected_price = self.data['open'].iloc[self.current_step]
        actual_price = execution_price
        

        # Calculating various components of the reward function
        slippage = (expected_price - actual_price)*action
        
        transaction_costs = self.data.iloc[self.current_step]['transaction_cost']
        
        mid_price = (self.data['ask_price_1'].iloc[self.current_step] + \
                    self.data['bid_price_1'].iloc[self.current_step]) / 2
        spread_cost = ((mid_price - actual_price)*action)

        # Combining all the components to calculate the reward
        penalty = (slippage + transaction_costs*action + spread_cost*action)
        
        if np.isnan(penalty):
            print(slippage, transaction_costs, spread_cost)
            raise ValueError

        
        if action > 0:
            reward = np.exp(-penalty - (2 * kappa * (penalty ** 2)))
        else:
            # lower the reward for action=0 more the exploration for a better point.
            reward = -20 * (self.progress/self.reset_count) *\
                        (self.remaining_inventory/self.initial_inventory)
        self.cumulative_reward += reward

        return reward

    
    def render(self):
        print('--------------------------------------------------')
        if self.actions_ct:
            print(f'Reward per trade: {self.cumulative_reward/self.actions_ct}')
        print(f'Actions:{self.actions_ct}')
        print(f'Number of steps:{self.progress}')
        print(f'Remaining inventory: {self.remaining_inventory}')
        print(f'Day End: {self.is_final_state()}')
        # self.print_trades()

    def close(self):
        pass