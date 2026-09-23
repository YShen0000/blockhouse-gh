from backtest_lib.backtest import run_backtest 
from backtest_lib.monte_carlo.MC_backtest import run_monte_carlo_backtest
if __name__ == "__main__":
    # Add desired tests here [ticker, inventory, day_of_backtest, is_sell], if it is a buy backtest is_sell=False
    tests = [['AAPL', 100, '2024-09-09', False],
             ['AAPL', 100, '2024-09-10', True]] 
    for test in tests:
        ticker, inventory, day_of_backtest, is_sell = test[0], test[1], test[2], test[3] 
        run_backtest(ticker, inventory, day_of_backtest, True, is_sell, True, True)
        run_monte_carlo_backtest(ticker, inventory, day_of_backtest, num_simulations=20, is_sell=is_sell, record_data=True, plotter=True)
