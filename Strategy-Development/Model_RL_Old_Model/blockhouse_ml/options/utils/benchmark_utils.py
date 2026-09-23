import numpy as np
import pandas as pd
import pytz
# from icecream import ic

def compute_components(data, step, env,  shares, begin_vwap_val, vwap_values_set= None):
    slippage, spread_cost, transaction_costs = get_slippage(data, step, env, shares)
    if vwap_values_set is None:
        Opportunity_cost = 0
    else:
        Opportunity_cost =   begin_vwap_val - sum(vwap_values_set) / len(vwap_values_set)
    return np.array([slippage, Opportunity_cost, transaction_costs, spread_cost])

def compute_components_micro(data, alpha, lambda_, shares, execution_price):
    Slippage = (data['expected_price'] - execution_price)
    Market_Impact = alpha * np.sqrt(shares)
    # Liquidity_Penalty = lambda_ * (shares / data['market_liquidity'])
    Transaction_Cost = data['transaction_cost']
    return np.array([Slippage, Market_Impact, Transaction_Cost])

# def get_slippage(data, current_step, env, size_of_slice ):
#     current_timestamp = data['datetime'].iloc[current_step]
#     timestamp = pd.to_datetime(current_timestamp).replace(tzinfo=pytz.UTC)
#     api_key = 'r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc'
#     # Fetch expected price, bid_sizes, ask_sizes, and bid_prices from the Polygon API
#     expected_price, bid_sizes, ask_sizes, bid_prices, ask_prices= env.get_expected_price(api_key,
#                                                                                            data['contract'].iloc[
#                                                                                                current_step],
#                                                                                            timestamp)

#     max_bid_price = expected_price

#     if expected_price is None:
#         print("Expected price couldn't be fetched, returning no reward.")
#         return 0, 0, 0
#     else:
#         spread_cost = np.min(ask_prices) - np.max(bid_prices)

#         # Calculate VWAP based on bid prices and sizes
#     actual_price = env.calculate_vwap(bid_prices, bid_sizes)

#     slippage = (expected_price - actual_price) * size_of_slice
#     transaction_costs = data['transaction_cost'].iloc[current_step] *size_of_slice


#     return slippage, spread_cost, transaction_costs


def get_slippage(data, current_step, env, size_of_slice ):
    current_timestamp = data['datetime'].iloc[current_step]
    timestamp = pd.to_datetime(current_timestamp).replace(tzinfo=pytz.UTC)
    api_key = 'r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc'
    # Fetch expected price, bid_sizes, ask_sizes, and bid_prices from the Polygon API
    expected_price = data['expected_price_sell'].iloc[current_step]
    actual_price = data['actual_price'].iloc[current_step]
    spread_cost = data['spread_cost'].iloc[current_step]

    slippage = (expected_price - actual_price) * size_of_slice
    transaction_costs = data['transaction_cost'].iloc[current_step] * size_of_slice


    return slippage, spread_cost, transaction_costs

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

    GLR = delta_IS[delta_IS > 0].mean() / (-1 * delta_IS[delta_IS < 0].mean())

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
                 'action': (1, 1),  # 1 indicates 1 step taken, another 1 is useless
                 }
        trades.append(trade)
    return pd.DataFrame(trades)



def get_vwap_trades(data, initial_inventory, preferred_timeframe, if_limit = False):
    total_volume = data['volume'].iloc[:preferred_timeframe].sum()
    total_steps = len(data)
    remaining_inventory = initial_inventory
    trades = []
    for step in range(min(total_steps, preferred_timeframe)):
        volume_at_step = data['volume'].iloc[step]
        size_of_slice = (volume_at_step / total_volume) * initial_inventory
        size_of_slice = min(size_of_slice, remaining_inventory)
        remaining_inventory -= int(np.ceil(size_of_slice))
        if if_limit:
            price = data.iloc[step]['close'] * 1.05
        else:
            price = data.iloc[step]['close']

        trade = {'step': step,
                 'price': price,
                 'shares': size_of_slice,
                 'inventory': remaining_inventory,
                 'action': (1, 1),  # 1 indicates 1 step taken, another 1 is useless
                 }
        trades.append(trade)
    return pd.DataFrame(trades)





def simulate_strategy(trades, data, preferred_timeframe, env):
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

    vwap_values_set = []
    try:
        begin_vwap_val = data.iloc[0]['VWAP']
    except:
        begin_vwap_val = 0

    max_len = min(len(data), preferred_timeframe)

    # Filter the data to include only rows from the target timestamp onwards
    # data = data[data['timestamp'] >= start_timestamp]
    vwap_values_set = []
    # Render the final state
    for idx in range(len(trades)):
        shares = trades.iloc[idx]['shares']
        step = trades.iloc[idx]['step']

        try:
            vwap_values_set.append(data.iloc[step]['VWAP'])
        except:
            vwap_values_set = None
        reward = compute_components(data, step, env, shares, begin_vwap_val, vwap_values_set)
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

def simulate_strategy_micro(trades, results, preferred_timeframe):

    slippage = []
    market_impact = []
    liquidity_penalty = []
    tc = []
    alpha = 4.439584265535017e-06
    lambda_ = 0.05
    rewards = []
    shares_traded = []

    max_len = preferred_timeframe

    # Render the final state
    step = 0
    for idx in range(len(trades)):
        curr_results = results[idx]
        shares = trades.iloc[idx]['shares']

        # reward = compute_components_micro(trades.iloc[idx], alpha, lambda_, shares, curr_results['execution_price'])

        Slippage = (trades.iloc[idx]['expected_price'] - curr_results['execution_price'])
        Market_Impact = alpha * np.sqrt(shares)
        Transaction_Cost = trades.iloc[idx]['transaction_cost']

        slippage.append(Slippage)
        market_impact.append(Market_Impact)
        tc.append(Transaction_Cost)

        shares_traded.append(shares)

    IS = calculate_IS(slippage, shares_traded)
    IS_shape = IS.shape[0]

    # Concatenate the zeros to the end of the array to make it the same length as the original array
    IS = np.vstack((IS, np.zeros((max_len - IS_shape, 1))))

    return slippage, market_impact, liquidity_penalty, tc, rewards, IS
