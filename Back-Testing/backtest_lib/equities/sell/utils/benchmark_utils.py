import numpy as np
import pandas as pd

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

def get_actual_price(data, ticker, size_of_slice, min_backtest_data):
    trade_time = data.iloc[0]['datetime']
    row = min_backtest_data[min_backtest_data['timestamp'] == trade_time]
    max_bid_price = row["max_bid_price"].iloc[0]
    bid_prices = row["bid_prices"].iloc[0]
    bid_sizes = row["bid_sizes"].iloc[0]
    ask_prices = row["ask_prices"].iloc[0]
    min_ask_price = row["min_ask_price"].iloc[0]
    actual_price = calculate_vwap(bid_prices, bid_sizes, size_of_slice)
    avg_ask_price = sum(ask_prices) / len(ask_prices)
    avg_bid_price = sum(bid_prices) / len(bid_prices)
    return actual_price, avg_ask_price, avg_bid_price, max_bid_price,min_ask_price

def compute_components(data, shares, ticker, min_backtest_data):
    actual_price, avg_ask_price, avg_bid_price, max_bid_price, min_ask_price = get_actual_price(data, ticker, shares, min_backtest_data)
    mid_price = (min_ask_price + max_bid_price) / 2
    Spread_cost = (mid_price - actual_price) * shares
    Slippage = (max_bid_price - actual_price) * shares 
    Market_impact = data['transaction_cost'].iat[0] * shares 
    return np.array([Slippage, Market_impact, Spread_cost])

def get_metrics_wrt_twap(IS_twap_arr, IS_arr):
    """
    refence: https://www.ijcai.org/proceedings/2020/0627.pdf (Page 2)
    Calculates various metrics with respect to the Time-Weighted Average Price (TWAP) for the given Implementation Shortfall (IS) arrays.

    Parameters:
    IS_twap_arr (array): The IS array with respect to TWAP.
    IS_arr (array): The actual IS array.

    Returns:
    tuple: A tuple containing the delta IS, IS standard deviation, and the Gain-Loss Ratio (GLR).
    """
    delta_IS = IS_arr - IS_twap_arr
    IS_std = IS_arr.std()

    GLR = delta_IS[delta_IS > 0].mean() / (-1*delta_IS[delta_IS < 0].mean())

    return delta_IS, IS_std, GLR

def calculate_IS(slippage, shares_traded):
    """
    # refence: https://www.ijcai.org/proceedings/2020/0627.pdf (Page 2)
    Calculates the Implementation shortfall (IS) mean of the given rewards.

    Parameters:
    slippage (list): A list of slippage rewards.
    shares_traded (list): A list of shares traded rewards.

    Returns:
    tuple: A tuple containing the IS mean and standard deviation.
    """

    slip_arr = np.vstack(slippage)
    share_arr = np.vstack(shares_traded)

    IS_arr = slip_arr * share_arr 
    return IS_arr 

def get_twap_trades(data, initial_inventory, preferred_timeframe):
    total_steps = len(data)
    preferred_timeframe=min(preferred_timeframe,total_steps)
    twap_shares_per_step = initial_inventory / preferred_timeframe
    remaining_inventory = initial_inventory
    trades = []

    for step in range(min(total_steps, preferred_timeframe)):
        # Distribute shares evenly over time, using floor or round to avoid over-allocation
        size_of_slice = min(int(np.ceil(twap_shares_per_step)), remaining_inventory)
        remaining_inventory -= size_of_slice

        trade = {
            'step': step,
            'timestamp': data.iloc[step]['datetime'],  # Time of trade
            'price': data.iloc[step]['close'],
            'shares': size_of_slice,
            'inventory': remaining_inventory,
            'action': 'sell',  # More descriptive action
        }

        trades.append(trade)

    return pd.DataFrame(trades)

def get_vwap_trades(data, initial_inventory, preferred_timeframe):
    total_volume = data['volume'].iloc[:preferred_timeframe].sum()
    total_steps = len(data)
    remaining_inventory = initial_inventory
    trades = []
    for step in range(min(total_steps, preferred_timeframe)):
        volume_at_step = data['volume'].iloc[step]
        size_of_slice = (volume_at_step / total_volume) * initial_inventory
        size_of_slice = min(int(np.ceil(size_of_slice)), remaining_inventory)
        remaining_inventory -= int(np.ceil(size_of_slice))
        trade = {'step': step,
                 'timestamp': data.iloc[step]['datetime'], # Added time of trade
                 'price': data.iloc[step]['close'],
                 'shares': size_of_slice,
                 'inventory': remaining_inventory,
                 'action': "sell", # 1 indicates 1 step taken, another 1 is useless
                    }
        trades.append(trade)
    return pd.DataFrame(trades)

def simulate_strategy(trades, data, preferred_timeframe, ticker, min_backtest_data):
    """
    Simulates a our strategy based on the provided trades.

    Parameters:
    trades (dataframe): , where each row in trade contains 'shares' and 'action'.

    Returns:
    tuple: A tuple containing four lists: slippage, market impact, liquidity penalty, and transaction cost.
    """
    
    # Get results
    slippage = []
    market_impact = []
    spread_cost = []
    rewards = []
    shares_traded = []
    # Render the final state
    step = 0
    for idx in range(len(trades)):
        shares = trades.iloc[idx]['shares']
        trade_time = trades.iloc[idx]['timestamp'] # Get the time of the trade
        corresponding_data = data[data['datetime'] == trade_time] # Find corresponding time in data
        reward = compute_components(corresponding_data, shares, ticker, min_backtest_data)
        slippage.append(reward[0])
        market_impact.append(reward[1])
        spread_cost.append(reward[2])

        shares_traded.append(shares)
        rewards.append(reward)
    
    imp_shortfall = slippage

    
    def calculate_execution_vwap(prices, sizes):
        # VWAP calculation: sum(price * size) / sum(size)
        if np.sum(sizes) == 0:
            print("Trade sizes sum to zero")
            return 0.0  # Handle edge case

        vwap = np.sum(np.array(prices) * np.array(sizes)) / np.sum(sizes)
        return vwap
    # Calculate VWAP execution price
    trade_prices = trades["price"]
    vwap_execution_price = calculate_execution_vwap(trade_prices, shares_traded)
    # Calculate opportunity cost vs close
    close_price = data['close'].iat[-1]
    open_price = data['open'].iat[0]
    opportunity_cost_vs_close = (close_price - vwap_execution_price) * sum(shares_traded)
    opportunity_cost_vs_open = (open_price - vwap_execution_price) * sum(shares_traded)
    return slippage, market_impact, spread_cost, rewards, imp_shortfall, opportunity_cost_vs_close, opportunity_cost_vs_open
