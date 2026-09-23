import numpy as np
import pandas as pd

def compute_components(data, alpha, lambda_, shares):
    Slippage = (data['expected_price'] - data['close'])
    Market_Impact = alpha * np.sqrt(shares)
    if data['market_liquidity'] <= 0:
        Liquidity_Penalty = lambda_ * (shares / .1)
    else:
        Liquidity_Penalty = lambda_ * (shares / data['market_liquidity'])
    Transaction_Cost = data['transaction_cost']
    return np.array([Slippage, Market_Impact, Liquidity_Penalty, Transaction_Cost])

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
    twap_shares_per_step = initial_inventory / preferred_timeframe
    remaining_inventory = initial_inventory
    trades = []
    for step in range(min(total_steps, preferred_timeframe)):
        size_of_slice = min(twap_shares_per_step, remaining_inventory)
        remaining_inventory -= int(np.ceil(size_of_slice))
        trade = {'step': step,
                 'price': data.iloc[step]['close'],
                 'shares': size_of_slice,
                 'inventory': remaining_inventory,
                 'action': (1, 1), # 1 indicates 1 step taken, another 1 is useless
                }
        trades.append(trade)
    return pd.DataFrame(trades)

def get_vwap_trades(data, initial_inventory, preferred_timeframe):
    total_volume = data['volume'].sum()
    total_steps = len(data)
    remaining_inventory = initial_inventory
    trades = []
    for step in range(min(total_steps, preferred_timeframe)):
        volume_at_step = data['volume'].iloc[step]
        size_of_slice = (volume_at_step / total_volume) * initial_inventory
        size_of_slice = min(size_of_slice, remaining_inventory)
        remaining_inventory -= int(np.ceil(size_of_slice))
        trade = {'step': step,
                 'price': data.iloc[step]['close'],
                 'shares': size_of_slice,
                 'inventory': remaining_inventory,
                 'action': (1, 1), # 1 indicates 1 step taken, another 1 is useless
                }
        trades.append(trade)
    return pd.DataFrame(trades)

def simulate_strategy(trades, data, preferred_timeframe):
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
    liquidity_penalty = []
    tc = []
    alpha = 4.439584265535017e-06
    lambda_ = 0.05
    rewards = []
    shares_traded = []

    max_len = min(len(data), preferred_timeframe)


    # Render the final state
    step = 0
    for idx in range(len(trades)):
        shares = trades.iloc[idx]['shares']
        timing_of_slice = int(np.ceil(trades.iloc[idx]['action'][0]))
        step += timing_of_slice

        reward = compute_components(data.iloc[step], alpha, lambda_, shares)
        slippage.append(reward[0])
        market_impact.append(reward[1])
        liquidity_penalty.append(reward[2])
        tc.append(reward[3])

        shares_traded.append(shares)

        rewards.append(reward)
    
    IS = calculate_IS(slippage, shares_traded)
    IS_shape= IS.shape[0]
    
    # Concatenate the zeros to the end of the array to make it the same length as the original array
    IS = np.vstack((IS,np.zeros((max_len-IS_shape,1))))

    return slippage, market_impact, liquidity_penalty, tc, rewards, IS

def simulate_strategy_updated(trades, data, preferred_timeframe, env):
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
    Opputunity_cost = []
    spread_cost = []
    tc = []
    alpha = 4.439584265535017e-06
    lambda_ = 0.05
    rewards = []
    shares_traded = []

    begin_vwap_val = data.iloc[0]['VWAP']
    max_len = min(len(data), preferred_timeframe)

    # Filter the data to include only rows from the target timestamp onwards
    # data = data[data['timestamp'] >= start_timestamp]
    vwap_values_set = []
    # Render the final state
    for idx in range(len(trades)):
        shares = trades.iloc[idx]['shares']
        step = trades.iloc[idx]['step']

        vwap_values_set.append(data.iloc[step]['VWAP'])

        reward = compute_components_updated(data, step, env, shares, begin_vwap_val, vwap_values_set)
        slippage.append(reward[0])
        Opputunity_cost.append(reward[1])
        tc.append(reward[2])
        spread_cost.append(reward[3])

        shares_traded.append(shares)

        rewards.append(reward)

    IS = calculate_IS(slippage, shares_traded)
    IS_shape = IS.shape[0]

    # Concatenate the zeros to the end of the array to make it the same length as the original array
    IS = np.vstack((IS, np.zeros((max_len - IS_shape, 1))))

    return slippage, Opputunity_cost, tc, spread_cost,  rewards, IS


def compute_components_updated(data, step, env,  shares, begin_vwap_val, vwap_values_set):
    slippage, spread_cost, transaction_costs = get_slippage(data, step, env, shares)
    Opputunity_cost =   begin_vwap_val - sum(vwap_values_set) / len(vwap_values_set)
    return np.array([slippage, Opputunity_cost, transaction_costs, spread_cost])

def get_slippage(data, current_step, env, size_of_slice ):
    current_timestamp = data['datetime'].iloc[current_step]
    timestamp = pd.to_datetime(current_timestamp).replace(tzinfo=pytz.UTC)
    api_key = 'r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc'
    # Fetch expected price, bid_sizes, ask_sizes, and bid_prices from the Polygon API
    expected_price, min_ask_price, bid_sizes, ask_sizes, bid_prices, ask_prices= env.get_expected_price(api_key,
                                                                                           data['ticker'].iloc[
                                                                                               current_step],
                                                                                           timestamp)

    max_bid_price = expected_price

    if expected_price is None:
        print("Expected price couldn't be fetched, returning no reward.")
        return 0, 0, 0
    else:
        spread_cost = min_ask_price - max_bid_price

        # Calculate VWAP based on bid prices and sizes
    actual_price = env.calculate_vwap(bid_prices, bid_sizes)

    slippage = (expected_price - actual_price) * size_of_slice
    transaction_costs = data['transaction_cost'].iloc[current_step] *size_of_slice

    return slippage, spread_cost, transaction_costs




# ## TWAP MODEL for comparison with our model
# def simulate_twap_strategy(data, initial_inventory, preferred_timeframe):
#     total_steps = len(data)
#     twap_shares_per_step = initial_inventory / preferred_timeframe
#     remaining_inventory = initial_inventory
    
#     # twap_rewards will have a list of lists, where each list will have reward components
#     twap_rewards = []
#     slippage = []
#     market_impact = []
#     liquidity_penalty = []
#     tc = []
    
#     alpha = 4.439584265535017e-06
#     lambda_ = 0.05
    
#     shares_traded = []
    
#     for step in range(min(total_steps, preferred_timeframe)):
#         # print(f"Step:{step} / {min(total_steps, preferred_timeframe)}")
#         size_of_slice = min(twap_shares_per_step, remaining_inventory)
#         remaining_inventory -= int(np.ceil(size_of_slice))
        
#         reward = compute_components(data.iloc[step], alpha, lambda_, size_of_slice)
#         slippage.append(reward[0])
#         market_impact.append(reward[1])
#         liquidity_penalty.append(reward[2])
#         tc.append(reward[3])
#         shares_traded.append(size_of_slice)

#         twap_rewards.append(reward)
        
#         if remaining_inventory <= 0:
#             break
#     twap_rewards = calculate_IS(slippage,shares_traded)
#     return slippage, market_impact, liquidity_penalty, tc, twap_rewards

# # VWAP MODEL for comparison with our model
# def simulate_vwap_strategy(data, initial_inventory, preferred_timeframe):
#     total_volume = data['volume'].sum()
#     total_steps = len(data)
#     remaining_inventory = initial_inventory
    
#     # vwap_rewards will have a list of lists, where each list will have reward components
#     vwap_rewards = []
#     slippage = []
#     market_impact = []
#     liquidity_penalty = []
#     tc = []
    
#     alpha = 4.439584265535017e-06
#     lambda_ = 0.05
#     shares_traded = []
    
#     for step in range(min(total_steps, preferred_timeframe)):
#         volume_at_step = data['volume'].iloc[step]
        
#         # Calculate the number of shares to trade based on the VWAP formula
#         size_of_slice = (volume_at_step / total_volume) * initial_inventory
#         size_of_slice = min(size_of_slice, remaining_inventory)
#         # print(f"Size of slice: {size_of_slice}")
#         remaining_inventory -= int(np.ceil(size_of_slice))
        
#         reward = compute_components(data.iloc[step], alpha, lambda_, size_of_slice)
#         # print(f"Slippage: {reward[0]}")
#         slippage.append(reward[0])
#         market_impact.append(reward[1])
#         liquidity_penalty.append(reward[2])
#         tc.append(reward[3])
        
#         shares_traded.append(size_of_slice)
        
#         vwap_rewards.append(reward)
        
#         if remaining_inventory <= 0:
#             break
#     vwap_rewards = calculate_IS(slippage, shares_traded)
#     return slippage, market_impact, liquidity_penalty, tc, vwap_rewards

# def simulate_our_strategy(trades, data, preferred_timeframe):
#     """
#     Simulates a our strategy based on the provided trades.

#     Parameters:
#     trades (dataframe): , where each row in trade contains 'shares' and 'action'.

#     Returns:
#     tuple: A tuple containing four lists: slippage, market impact, liquidity penalty, and transaction cost.
#     """
    
#     # Get results
#     slippage = []
#     market_impact = []
#     liquidity_penalty = []
#     tc = []
#     alpha = 4.439584265535017e-06
#     lambda_ = 0.05
#     model_rewards = []
#     shares_traded = []

#     # Render the final state
#     step = 0
#     for idx in range(len(trades)):
#         shares = trades.iloc[idx]['shares']
#         timing_of_slice = int(np.ceil(trades.iloc[idx]['action'][0]))
#         step += timing_of_slice

#         reward = compute_components(data.iloc[step], alpha, lambda_, shares)
#         slippage.append(reward[0])
#         market_impact.append(reward[1])
#         liquidity_penalty.append(reward[2])
#         tc.append(reward[3])

#         shares_traded.append(shares)

#         model_rewards.append(reward)
    
#     IS_model = calculate_IS(slippage, shares_traded)


#     return slippage, market_impact, liquidity_penalty, tc, model_rewards, IS_model
