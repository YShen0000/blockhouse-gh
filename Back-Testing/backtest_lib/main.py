from backtest import run_backtest
# from backtest_lib.backtest import run_hw_trade_list
# from backtest_lib.backtest import save_backtest_data
# from backtest_lib.backtest import run_blockhouse_list   
from monte_carlo.MC_backtest import run_monte_carlo_backtest
from plot_backtests import plot_single_backtest
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


if __name__ == "__main__":
    # List of tests with inventory 10000 and is_sell=True
    tests = [['AAPL', 10000, '2024-09-09', True],
            ['AAPL', 10000, '2024-09-09', False]] 
    # tests = [
    #     ['AAPL', 10000, '2024-09-09', True],
    #     ['AAPL', 10000, '2024-09-10', True],
    #     ['AAPL', 10000, '2024-10-11', True],
    #     ['ADBE', 10000, '2024-09-13', True],
    #     ['BA', 10000, '2024-09-13', True],
    #     ['CRWD', 10000, '2024-07-19', True],
    #     ['MSFT', 10000, '2024-07-19', True],
    #     ['NVDA', 10000, '2024-07-26', True],
    #     ['NVDA', 10000, '2024-08-01', True],
    #     ['NVDA', 10000, '2024-08-28', True],
    #     ['NVDA', 10000, '2024-09-09', True]
    # ]
    # tests = [
    #     ['AAPL', 10000, '2024-09-09', False],
    #     ['AAPL', 10000, '2024-09-10', False],
    #     ['AAPL', 10000, '2024-10-11', False],
    #     ['ADBE', 10000, '2024-09-13', False],
    #     ['BA', 10000, '2024-09-13', False],
    #     ['CRWD', 10000, '2024-07-19', False],
    #     ['MSFT', 10000, '2024-07-19', False],
    #     ['NVDA', 10000, '2024-07-26', False],
    #     ['NVDA', 10000, '2024-08-01', False],
    #     ['NVDA', 10000, '2024-08-28', False],
    #     ['NVDA', 10000, '2024-09-09', False]
    # ]
    # run_backtest(ticker, inventory, day_of_backtest, is_equity, is_sell, record_data, plotter)
    #                |         |             |             |          |             |
    #                |         |             |             |          |             +-- True to generate plots
    #                |         |             |             |          +-- True to record backtest data
    #                |         |             |             +-- True if the strategy is a sell strategy
    #                |         |             +-- True if the asset is an equity
    #                |         +-- Date for backtest (e.g., 'YYYY-MM-DD')
    #                +-- Number of shares to trade
    # Stock ticker symbol (e.g., 'AAPL')
    all_results = []
    MonteCarlo=True
    for test in tests:
        ticker, inventory, day_of_backtest, is_sell = test
        model_trades, model_metrics, twap_metrics, vwap_metrics = run_backtest(ticker, inventory, day_of_backtest, True, is_sell, True, False)
        if MonteCarlo==True:
            run_monte_carlo_backtest(ticker, inventory, day_of_backtest, num_simulations=20, is_sell=is_sell, record_data=True, plotter=True)

        backtest_results = pd.DataFrame({
            'Slippage': [model_metrics[0], twap_metrics[0], vwap_metrics[0]],
            'Market Impact': [model_metrics[1], twap_metrics[1], vwap_metrics[1]],
            'Spread Cost': [model_metrics[2], twap_metrics[2], vwap_metrics[2]],
            'Opportunity Cost vs Close': [model_metrics[4], twap_metrics[4], vwap_metrics[4]],
            'Opportunity Cost vs Open': [model_metrics[5], twap_metrics[5], vwap_metrics[5]]
        }, index=['Model', 'TWAP', 'VWAP'])
        
        all_results.append(backtest_results)
        
        print(f"Backtest Results of {inventory} {ticker} on {day_of_backtest} for {'sell' if is_sell else 'buy'}:")
        print(backtest_results)
        print("\n")

        # Plot and save individual backtest results
        plot_single_backtest(backtest_results, ticker, inventory, day_of_backtest, is_sell)

    # Calculate the mean of all backtest results
    backtest_results_mean = pd.concat(all_results).groupby(level=0).mean()
    print("Mean of all backtest results:")
    print(backtest_results_mean)

    # Plot and save mean of all backtest results
    plot_single_backtest(backtest_results_mean, "All", "10000", "All Dates", True)