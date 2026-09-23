
# Trading Model

## Observation space:
`self.observation_space`: depends on states columns which are standardised, and the following additional states:
* self.remaining_inventory/self.total_inventory: the remaining inventory as a fraction of the total inventory.
* self.time_elapsed/self.preferred_timeframe: the elapsed time as a fraction of the preferred timeframe.
* actions[0]/self.max_shares_per_step: the first action ( likely the number of shares) scaled by the maximum number of shares per step.
* actions[1]/self.high_time: the second action (likely the time step) scaled by the high time.

### States used:
* For sell:
    - Top 5 bid prices (highest better) and there respective sizes, per minute
* For buy:
    - bottom 5 ask prices (lowest better) and there respective sizes, per minute


## Action space:
`self.action_space`: a 2D space where each dimension is a float between 0 and 1, representing
* the action (number of shares) that will be scaled to a range of 0 to 1.
    - `self.min_size` and `self.max_size` constants defining the minimum and maximum sizes of a trade, based on the inventory.
    - Which are used to unscale the action to the original space.

* the action (time) that will be scaled to a range of 0 to 1.
    - `self.high_time` and `self.low_time`: constants defining the high and low bounds for the time step that an action can jump to.
    - Which are used to unscale the action to the original space.


## Step:

It takes an `action` as input, which is a 2-element array representing the proportion of inventory to trade and the proportion of remaining time to spend.

The method updates the environment's state based on the action, including:

1. Calculating the trade size and time slice based on the action.
2. Executing the trade and calculating the penalty.
3. Updating the environment's time elapsed, current step, and remaining inventory.
4. Checking if the episode is done and calculating the reward.

The method returns:

1. The next observation (state) of the environment.
2. The reward for the current step.
3. A boolean indicating whether the episode is done.
4. Additional information about the step, including trade details and performance metrics.

The method also maintains a list of trade information, which includes details about each trade, such as the inventory, step, timestamp, time elapsed, and reward.

### Reward:

Function : `_calculate_reward`
This code calculates a reward based on the performance of a trading agent using the RL algorithm. The reward is a combination of two components:

1. `IS_diff`: the difference between the TWAP (Time-Weighted Average Price) and RL implementation shortfall, with a greater weight applied to TWAP.
2. `price_diff`: the difference between the best price achieved by the RL algorithm and the initial price, with a greater weight applied to the best price.

The reward is calculated differently depending on whether the agent is selling (`self.is_sell` is `True`) or buying (`self.is_sell` is `False`). The reward is then clipped to be between 0 and 10000.

* Note: reward only calculated for `buy` if IS_agent is greater than IS_twap.
* Note: reward only calculated for `sell` if IS_agent is less than IS_twap.


## Sell

### Calculating Twap:

Function : `_calculate_IS_sell_twap`


The Implementation Shortfall (IS) for the Time-Weighted Average Price (TWAP) benchmark. 

It simulates selling a fixed quantity of shares (`twap_order_size`) over a specified timeframe (`self.preferred_timeframe`), executing trades at the best available bid prices. 

The IS is calculated as the difference between the average best bid price over the timeframe and the actual executed price, scaled by the total inventory. 

The function returns the calculated IS (`IS_twap`) and the average best bid price (`best_price`). 

### Calculating IS based on Agent action:

Function : `_execute_sell_trade`
This code snippet defines a method `_execute_sell_trade` which simulates the execution of a sell trade in a trading environment. 

Here's a succinct explanation:

1. It takes in a `size_of_slice` parameter, which is the number of shares to be sold.
2. It iterates through the top 5 bid prices and sizes, matching the shares to be sold with the available bids.
3. It calculates the total executed shares and value, and applies a quadratic penalty for any remaining shares that couldn't be sold.
4. It calculates the weighted average price of the executed trade.
5. It logs the executed trade and updates the trading environment's state (e.g., remaining inventory, total shares traded).

The method returns the penalty applied for any unexecuted shares.

---

Function :  `_calculate_IS_ppo`

* It just computes the IS based on total executed value (from the `_execute_sell_trade` method) and total inventory and best price for those timesteps.




## Buy

* Similar to `sell` but for `buy` we use `ask_price` and `ask_size` instead of `bid_price` and `bid_size`, for calculating TWAP, reward.

