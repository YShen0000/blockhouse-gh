import numpy as np
import pandas as pd
import pytz
import numpy as np
import pandas as pd
from polygon import RESTClient

def get_expected_price(symbol, timestamp):
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

    # Added minimum ask price
    return max_bid_price, bid_prices, bid_sizes, ask_prices, ask_sizes, min(ask_prices)

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
    if (min_backtest_data is not None):
        trade_time = data.iloc[0]['datetime']
        row = min_backtest_data[min_backtest_data['timestamp'] == trade_time]
        max_bid_price = row["max_bid_price"].iloc[0]
        bid_prices = row["bid_prices"].iloc[0]
        bid_sizes = row["bid_sizes"].iloc[0]
        ask_prices = row["ask_prices"].iloc[0]
        # ask_sizes = row["ask_sizes"]
        # min_ask_price = row["min_ask_price"]
    else:
        timestamp = data['datetime'].iloc[0]
        max_bid_price, bid_prices, bid_sizes, ask_prices, ask_sizes, min_ask_price = get_expected_price(symbol=ticker, timestamp=timestamp)
    actual_price = calculate_vwap(bid_prices, bid_sizes, size_of_slice)
    avg_ask_price = sum(ask_prices) / len(ask_prices)
    avg_bid_price = sum(bid_prices) / len(bid_prices)
    return actual_price, avg_ask_price, avg_bid_price, max_bid_price

def compute_components(data, alpha, lambda_, shares, ticker, is_sell, min_backtest_data):
    actual_price, avg_ask_price, avg_bid_price, max_bid_price = get_actual_price(data, ticker, shares, min_backtest_data)
    Spread_cost = (avg_ask_price - avg_bid_price) * shares
    if (is_sell):
        Slippage = (max_bid_price - actual_price) * shares 
    else:
        Slippage = (actual_price - max_bid_price) * shares # Should be negative, flippeds
    Market_Impact = alpha * np.sqrt(shares)
    Transaction_Cost = data['transaction_cost'].iat[0] * shares 
    return np.array([Slippage, Market_Impact, Transaction_Cost, Spread_cost])

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
                 'timestamp': data.iloc[step]['datetime'], # Added time of trade
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
                 'timestamp': data.iloc[step]['datetime'], # Added time of trade
                 'price': data.iloc[step]['close'],
                 'shares': size_of_slice,
                 'inventory': remaining_inventory,
                 'action': (1, 1), # 1 indicates 1 step taken, another 1 is useless
                }
        trades.append(trade)
    return pd.DataFrame(trades)

def simulate_strategy(trades, data, preferred_timeframe, ticker, is_sell, min_backtest_data=None):
    """
    Simulates a our strategy based on the provided trades.

    Parameters:
    trades (dataframe): , where each row in trade contains 'shares' and 'action'.

    Returns:
    tuple: A tuple containing four lists: slippage, market impact, liquidity penalty, and transaction cost.
    """
    slippage = []
    market_impact = []
    spread_cost = []
    tc = []
    alpha = 4.439584265535017e-06
    lambda_ = 0.05
    rewards = []
    shares_traded = []

    # Render the final state
    step = 0
    for idx in range(len(trades)):
        shares = trades.iloc[idx]['shares']
        trade_time = trades.iloc[idx]['timestamp'] # Get the time of the trade
        corresponding_data = data[data['datetime'] == trade_time] # Find corresponding time in data
        reward = compute_components(corresponding_data, alpha, lambda_, shares, ticker, is_sell, min_backtest_data)
        slippage.append(reward[0])
        market_impact.append(reward[1])
        tc.append(reward[2])
        spread_cost.append(reward[3])

        shares_traded.append(shares)

        rewards.append(reward)
    
    # IS = calculate_IS(slippage, shares_traded)
    # IS_shape= IS.shape[0]
    
    # # Concatenate the zeros to the end of the array to make it the same length as the original array
    # IS = np.vstack((IS,np.zeros((max_len-IS_shape,1))))
    imp_shortfall = slippage

    return slippage, market_impact, spread_cost, tc, rewards, imp_shortfall