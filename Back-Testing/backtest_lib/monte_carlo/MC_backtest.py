import numpy as np
import pandas as pd
from scipy import stats
from backtest_lib.backtest import load_backtest_data, equity_backtest
from backtest_lib.monte_carlo.MC_plot import plot_metrics, streamlit_metrics_plot
import csv
def monte_carlo_simulation(day_of_backtest_data, num_simulations=1000):
    # Calculate minute returns
    returns = day_of_backtest_data['close'].pct_change().dropna()
    
    # Calculate mean and standard deviation of returns
    mu = returns.mean()
    sigma = returns.std()
    
    # Generate simulated price paths
    simulated_paths = []
    initial_price = day_of_backtest_data['close'].iloc[0]
    minutes_per_day = len(day_of_backtest_data)
    
    for _ in range(num_simulations):
        prices = [initial_price]
        for _ in range(minutes_per_day - 1):  # -1 because we already have the initial price
            # Generate random return using geometric Brownian motion
            r = np.random.normal(mu, sigma)
            price = prices[-1] * (1 + r)
            prices.append(price)
        simulated_paths.append(prices)
    
    return np.array(simulated_paths)



def create_simulated_minute_data(minute_backtest_data, simulated_path, backtest_data):
    simulated_minute_data = minute_backtest_data.copy()
    simulated_minute_data['close'] = simulated_path
    
    # Calculate the ratio of simulated close to original close
    ratios = simulated_path / backtest_data['close'].values
    
    # Function to adjust prices
    def adjust_prices(prices, ratio):
        return [[price * r for price in price_list] for price_list, r in zip(prices, ratio)]
    
    # Adjust bid and ask prices
    simulated_minute_data['bid_prices'] = adjust_prices(simulated_minute_data['bid_prices'], ratios)
    simulated_minute_data['ask_prices'] = adjust_prices(simulated_minute_data['ask_prices'], ratios)
    
    # Adjust max bid and min ask prices
    simulated_minute_data['max_bid_price'] *= ratios
    simulated_minute_data['min_ask_price'] *= ratios
    
    # Ensure bid prices are always lower than ask prices
    def adjust_bid_ask(row):
        bid_prices = np.array(row['bid_prices'])
        ask_prices = np.array(row['ask_prices'])
        mid_price = row['close']
        
        # Adjust prices to ensure bid < mid < ask
        bid_prices = np.minimum(bid_prices, mid_price * 0.9999)
        ask_prices = np.maximum(ask_prices, mid_price * 1.0001)
        
        return pd.Series({
            'bid_prices': bid_prices.tolist(),
            'ask_prices': ask_prices.tolist(),
            'max_bid_price': np.max(bid_prices),
            'min_ask_price': np.min(ask_prices)
        })
    
    # Apply the adjustment
    adjusted = simulated_minute_data.apply(adjust_bid_ask, axis=1)
    simulated_minute_data[['bid_prices', 'ask_prices', 'max_bid_price', 'min_ask_price']] = adjusted
    
    return simulated_minute_data

# Function to append rows of various model data to the CSV file
def append_metric_rows(filename, ticker, date, shares, m_metrics_sum, t_metrics_sum, v_metrics_sum):
    with open(filename, mode='a', newline='') as file:  # 'a' mode opens the file for appending
        writer = csv.writer(file)
        writer.writerow(['Model', ticker, date, shares, m_metrics_sum[0], m_metrics_sum[1], m_metrics_sum[2], m_metrics_sum[3], m_metrics_sum[4], m_metrics_sum[5]])
        writer.writerow(['TWAP', ticker, date, shares, t_metrics_sum[0], t_metrics_sum[1], t_metrics_sum[2], t_metrics_sum[3], t_metrics_sum[4], t_metrics_sum[5]])
        writer.writerow(['VWAP', ticker, date, shares, v_metrics_sum[0], v_metrics_sum[1], v_metrics_sum[2], v_metrics_sum[3], v_metrics_sum[4], v_metrics_sum[5]])
    
    print(f"Model rows added to '{filename}'.")
    return
def create_csv_file(filename):
    # Column headers
    headers = [
        'trader_model', 
        'ticker', 
        'date', 
        'shares', 
        'slippage', 
        'market_impact', 
        'spread_cost', 
        'imp_shortfall',
        'opportunity_cost_vs_close',
        'opportunity_cost_vs_open'
    ]

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)  # Write the headers
    
    print(f"CSV file '{filename}' created with headers")
    return 

def run_monte_carlo_backtest(ticker='AAPL', inventory=1000, day_of_backtest='2024-09-10', num_simulations=5, is_sell=True, record_data=False, plotter=False):
    print(f"Running Monte Carlo Simulation for {ticker} on {day_of_backtest}")

    # Load backtest data
    day_of_backtest_data, minute_backtest_data = load_backtest_data(ticker, day_of_backtest)

    # Run Monte Carlo simulation
    simulated_paths = monte_carlo_simulation(day_of_backtest_data, num_simulations)
    
    metrics_num = 6
    # Initialize arrays to store results
    model_results = np.zeros((num_simulations, metrics_num))
    twap_results = np.zeros((num_simulations, metrics_num))
    vwap_results = np.zeros((num_simulations, metrics_num))
    
    for i, path in enumerate(simulated_paths):
        simulated_minute_data = create_simulated_minute_data(minute_backtest_data, path, day_of_backtest_data)
        
        # Save the first simulated minute data to CSV
        if i == 0:
            simulated_minute_data.to_csv(f'{ticker}_{day_of_backtest}_simulated_minute_data.csv', index=False)
            print(f"First simulated minute data saved to {ticker}_{day_of_backtest}_simulated_minute_data.csv")
        
        # Run backtest on simulated data
        _, model_metrics, twap_metrics, vwap_metrics = equity_backtest(
            ticker, inventory, day_of_backtest, day_of_backtest_data, simulated_minute_data, is_sell
        )
        
        # Store results
        model_results[i] = model_metrics
        twap_results[i] = twap_metrics
        vwap_results[i] = vwap_metrics
    
    # Calculate average results
    avg_model_results = np.mean(model_results, axis=0)
    avg_twap_results = np.mean(twap_results, axis=0)
    avg_vwap_results = np.mean(vwap_results, axis=0)
    
    mc_results = pd.DataFrame({
        'Model': avg_model_results,
        'TWAP': avg_twap_results,
        'VWAP': avg_vwap_results
    }, index=['Slippage', 'Market Impact', 'Spread Cost', 'Imp Shortfall', "Opportunity Cost vs Close", "Opportunity Cost vs Open"])
    
    if record_data:
        # CSV file that stores all metrics
        filename = 'monte_carlo_metrics.csv'
        create_csv_file(filename)
        # Add data to csv file
        append_metric_rows(filename, ticker, day_of_backtest, inventory, avg_model_results, avg_twap_results, avg_vwap_results)

        if plotter:
            plot_metrics(filename, is_sell, is_equity=True, is_monte_carlo=True)
            streamlit_metrics_plot(filename, is_sell, is_equity=True, is_monte_carlo=True)    
    return mc_results

# if __name__ == "__main__":

#     tests = [['AAPL', 1000, '2024-09-10', True]] 
#     for test in tests:
#         ticker, inventory, day_of_backtest, is_sell = test[0], test[1], test[2], test[3] 
#         run_monte_carlo_backtest(ticker, inventory, day_of_backtest, num_simulations=20, is_sell=is_sell, record_data=True, plotter=True)
