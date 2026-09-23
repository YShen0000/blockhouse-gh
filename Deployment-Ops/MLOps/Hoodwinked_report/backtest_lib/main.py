from backtest_lib.backtest import run_backtest
from backtest_lib.backtest import run_hw_trade_list
from backtest_lib.backtest import save_backtest_data
from backtest_lib.backtest import run_blockhouse_list   

if __name__ == "__main__":
    # Local call to replicate the Hoodwinked Report Call
    # run_hw_trade_list('tests.csv')

    # Use to gather metrics comparing our model vs TWAP vs. VWAP 
    # run_blockhouse_list('tests.csv')

    # # Use this to save a ticker and day you want to backtest and save file to BacktestData
    # save_backtest_data('BA', '2024-09-13')

    # Call to run backtest for manual input
    # Add desired tests here [ticker, inventory, day_of_backtest, is_sell], if it is a buy backtest is_sell=False
    tests = [['AAPL', 100, '2024-09-09', False],
             ['AAPL', 100, '2024-09-09', True]] 
    for test in tests:
        ticker, inventory, day_of_backtest, is_sell = test[0], test[1], test[2], test[3] 
        run_backtest(ticker, inventory, day_of_backtest, True, is_sell, True, True)
