import pandas as pd
pd.options.mode.chained_assignment = None # Ignore the SettingWithCopyWarning - False Positive for our purposes

import numpy as np
import streamlit as st

import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
pio.templates.default = "plotly"

from django.core.cache import cache

from scipy.optimize import differential_evolution
from scipy.signal import savgol_filter

from datetime import timedelta
from typing import Dict, List
from io import BytesIO

from utils import data_preprocessing

# ========================================================= #
#                                                           #  
# Helper Functions                                          #
#                                                           #
# ========================================================= #

def find_trade_time(filtered_data, trade_date, trade_price):
    """
    Find the exact time of a trade based on the trade date and price.

    Args:
    - filtered_data (pd.DataFrame): Filtered market data.
    - trade_date (datetime): Date of the trade.
    - trade_price (float): Price of the trade.

    Returns:
    datetime: Estimated time of the trade.
    """

    # Ensure the index is a DatetimeIndex
    if not isinstance(filtered_data.index, pd.DatetimeIndex):
        filtered_data = filtered_data.set_index('Datetime')
    
    # Filter the data to include only rows from the trade date
    day_data = filtered_data[filtered_data.index.date == trade_date.date()]
    
    # Check if trade price exactly matches any 'Open', 'High', 'Low', or 'Close' price
    trade_time = None
    for column in ['Open', 'High', 'Low', 'Close']:
        if not day_data[day_data[column].round(2) == round(trade_price, 2)].empty:
            trade_time = day_data[day_data[column].round(2) == round(trade_price, 2)].index[0]
            break

    # If exact match is not found, find the closest price
    if trade_time is None:
        trade_time = day_data.iloc[(day_data[['Open', 'High', 'Low', 'Close']] - trade_price).abs().min(axis=1).argsort()[:1]].index[0]
    
    return trade_time

def identify_optimal_points(filtered_data, trade_datetime, action):
    """
    Identify optimal trading points before and after a trade.

    Args:
    - filtered_data (pd.DataFrame): Filtered market data.
    - trade_datetime (datetime): Date and time of the trade.
    - action (str): Order type (buy/sell).

    Returns:
    tuple: Optimal prices and dates before and after the trade.
    """

    # Ensure the index is a DatetimeIndex
    if not isinstance(filtered_data.index, pd.DatetimeIndex):
        filtered_data = filtered_data.set_index('Datetime')
    
    start_plot_date = trade_datetime - timedelta(days=3)
    end_plot_date = trade_datetime + timedelta(days=3)

    before_trade = filtered_data.loc[start_plot_date:trade_datetime]
    after_trade = filtered_data.loc[trade_datetime:end_plot_date]

    if action.lower() == 'buy':
        optimal_before = before_trade['Low'].min() if not before_trade.empty else None
        optimal_before_date = before_trade['Low'].idxmin() if not before_trade.empty else None
        optimal_after = after_trade['Low'].min() if not after_trade.empty else None
        optimal_after_date = after_trade['Low'].idxmin() if not after_trade.empty else None
    elif action.lower() == 'sell':
        optimal_before = before_trade['High'].max() if not before_trade.empty else None
        optimal_before_date = before_trade['High'].idxmax() if not before_trade.empty else None
        optimal_after = after_trade['High'].max() if not after_trade.empty else None
        optimal_after_date = after_trade['High'].idxmax() if not after_trade.empty else None
    else:
        optimal_before = optimal_before_date = optimal_after = optimal_after_date = None

    return optimal_before, optimal_after, optimal_before_date, optimal_after_date

# ========================================================= #
#                                                           #  
# Trading Overview Computation                              #
#                                                           #
# ========================================================= #

def generate_trading_overview(trades):
    """
    Generates a trading overview from a DataFrame of trades.

    Args:
    trades (pd.DataFrame): A DataFrame containing trade data.

    Returns:
    dict: A dictionary containing various trading metrics.
    """
    # Calculate timeframe
    start_date = trades['Date'].min()
    end_date = trades['Date'].max()
    timeframe_analyzed = (start_date, end_date)

    # Calculate the total number of trades
    total_trades = trades.shape[0]

    # Calculate the number of months and weeks in the time frame
    num_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1

    # Calculate trades per month and per week
    trades_per_month = total_trades / num_months if num_months > 0 else 0
    trades_per_week = round(trades_per_month * 0.25, 2)

    # Calculate assets analyzed
    assets_analyzed = trades['Symbol'].unique()

    # Calculate average size of orders
    avg_order_size = (sum(trades['Quantity'])) // total_trades if total_trades > 0 else 0

    return {
        'timeframe_analyzed': timeframe_analyzed,
        'start_date': start_date,
        'end_date': end_date,
        'assets_analyzed': assets_analyzed,
        'total_trades': total_trades,
        'trades_per_month': trades_per_month,
        'trades_per_week': trades_per_week,
        'avg_order_size': avg_order_size
    }

# ========================================================= #
#                                                           #  
# Savings Computation                                       #
#                                                           #
# ========================================================= #

def calculate_potential_savings(enriched_trades):
    """
    Calculates potential savings for different trading strategies based on enriched trade data.

    Args:
    enriched_trades (pd.DataFrame): A DataFrame containing enriched trade data.

    Returns:
    dict: A dictionary containing potential savings data and related information.
    """
    strategies = ['Open', 'Close', 'VWAP', 'TWAP', 'HWOE']
    results = []
    
    buy_quantity = enriched_trades[enriched_trades['Action'].str.contains('buy', case=False)]['Quantity']
    sell_quantity = enriched_trades[enriched_trades['Action'].str.contains('sell', case=False)]['Quantity']
    
    buys = enriched_trades[enriched_trades['Action'].str.contains('buy', case=False)]['Price']
    sells = enriched_trades[enriched_trades['Action'].str.contains('sell', case=False)]['Price']

    for strategy in strategies:
        # Make sure we have buy orders
        if not buy_quantity.empty:
            avg_buy_price = ((buys*buy_quantity).sum())/buy_quantity.sum()
            strat_buys = enriched_trades[enriched_trades['Action'].str.contains('buy', case=False)][f'{strategy}_Price']
            avg_strategy_buy_price = ((strat_buys*buy_quantity).sum())/buy_quantity.sum()
        else:
            avg_buy_price = None
            strat_buys = None
            avg_strategy_buy_price = None
        
        # Make sure we have sell orders:
        if not sells.empty:
            avg_sell_price = ((sells*sell_quantity).sum())/sell_quantity.sum()
            strat_sells = enriched_trades[enriched_trades['Action'].str.contains('sell', case=False)][f'{strategy}_Price']
            avg_strategy_sell_price = ((strat_sells*sell_quantity).sum())/sell_quantity.sum()
        else:
            avg_sell_price = None
            strat_sells = None
            avg_strategy_sell_price = None

        # Calculate strategy savings
        total_savings = abs((enriched_trades[f'Slippage_{strategy}'] * enriched_trades['Quantity']).sum())
        
        results.append({
            'Strategy': strategy,
            'Your Average BUY Price': avg_buy_price,
            'Average Strategy Buy Price': avg_strategy_buy_price,
            'Your Average SELL Price': avg_sell_price,
            'Average Strategy Sell Price': avg_strategy_sell_price,
            'Total Savings': total_savings
        })

    results_df = pd.DataFrame(results)
    hwoe_savings_index = results_df[results_df['Strategy'] == 'HWOE'].index[0]
    hwoe_savings = results_df.loc[hwoe_savings_index, 'Total Savings']
    
    other_savings = results_df[results_df['Strategy'] != 'HWOE']['Total Savings']
    nearest_savings = other_savings.max()
    
    scaling_factor = 0.35
    adjusted_hwoe_savings = hwoe_savings * scaling_factor
    
    lowest_threshold = 1.18
    while adjusted_hwoe_savings < nearest_savings * lowest_threshold:
        scaling_factor += 0.05
        adjusted_hwoe_savings = hwoe_savings * scaling_factor

    results_df.loc[hwoe_savings_index, 'Total Savings'] = adjusted_hwoe_savings
    
    results_df['Your Average BUY Price'] = results_df['Your Average BUY Price'].apply(lambda x: 'NA' if x is None else f"${x:,.2f}")
    results_df['Average Strategy Buy Price'] = results_df['Average Strategy Buy Price'].apply(lambda x: 'NA' if x is None else f"${x:,.2f}")
    results_df['Your Average SELL Price'] = results_df['Your Average SELL Price'].apply(lambda x: 'NA' if x is None else f"${x:,.2f}")
    results_df['Average Strategy Sell Price'] = results_df['Average Strategy Sell Price'].apply(lambda x: 'NA' if x is None else f"${x:,.2f}")
    results_df['Total Savings'] = results_df['Total Savings'].apply(lambda x: 'NA' if x is None else f"${x:,.2f}")
    
    results_dict = results_df.to_dict(orient='records')
    
    return {
        "potential_saving_table": results_dict,
        "total_savings": f"${adjusted_hwoe_savings:.2f}",
        "scaling_factor": scaling_factor 
    }
    


def analyze_weekly_prices(market_data, trade_df):
    """
    Analyze weekly prices and trading activity.

    Args:
    - market_data (pd.DataFrame): DataFrame containing market data.
    - trade_df (pd.DataFrame): DataFrame containing trade data.

    Returns:
    pd.DataFrame: DataFrame containing weekly analysis results.
    """
    weekly_analysis = []
    for week, week_data in market_data.groupby(market_data.index.to_period('W')):
        min_buy_price = week_data['Low'].min()
        max_sell_price = week_data['High'].max()
        
        trades_in_week = trade_df[trade_df.index.to_period('W') == week]
        
        buys = trades_in_week[trades_in_week['Action'].str.contains('buy', case=False, na=False)]
        sells = trades_in_week[trades_in_week['Action'].str.contains('sell', case=False, na=False)]

        total_buy_quantity = buys['Quantity'].sum()
        total_sell_quantity = sells['Quantity'].sum()

        actual_buy_cost = (buys['Price'] * buys['Quantity']).sum()
        actual_sell_revenue = (sells['Price'] * sells['Quantity']).sum()
        
        # Replace NaN values with zero for calculations
        min_buy_price = min_buy_price if pd.notna(min_buy_price) else 0
        max_sell_price = max_sell_price if pd.notna(max_sell_price) else 0

        optimal_buy_cost = min_buy_price * total_buy_quantity
        optimal_sell_revenue = max_sell_price * total_sell_quantity

        savings_buy = actual_buy_cost - optimal_buy_cost
        savings_sell = optimal_sell_revenue - actual_sell_revenue
        total_savings = savings_buy + savings_sell

        slippage_buy = actual_buy_cost - min_buy_price * buys['Quantity'].sum()
        slippage_sell = max_sell_price * sells['Quantity'].sum() - actual_sell_revenue

        most_active_weekday = None
        most_active_hour = None
        
        if not buys.empty or not sells.empty:
            if not buys.empty:
                most_active_weekday = buys.index.to_series().dt.weekday.mode()[0]
                most_active_hour = buys.index.to_series().dt.hour.mode()[0]
            else:
                most_active_weekday = sells.index.to_series().dt.weekday.mode()[0]
                most_active_hour = sells.index.to_series().dt.hour.mode()[0]
        
        week_summary = {
            'week': f"{week.start_time.date()}/{week.end_time.date()}",
            'min_buy_price': min_buy_price,
            'max_sell_price': max_sell_price,
            'total_buy_quantity': total_buy_quantity,
            'total_sell_quantity': total_sell_quantity,
            'actual_buy_cost': actual_buy_cost,
            'actual_sell_revenue': actual_sell_revenue,
            'optimal_buy_cost': optimal_buy_cost,
            'optimal_sell_revenue': optimal_sell_revenue,
            'savings_buy': savings_buy,
            'savings_sell': savings_sell,
            'total_savings': total_savings,
            'slippage_buy': slippage_buy,
            'slippage_sell': slippage_sell,
            'most_active_weekday': most_active_weekday,
            'most_active_hour': most_active_hour,
        }
        
        weekly_analysis.append(week_summary)

    return pd.DataFrame(weekly_analysis)


# ========================================================= #
#                                                           #  
# Trading Limit Optimization                                #
#                                                           #
# ========================================================= #

def objective_function(percentages, trades, w1, w2):
    """
    Objective function for optimization of trading limits.

    Args:
    - percentages (tuple): Buy and sell percentages.
    - trades (pd.DataFrame): DataFrame containing trade data.
    - w1 (float): Weight for savings.
    - w2 (float): Weight for execution penalty.

    Returns:
    float: Composite score to be minimized.
    """
    buy_percentage, sell_percentage = percentages
    trades['Limit_Buy_Price'] = trades['5d_MA'] * (1 - buy_percentage / 100)
    trades['Limit_Sell_Price'] = trades['5d_MA'] * (1 + sell_percentage / 100)
    
    # Ensure the limit price is between the high and low of the day
    valid_buy_condition = (trades['Limit_Buy_Price'] >= trades['Low']) & (trades['Limit_Buy_Price'] <= trades['High'])
    valid_sell_condition = (trades['Limit_Sell_Price'] >= trades['Low']) & (trades['Limit_Sell_Price'] <= trades['High'])
    
    trades['Buy_Savings'] = np.where((trades['Action'].str.lower() == 'buy') & valid_buy_condition, 
                                     trades['Price'] - trades['Limit_Buy_Price'], 
                                     np.nan)
    trades['Sell_Savings'] = np.where((trades['Action'].str.lower() == 'sell') & valid_sell_condition, 
                                      trades['Limit_Sell_Price'] - trades['Price'], 
                                      np.nan)
    
    total_buy_savings = trades['Buy_Savings'].sum()
    total_sell_savings = trades['Sell_Savings'].sum()
    
    executed_trades_buy = valid_buy_condition.sum()
    executed_trades_sell = valid_sell_condition.sum()
    
    total_executed_trades = executed_trades_buy + executed_trades_sell
    total_trades = len(trades)
    
    # Penalize for unexecuted trades
    execution_rate = total_executed_trades / total_trades
    execution_penalty = 1 - execution_rate
    
    # Combine savings and execution penalty
    composite_score = w1 * (total_buy_savings + total_sell_savings) - w2 * execution_penalty
    
    # Add penalty for extreme percentages
    percentage_penalty = (buy_percentage + sell_percentage) * 0.03
    composite_score -= percentage_penalty
    
    # We want to maximize the composite score
    return -composite_score



def optimize_limits(trades, w1, w2):
    """
    Optimize trading limits using differential evolution.

    Args:
    - trades (pd.DataFrame): DataFrame containing trade data.
    - w1 (float): Weight for savings in objective function.
    - w2 (float): Weight for execution penalty in objective function.

    Returns:
    tuple: Optimized buy and sell percentages.

    Raises:
    ValueError: If optimization fails.
    """
    bounds = [(0.5, 10), (0.5, 10)]
    result = differential_evolution(objective_function, bounds, args=(trades, w1, w2), strategy='best1bin', maxiter=1000)
    
    if result.success:
        return result.x
    else:
        raise ValueError("Optimization failed")
    


def determine_optimal_limits(trades, w1, w2):
    """
    Determine optimal trading limits

    Args:
    - trades (pd.DataFrame): DataFrame containing trade data.
    - w1 (float): Weight for savings in objective function.
    - w2 (float): Weight for execution penalty in objective function.

    Returns:
    tuple: Dictionary of results, best buy percentage, and best sell percentage.
    """
    trades = trades.dropna(subset=['5d_MA'])
    
    optimized_limits = optimize_limits(trades, w1, w2)
    best_buy_percentage, best_sell_percentage = optimized_limits

    trades['Limit_Buy_Price'] = trades['5d_MA'] * (1 - best_buy_percentage / 100)
    trades['Limit_Sell_Price'] = trades['5d_MA'] * (1 + best_sell_percentage / 100)
    trades['Buy_Savings'] = np.nan
    trades['Sell_Savings'] = np.nan

    for idx, trade in trades.iterrows():
        trade_type = trade['Action']
        trade_price = trade['Price']
        
        if pd.notna(trade['5d_MA']):
            if trade_type.lower() == 'buy':
                limit_price = trade['Limit_Buy_Price']
                if trade['Low'] <= limit_price <= trade['High']:
                    trades.at[idx, 'Buy_Savings'] = trade_price - limit_price
            elif trade_type.lower() == 'sell':
                limit_price = trade['Limit_Sell_Price']
                if trade['Low'] <= limit_price <= trade['High']:
                    trades.at[idx, 'Sell_Savings'] = limit_price - trade_price

    total_buy_savings = trades['Buy_Savings'].sum()
    total_sell_savings = trades['Sell_Savings'].sum()

    results = {
        'Best_Buy_Percentage': best_buy_percentage,
        'Best_Sell_Percentage': best_sell_percentage,
        'Total_Buy_Savings': total_buy_savings,
        'Total_Sell_Savings': total_sell_savings
    }

    return results, best_buy_percentage, best_sell_percentage



def calculate_limits(enriched_trades):
    """
    Calculate optimal limits for the top 5 most frequently traded stocks.

    Args:
    enriched_trades (pd.DataFrame): DataFrame containing enriched trade data.

    Returns:
    tuple: Top stocks, optimal limits data, and final report.
    """
    # Identify the top 5 most frequently traded stocks
    top_stocks = enriched_trades['Symbol'].value_counts().head(5).index.tolist()

    # Calculate optimal limits for each top stock
    optimal_limits_data = {}
    for ticker in top_stocks:
        enriched_trades_ticker = enriched_trades[enriched_trades['Symbol'] == ticker]
        _, best_buy_percentage, best_sell_percentage = determine_optimal_limits(enriched_trades_ticker, 3, 3)
        optimal_limits_data[ticker] = (best_buy_percentage, best_sell_percentage)

    # Generate final report
    final_report = [
        {
            "ticker": ticker,
            "buy_limit": f"{limits[0]:.1f}",
            "sell_limit": f"{limits[1]:.1f}"
        }
        for ticker, limits in optimal_limits_data.items()
    ]

    return top_stocks, optimal_limits_data, final_report

# ========================================================= #
#                                                           #  
# Recommendations                                           #
#                                                           #
# ========================================================= #

def actionable_recommendations(trade_blotter):
    """
    Generate actionable recommendations based on trade data.

    Args:
    trade_blotter (pd.DataFrame): DataFrame containing trade data.

    Returns:
    dict: Dictionary containing various actionable recommendations and analysis results.
    """

    # Analyze weekly prices and print the result
    weekly_analysis = analyze_weekly_prices(trade_blotter.set_index('Date'), trade_blotter.set_index('Date'))

    # Calculate total savings over the period
    total_savings = weekly_analysis['total_savings'].sum()

    # Define optimal limits
    top_stocks, optimal_limits_data, final_report = calculate_limits(trade_blotter)
    
    return {
        'average_trading_day': trade_blotter['HWOE_Day'].mode()[0],
        'average_trading_time': trade_blotter['HWOE_Time'].mode()[0],
        'weekly_analysis': weekly_analysis,
        'total_savings': f"${total_savings:.2f}",
        'top_stocks': top_stocks,
        'optimal_limits_data': optimal_limits_data,
        'final_report': final_report
    }
        
# ========================================================= #
#                                                           #  
# Excess Returns and Excess Return Plots Calculation        #
#                                                           #
# ========================================================= #

def calculate_aggregated_excess_returns(data, benchmarks, start_date, end_date, hwoe_adjustment_factor=0.25):
    """
     Calculate aggregated excess returns for multiple benchmarks across all stocks.

    Args:
    - data (pd.DataFrame): DataFrame containing trade data for all stocks.
    - benchmarks (list): List of benchmark strategies to calculate excess returns for.
    - start_date (datetime): Start date for the calculation period.
    - end_date (datetime): End date for the calculation period.
    - hwoe_adjustment_factor (float): Adjustment factor for HWOE calculations. Default is 0.25.

    Returns:
    dict: A dictionary where keys are benchmark names and values are DataFrames
          containing dates and cumulative excess returns for each benchmark.
    """
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    filtered_data = data[(data['Date'] >= start_date) & 
                         (data['Date'] <= end_date)].copy()
    
    if filtered_data.empty:
        print("No data available in the specified date range.")
        return {}
    
    filtered_data = filtered_data.sort_values(by='Date', ascending=True)
    excess_returns = {}
    
    for benchmark in benchmarks:
        if benchmark == 'HWOE':
            filtered_data[f'Slippage_{benchmark}_Adjusted'] = filtered_data[f'Slippage_{benchmark}'] * hwoe_adjustment_factor
            filtered_data[f'{benchmark}_Excess_Returns'] = -(filtered_data[f'Slippage_{benchmark}_Adjusted'] * filtered_data['Quantity']).cumsum()
            excess_returns[benchmark] = filtered_data[['Date', f'{benchmark}_Excess_Returns']]
        else:
            filtered_data[f'{benchmark}_Excess_Returns'] = -(filtered_data[f'Slippage_{benchmark}'] * filtered_data['Quantity']).cumsum()
            excess_returns[benchmark] = filtered_data[['Date', f'{benchmark}_Excess_Returns']]
    return excess_returns



def calculate_excess_returns(data, stock, benchmarks, start_date, end_date, hwoe_adjustment_factor=0.25):
    """
    Calculate excess returns for multiple benchmarks for a specific stock.

    Args:
    - data (pd.DataFrame): DataFrame containing trade data for all stocks.
    - stock (str): The stock symbol to calculate excess returns for.
    - benchmarks (list): List of benchmark strategies to calculate excess returns for.
    - start_date (datetime): Start date for the calculation period.
    - end_date (datetime): End date for the calculation period.
    - hwoe_adjustment_factor (float): Adjustment factor for HWOE calculations. Default is 0.25.

    Returns:
    dict: A dictionary where keys are benchmark names and values are DataFrames
          containing dates and cumulative excess returns for each benchmark.
    """
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    if stock not in data['Symbol'].unique():
        print(f"Stock {stock} does not exist in the data.")
        return {}
    
    filtered_data = data[(data['Symbol'] == stock) & 
                         (data['Date'] >= start_date) & 
                         (data['Date'] <= end_date)].copy()
    if filtered_data.empty:
        print(f"No data available for stock {stock} in the specified date range.")
        return {}
   
    filtered_data = filtered_data.sort_values(by='Date', ascending=True)
    excess_returns = {}
    
    for benchmark in benchmarks:
        if benchmark == 'HWOE':
            filtered_data[f'Slippage_{benchmark}_Adjusted'] = filtered_data[f'Slippage_{benchmark}'] * hwoe_adjustment_factor
            filtered_data[f'{benchmark}_Excess_Returns'] = -(filtered_data[f'Slippage_{benchmark}_Adjusted'] * filtered_data['Quantity']).cumsum()
            excess_returns[benchmark] = filtered_data[['Date', f'{benchmark}_Excess_Returns']]
        else:
            filtered_data[f'{benchmark}_Excess_Returns'] = -(filtered_data[f'Slippage_{benchmark}'] * filtered_data['Quantity']).cumsum()
            excess_returns[benchmark] = filtered_data[['Date', f'{benchmark}_Excess_Returns']]
    
    return excess_returns

def plot_excess_returns(trade_blotter_filtered, stock, show_open, show_close, show_twap, show_vwap, show_hwoe, start_date, end_date, hwoe_adjustment_factor=0.3, aggregate=False):
    """
    Retrieve excess returns data for plotting.

    Args:
    - trade_blotter_filtered (pd.DataFrame): Filtered trade data.
    - stock (str): Stock symbol.
    - show_open, show_close, show_twap, show_vwap, show_hwoe (bool): Flags for different price types.
    - start_date, end_date (datetime): Start and end dates for the analysis.
    - hwoe_adjustment_factor (float): Adjustment factor for HWOE calculations.
    - aggregate (bool): Whether to aggregate data across all stocks.

    Returns:
    dict: Processed data for excess returns plotting.
    """
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    benchmarks = []
    if show_open: benchmarks.append('Open')
    if show_close: benchmarks.append('Close')
    if show_twap: benchmarks.append('TWAP')
    if show_vwap: benchmarks.append('VWAP')
    if show_hwoe: benchmarks.append('HWOE')

    if aggregate:
        excess_returns = calculate_aggregated_excess_returns(trade_blotter_filtered, benchmarks, start_date, end_date, hwoe_adjustment_factor)
    else:
        excess_returns = calculate_excess_returns(trade_blotter_filtered, stock, benchmarks, start_date, end_date, hwoe_adjustment_factor)

    if not excess_returns:
        return {}
    
    processed_data = {}
    for benchmark, returns in excess_returns.items():
        try:
            returns['Date'] = pd.to_datetime(returns['Date'])
            returns.set_index('Date', inplace=True)
            returns = returns[~returns.index.duplicated(keep='last')]
            returns = returns.sort_index()
            
            if returns.index.isnull().any() or returns.empty:
                continue
            
            start_idx = returns.index.min()
            end_idx = returns.index.max()
            
            if pd.isna(start_idx) or pd.isna(end_idx):
                continue
            
            full_index = pd.date_range(start_idx, end_idx)
            
            # Ensure the excess returns column is numeric
            excess_returns_col = f'{benchmark}_Excess_Returns'
            returns[excess_returns_col] = pd.to_numeric(returns[excess_returns_col], errors='coerce')
            
            # Drop NaN values before interpolation
            returns = returns.dropna()
            
            if returns.empty:
                continue
            
            returns = returns.reindex(full_index).interpolate(method='linear').reset_index()
            returns.rename(columns={'index': 'Date'}, inplace=True)
            
            window_length = min(11, len(returns))   # Adjust window length based on available data points
            if window_length < 2:
                smoothed_data = returns[excess_returns_col]
            else:
                smoothed_data = savgol_filter(returns[excess_returns_col], window_length=window_length, polyorder=2)
            
            returns[excess_returns_col] = smoothed_data
            
            processed_data[benchmark] = returns[['Date', excess_returns_col]].to_dict(orient='records')
        
        except Exception as e:
            print(f"Error processing benchmark {benchmark}: {str(e)}")
            continue
    
    return processed_data

def xs_returns_line(data: Dict[str, List[Dict]]) -> None:
    """
    Plot a line chart of excess returns over time using Plotly.

    Args:
    data (dict): Dictionary containing excess returns data.

    Returns:
    plotly Figure: Plotly line chart of excess returns over time
    """
    fig = go.Figure()
    
    for benchmark, records in data.items():
        # Convert the list of dictionaries to a DataFrame
        df = pd.DataFrame(records)
        
        # Ensure 'Date' is in datetime format
        df['Date'] = pd.to_datetime(df['Date'])
        
        # The column name for excess returns might vary, so we find it dynamically
        excess_returns_col = [col for col in df.columns if col.endswith('Excess_Returns')][0]
        
        fig.add_trace(go.Scatter(
            x=df['Date'], 
            y=df[excess_returns_col], 
            name=benchmark,
        ))
    
    fig.update_layout(
        title='Excess Returns Over Time', 
        xaxis_title='Date', 
        yaxis_title='Excess Cost Savings ($)',
    )

    return fig

# ========================================================= #
#                                                           #  
# Slippage and Slippage Plot Computation                    #
#                                                           #
# ========================================================= #

def calculate_trades_slippage(enriched_trades):
    """
    Calculates slippage for trades and determines market conditions for the top 5 trades with the highest slippage.

    Args:
    enriched_trades (pd.DataFrame): A DataFrame containing enriched trade data.

    Required columns:
        - 'Slippage_PCT_TWAP': Slippage percentage compared to Time-Weighted Average Price
        - 'Close_Price': Closing price of the asset
        - 'Market Volume': Volume of trades in the market
        - 'Volume_Rolling_Mean': Rolling mean of the market volume
        - 'Volatility': Measure of price volatility
        - 'Volatility_Rolling_Mean': Rolling mean of the volatility
        - 'Date': Date of the trade
        - 'Action': Order type (buy/sell)
        - 'Symbol': The traded asset
        - 'Price': Executed price of the trade
        - 'TWAP_Price': Time-Weighted Average Price
        - 'Quantity': Number of shares traded

    Returns:
    list: A list of dictionaries, each representing one of the top 5 trades with the highest slippage.
          Each dictionary contains trade details and market conditions.

    Raises:
    TypeError: If input is not a pandas DataFrame or if column data types are incorrect.
    ValueError: If the DataFrame is empty or missing required columns.
    """
    
    try:
        # Input Validation
        if not isinstance(enriched_trades, pd.DataFrame):
            raise TypeError("Input 'enriched_trades' must be a pandas DataFrame")

        if enriched_trades.empty:
            raise ValueError("The enriched_trades DataFrame is empty")
        
        required_columns = ['Slippage_PCT_TWAP', 'Close_Price', 'Market Volume', 'Volume_Rolling_Mean',
                            'Volatility', 'Volatility_Rolling_Mean', 'Date', 'Action',
                            'Symbol', 'Price', 'TWAP_Price', 'Quantity']
        missing_columns = [col for col in required_columns if col not in enriched_trades.columns]
        if missing_columns:
            raise ValueError(f"The enriched_trades DataFrame is missing required columns: {', '.join(missing_columns)}")

        # Ensure numeric columns are of the correct type
        numeric_columns = ['Slippage_PCT_TWAP', 'Close_Price', 'Market Volume', 'Volume_Rolling_Mean',
                           'Volatility', 'Volatility_Rolling_Mean', 'Price', 'TWAP_Price', 'Quantity']
        for col in numeric_columns:
            enriched_trades[col] = pd.to_numeric(enriched_trades[col], errors='coerce')

        # Remove rows with NaN values after conversion
        enriched_trades = enriched_trades.dropna(subset=numeric_columns)

        if enriched_trades.empty:
            raise ValueError("After removing invalid entries, the DataFrame is empty")

        # Calculate top slippage trades
        top_slippage_trades = enriched_trades.nsmallest(5, 'Slippage_PCT_TWAP').copy()
        top_slippage_trades['Price_Change'] = top_slippage_trades['Close_Price'].pct_change() * 100
        top_slippage_trades['Slippage_PCT_TWAP'] *= 100

        # Define market conditions
        def market_conditions(row):
            """
            Determine market conditions based on volume, price action, and volatility.
            """
            volume_condition = np.select(
                [row['Market Volume'] > row['Volume_Rolling_Mean'] * 1.5,
                 row['Market Volume'] < row['Volume_Rolling_Mean'] * 0.5],
                ['High', 'Low'],
                default='Medium'
            )
            
            price_action = np.select(
                [row['Price_Change'] > 1, row['Price_Change'] < -1],
                ['Upward Momentum', 'Downward Momentum'],
                default='Sideways'
            )
            
            volatility_condition = np.select(
                [row['Volatility'] > row['Volatility_Rolling_Mean'] * 1.5,
                 row['Volatility'] < row['Volatility_Rolling_Mean'] * 0.5],
                ['High Volatility', 'Low Volatility'],
                default='Medium Volatility'
            )
            
            return f'{volume_condition} Volume, {price_action}, {volatility_condition}'

        # Apply market conditions
        top_slippage_trades['Market_Condition'] = top_slippage_trades.apply(market_conditions, axis=1)

        # Convert DataFrame to list of dictionaries
        trade_data_list = [
            {
                "Date": row['Date'].strftime('%Y-%m-%d'),
                "Action": row['Action'],
                "Symbol": row['Symbol'],
                "Your Price": f"${row['Price']:.2f}",
                "TWAP Price": f"${row['TWAP_Price']:.2f}",
                "Slippage": f"{row['Slippage_PCT_TWAP']:.2f}%",
                "Order Size": f"{row['Quantity']} shares",
                "Market Condition": row['Market_Condition']
            }
            for _, row in top_slippage_trades.iterrows()
        ]

        return trade_data_list

    except (TypeError, ValueError) as e:
        print(f"Error in calculate_trades_slippage: {str(e)}")
        raise

    except Exception as e:
        print(f"Unexpected error in calculate_trades_slippage: {str(e)}")
        raise ValueError(f"An unexpected error occurred while calculating trades slippage: {str(e)}")



def setup_slippage_analysis(trade_blotter_filtered, data_dict, selected_trade, selected_benchmarks='All'):
    """
    Set up data for slippage analysis.

    Args:
    - trade_blotter_filtered (pd.DataFrame): Filtered trade data.
    - data_dict (dict): Dictionary of market data for each stock.
    - selected_trade (str): Selected trade for analysis.
    - selected_benchmarks (str or list): Selected benchmarks for comparison.

    Returns:
    dict: Data for slippage analysis.
    """
    try:
        benchmark_options = ['Open_Price', 'Close_Price', 'TWAP_Price', 'VWAP_Price', 'HWOE_Price']

        if ':' in selected_trade:
            trade_index = int(selected_trade.split(':')[0])
            ticker = selected_trade.split(':')[1]
            trade_details = trade_blotter_filtered.loc[trade_index]
        else:
            ticker = selected_trade
            trade_details = trade_blotter_filtered[trade_blotter_filtered['Symbol'] == ticker]
            
            if trade_details.empty:
                return {
                    "error": f"No trade details found for {ticker}",
                    "plot_data": {},
                    "trade_price": None,
                    "Benchmark_Prices": {},
                    "Slippage_Data": {}
                }
            
            trade_details = trade_details.iloc[0]  # Get the first row if multiple trades exist

        trade_date = trade_details['Date']
        action = trade_details['Action']
        trade_price = trade_details['Price']

        if ticker not in data_dict:
            return {
                "error": f"No market data found for {ticker}",
                "plot_data": {},
                "trade_price": trade_price,
                "Benchmark_Prices": {},
                "Slippage_Data": {}
            }

        market_data = data_dict[ticker]

        if market_data.empty:
            return {
                "error": f"Empty market data for {ticker}",
                "plot_data": {},
                "trade_price": trade_price,
                "Benchmark_Prices": {},
                "Slippage_Data": {}
            }

        if 'Datetime' not in market_data.columns:
            market_data = market_data.reset_index()
            market_data.rename(columns={'index': 'Datetime'}, inplace=True)

        trade_datetime = find_trade_time(market_data, trade_date, trade_price)        
        optimal_before, optimal_after, optimal_before_date, optimal_after_date = identify_optimal_points(market_data, trade_datetime, action)

        slippage_before = None
        slippage_after = None

        if action.lower() == 'buy':
            slippage_before = trade_price - optimal_before if optimal_before else None
            slippage_after = trade_price - optimal_after if optimal_after else None
        elif action.lower() == 'sell':
            slippage_before = optimal_before - trade_price if optimal_before else None
            slippage_after = optimal_after - trade_price if optimal_after else None

        result_data = plot_slippage_analysis(market_data, trade_datetime, trade_price, optimal_before, optimal_after, optimal_before_date, optimal_after_date, slippage_before, slippage_after, action)

        if 'All' in selected_benchmarks:
            selected_benchmarks = benchmark_options
        benchmark_prices = data_preprocessing.preprocess_benchmark_prices(trade_details, result_data['plot_data'], selected_benchmarks) 
        slippage_data = collect_slippage_data(trade_details, benchmark_prices)
        
        result_data.update({
            "Benchmark_Prices": benchmark_prices,
            "Slippage_Data": slippage_data
        })
        
        return result_data

    except Exception as e:
        return {
            "error": f"An error occurred: {str(e)}",
            "plot_data": {},
            "trade_price": None,
            "Benchmark_Prices": {},
            "Slippage_Data": {}
        }



def calculate_slippage_sums(trade_data, selected_trade='All Trades', hwoe_adjustment_factor=0.25):
    """
    Calculate slippage sums for different strategies.

    Args:
    trade_data (pd.DataFrame): Trade data.
    selected_trade (str): Selected trade or 'All Trades'.
    hwoe_adjustment_factor (float): Adjustment factor for HWOE calculations.

    Returns:
    dict: Slippage sums for each strategy.
    """
    slippage_types = ['Slippage_Open', 'Slippage_Close', 'Slippage_TWAP', 'Slippage_VWAP', 'Slippage_HWOE']
    strategies = ['Open', 'Close', 'TWAP', 'VWAP', 'HWOE']

    if selected_trade != 'All Trades':
        trade_index = int(selected_trade.split(':')[0])
        trades = trade_data.loc[[trade_index]]
    else:
        trades = trade_data

    # Calculate the sum of slippage for each strategy
    slippage_sums = {}
    for strategy, slippage_type in zip(strategies, slippage_types):
        if strategy == 'HWOE':
            slippage_sums[strategy] = -(trades[slippage_type] * trades['Quantity']).sum() * hwoe_adjustment_factor
        else:
            slippage_sums[strategy] = -(trades[slippage_type] * trades['Quantity']).sum()

    return slippage_sums



def collect_slippage_data(trade_details, benchmark_prices):
    """
    Collect slippage data for different benchmarks.

    Args:
    - trade_details (pd.Series): Details of a single trade.
    - benchmark_prices (dict): Prices for different benchmarks.

    Returns:
    dict: Slippage data for each benchmark.
    """
    trade_price = trade_details['Price']
    action = trade_details['Action']
    slippage_data = {}

    for benchmark, price in benchmark_prices.items():
        slippage = price - trade_price if action.lower() == 'buy' else trade_price - price
        slippage_data[benchmark] = {
            'Benchmark Price': price,
            'Slippage': slippage
        }

    return slippage_data



def plot_slippage_analysis(filtered_data, trade_datetime, trade_price, optimal_before, optimal_after, optimal_before_date, optimal_after_date, slippage_before, slippage_after, action):
    """
    Prepare data for slippage analysis plot.

    Args:
    - filtered_data (pd.DataFrame): Filtered market data.
    - trade_datetime (datetime): Date and time of the trade.
    - trade_price (float): Price of the trade.
    - optimal_before, optimal_after (float): Optimal prices before and after the trade.
    - optimal_before_date, optimal_after_date (datetime): Dates of optimal prices.
    - slippage_before, slippage_after (float): Slippage before and after the trade.
    - action (str): Order type (buy/sell).

    Returns:
    dict: Data for slippage analysis plot.
    """
    start_plot_date = trade_datetime - timedelta(days=1)
    end_plot_date = trade_datetime + timedelta(days=1)

    if not isinstance(filtered_data.index, pd.DatetimeIndex):
        filtered_data = filtered_data.set_index('Datetime')

    plot_data = filtered_data.loc[start_plot_date:end_plot_date]

    # Convert the index to string for JSON serialization
    plot_data.index = plot_data.index.astype(str)

    results = { 
        "plot_data": plot_data.to_dict(orient='index'),
        "optimal_before": optimal_before,
        "optimal_after": optimal_after,
        "optimal_before_date": optimal_before_date,
        "optimal_after_date": optimal_after_date,
        "slippage_before": slippage_before,
        "slippage_after": slippage_after,
        "trade_date": trade_datetime,
        "trade_price": trade_price,
        "action": action
    }

    return results



def calculate_slippage_bar_trade_option(trade_blotter_filtered):
    """
    Create trade options for the dropdown in slippage bar chart.

    Args:
    trade_blotter_filtered (pd.DataFrame): Filtered trade data.

    Returns:
    list: List of trade options.
    """
    return ['All Trades'] + [
        f"{idx}: {row['Symbol']} {row['Action']} {row['Quantity']} @ ${row['Price']} on {row['Date']}" 
        for idx, row in trade_blotter_filtered.iterrows()
    ]



def avg_slippage_bar(enriched_trades, scaling_factor=0.25):
    """
    Generate a bar graph of average slippage percentages for different trading strategies.

    Args:
    enriched_trades (pd.DataFrame): DataFrame containing trade data with slippage information.
    scaling_factor (float): Factor to scale the slippage percentages.

    Returns:
    plotly Figure: Plotly bar graph of average slippage percentages
    """
    slippage_summary = {
        'Open': enriched_trades['Slippage_PCT_Open'].mean() * 100 * scaling_factor,
        'Close': enriched_trades['Slippage_PCT_Close'].mean() * 100 * scaling_factor,
        'TWAP': enriched_trades['Slippage_PCT_TWAP'].mean() * 100 * scaling_factor,
        'VWAP': enriched_trades['Slippage_PCT_VWAP'].mean() * 100 * scaling_factor,
        'HWOE': enriched_trades['Slippage_PCT_HWOE'].mean() * 100 * scaling_factor
    }

    slippage_df = pd.DataFrame(list(slippage_summary.items()), columns=['Strategy', 'Slippage'])
    
    fig = px.bar(
        slippage_df,
        x='Strategy',
        y='Slippage', 
        title='Average Slippage % vs. Strategy',
        labels={'Slippage': 'Average Slippage (%)'},
        text='Slippage',
    )
    
    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

    return fig



def slippage_sum_bar(data):
    """
    Plot a bar chart of slippage sums using Plotly.

    Args:
    data (dict): Dictionary with benchmarks as keys and slippage sums as values.

    Returns:
    plotly Figure: Plotly bar chart of slippage sums
    """
    df = pd.DataFrame(list(data.items()), columns=['Benchmark', 'Slippage Sum'])
    
    fig = px.bar(
        df,
        x='Benchmark',
        y='Slippage Sum',
        title='Slippage Sums by Benchmark',
    )
    
    return fig

# ========================================================= #
#                                                           #
# Other Charts Computation                                  #
#                                                           #
# ========================================================= #

def candle_stick_trade_option(trade_blotter_filtered):
    """
    Create trade options for the dropdown in candlestick chart.

    Args:
    trade_blotter_filtered (pd.DataFrame): Filtered trade data.

    Returns:
    list: List of trade options.
    """
    return [f"{idx}: {row['Symbol']} {row['Action']} {row['Quantity']} @ ${row['Price']} on {row['Date']}" for idx, row in trade_blotter_filtered.iterrows()]

def candlestick(plot_data, trade_price, benchmark_prices, selected_benchmarks):
    """
    Plot a candlestick chart using Plotly.

    Args:
    plot_data (dict): Dictionary containing OHLC data.
    trade_price (float): Price of the trade.
    benchmark_prices (dict): Dictionary of benchmark prices.
    selected_benchmarks (list): List of selected benchmarks to display.

    Returns:
    plotly Figure: Plotly candlestick chart of the benchmarks and trade prices
    """
    df = pd.DataFrame.from_dict(plot_data, orient='index')
    df.index = pd.to_datetime(df.index)
    df = df.reset_index().rename(columns={'index': 'date'})

    numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(subset=numeric_columns)

    if df.empty:
        st.error("No valid data available for the candlestick chart after processing.")
        return

    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    )])

    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['Volume'],
        name='Volume',
        yaxis='y2',
        opacity=0.5
    ))

    fig.add_trace(go.Scatter(
        x=df['date'],
        y=[trade_price] * len(df),
        mode='lines',
        name='Trade Price',
        line=dict(color='black', dash='dash')
    ))

    colors = {'Open_Price': 'blue', 'Close_Price': 'purple', 'TWAP_Price': 'green', 'VWAP_Price': 'orange', 'HWOE_Price': 'red'}
    for benchmark in selected_benchmarks:
        if benchmark in benchmark_prices:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=[benchmark_prices[benchmark]] * len(df),
                mode='lines',
                name=benchmark,
                line=dict(color=colors.get(benchmark, 'gray'), dash='dot')
            ))

    fig.update_layout(
        title='Candlestick Chart with Volume and Benchmarks',
        yaxis_title='Price',
        xaxis_title='Date',
        yaxis2=dict(title='Volume', overlaying='y', side='right'),
        xaxis_rangeslider_visible=False
    )

    return fig

# ========================================================= #
#                                                           #
# Functions to generate all Report Data                     #
#                                                           #
# ========================================================= #

def generate_report_data(trade_blotter):
    """
    Generates numerical data required for generating the report. Cache-less

    Args:
    - trade_blotter: a prepared trade_blotter with all pre-processing complete. 

    Returns:
    dict: Data with all the numbers required for generating the report 
    """
    # Data filtration
    trade_blotter_filtered = trade_blotter.copy()
    start_date = trade_blotter_filtered['Date'].min()
    end_date = trade_blotter_filtered['Date'].max()

    # 1. Generate Overview
    print('generate_trading_overview')
    trading_overview = generate_trading_overview(trade_blotter)

    # 2. Trades with Most Slippage
    print('calculate_trades_slippage')
    most_slippage_trades = calculate_trades_slippage(trade_blotter)
    
    # 3. Calculate Potential Savings
    print('calculate_potential_savings')
    potential_savings = calculate_potential_savings(trade_blotter)

    # 4. Generate Average Slippage Bar Graph
    print('avg_slippage_bar')
    avg_slippage_bar_bytes = BytesIO(avg_slippage_bar(trade_blotter).to_image(format="png"))

    # 5. Generate Excess Return Line Graph
    print('plot_excess_returns')
    stock = trade_blotter_filtered['Symbol'].unique().tolist()[0]
    xs_returns_data = plot_excess_returns(
        trade_blotter_filtered, 
        stock=stock,
        show_open=True, 
        show_close=True, 
        show_twap=True, 
        show_vwap=True, 
        show_hwoe=True,
        start_date=start_date,
        end_date=end_date,
        hwoe_adjustment_factor=potential_savings['scaling_factor'],
        aggregate=True
    )
    xs_returns_line_bytes = BytesIO(xs_returns_line(xs_returns_data).to_image(format="png"))

    # 6. Generation Actionable Recommendations 
    print('actionable_recommendations')
    actionable_recommendation = actionable_recommendations(trade_blotter)

    return {
        'trading_overview': trading_overview,
        'avg_slippage_bar_bytes': avg_slippage_bar_bytes,
        'xs_returns_line_bytes': xs_returns_line_bytes,
        'most_slippage_trades': most_slippage_trades,
        'potential_savings': potential_savings,
        'actionable_recommendations': actionable_recommendation
    }



def generate_report_data_cached(trade_blotter, platform_type, file_id):
    """
    Generates numerical data required for generating the report. 
    Either retrieves it from the cache if it exists or stores the new data in cache

    Args:
    - trade_blotter: a prepared trade_blotter with all pre-processing complete. 
    - platform_type: the platform from which the user's data was acquired
    - file_id: file id to which to store the report data or retrieve it later

    Returns:
    dict: Data with all the numbers required for generating the report 
    """

    cache_key = f"{platform_type}_{file_id}"
    cache_key = f"{platform_type}_{file_id}_trade_blotter"
    cached_trade_blotter = cache.get(key=cache_key)

    if cached_trade_blotter is None:
        # If nothing cached yet, perform the usual computations then store it in the cache
        cache.set(key=cache_key,value=trade_blotter,timeout=60 * 15)
        trade_blotter_filtered = trade_blotter.copy()

        # Data filtration
        trade_blotter_filtered = trade_blotter.copy()
        start_date = trade_blotter_filtered['Date'].min()
        end_date = trade_blotter_filtered['Date'].max()
        
        # 1. Generate Overview
        trading_overview = generate_trading_overview(trade_blotter)
        cache.set(key=f"{platform_type}_{file_id}_trading_overview", value=trading_overview,timeout=60 * 15)

        # 2. Trades with Most Slippage
        most_slippage_trades = calculate_trades_slippage(trade_blotter)
        cache.set(key=f"{platform_type}_{file_id}_most_slippage_trades", value=most_slippage_trades,timeout=60 * 15)
        
        # 3. Calculate Potential Savings
        potential_savings = calculate_potential_savings(trade_blotter)
        cache.set(key=f"{platform_type}_{file_id}_potential_savings", value=potential_savings,timeout=60 * 15)
        
        # 4. Generate Average Slippage Bar Graph
        avg_slippage_bar_bytes = BytesIO(avg_slippage_bar(trade_blotter).to_image(format="png"))
        cache.set(key=f"{platform_type}_{file_id}_avg_slippage_bar_bytes", value=avg_slippage_bar_bytes,timeout=60 * 15)

        # 5. Generate Excess Return Line Graph
        stock = trade_blotter_filtered['Symbol'].unique().tolist()[0]
        xs_returns_data = plot_excess_returns(
            trade_blotter_filtered, 
            stock=stock,
            show_open=True, 
            show_close=True, 
            show_twap=True, 
            show_vwap=True, 
            show_hwoe=True,
            start_date=start_date,
            end_date=end_date,
            hwoe_adjustment_factor=potential_savings['scaling_factor'],
            aggregate=True
        )
        xs_returns_line_bytes = BytesIO(xs_returns_line(xs_returns_data).to_image(format="png"))
        cache.set(key=f"{platform_type}_{file_id}_xs_returns_line_bytes", value=xs_returns_line_bytes,timeout=60 * 15)
    
        # 5. Actionable Recommendations
        actionable_recommendation = actionable_recommendations(trade_blotter)
        cache.set(key=f"{platform_type}_{file_id}_actionable_recommendation", value=actionable_recommendation,timeout=60 * 15)
  
    elif cache.get(key=f"{platform_type}_{file_id}_trading_overview") is None:
        # Here if cache blotter found but no information has been generated
        trade_blotter = cache.get(key=f"{platform_type}_{file_id}_trade_blotter")
        trade_blotter_filtered = trade_blotter.copy()  

        # Data filtration
        trade_blotter_filtered = trade_blotter.copy()
        start_date = trade_blotter_filtered['Date'].min()
        end_date = trade_blotter_filtered['Date'].max()
        
        # 1. Generate Overview
        trading_overview = generate_trading_overview(trade_blotter)
        cache.set(key=f"{platform_type}_{file_id}_trading_overview", value=trading_overview,timeout=60 * 15)

        # 2. Trades with Most Slippage
        most_slippage_trades = calculate_trades_slippage(trade_blotter)
        cache.set(key=f"{platform_type}_{file_id}_most_slippage_trades", value=most_slippage_trades,timeout=60 * 15)
        
        # 3. Calculate Potential Savings
        potential_savings = calculate_potential_savings(trade_blotter)
        cache.set(key=f"{platform_type}_{file_id}_potential_savings", value=potential_savings,timeout=60 * 15)
        
        # 4. Generate Average Slippage Bar Graph
        avg_slippage_bar_bytes = BytesIO(avg_slippage_bar(trade_blotter).to_image(format="png"))
        cache.set(key=f"{platform_type}_{file_id}_avg_slippage_bar_bytes", value=avg_slippage_bar_bytes,timeout=60 * 15)

        # 5. Generate Excess Return Line Graph
        stock = trade_blotter_filtered['Symbol'].unique().tolist()[0]
        xs_returns_data = plot_excess_returns(
            trade_blotter_filtered, 
            stock=stock,
            show_open=True, 
            show_close=True, 
            show_twap=True, 
            show_vwap=True, 
            show_hwoe=True,
            start_date=start_date,
            end_date=end_date,
            hwoe_adjustment_factor=potential_savings['scaling_factor'],
            aggregate=True
        )
        xs_returns_line_bytes = BytesIO(xs_returns_line(xs_returns_data).to_image(format="png"))
        cache.set(key=f"{platform_type}_{file_id}_xs_returns_line_bytes", value=xs_returns_line_bytes,timeout=60 * 15)
    
        # 5. Actionable Recommendations
        actionable_recommendation = actionable_recommendations(trade_blotter)
        cache.set(key=f"{platform_type}_{file_id}_actionable_recommendation", value=actionable_recommendation,timeout=60 * 15)
    
    else:
        # Here if we have a trade_blotter in our cache, just load its data
        trading_overview = cache.get(key=f"{platform_type}_{file_id}_trading_overview")
        avg_slippage_bar_bytes = cache.get(key=f"{platform_type}_{file_id}_avg_slippage_bar_bytes")
        xs_returns_line_bytes = cache.get(key=f"{platform_type}_{file_id}_xs_returns_line_bytes")
        most_slippage_trades = cache.get(key=f"{platform_type}_{file_id}_most_slippage_trades")
        potential_savings = cache.get(key=f"{platform_type}_{file_id}_potential_savings")
        actionable_recommendation = cache.get(key=f"{platform_type}_{file_id}_actionable_recommendation")
        
    return {
        'trading_overview': trading_overview,
        'avg_slippage_bar_bytes': avg_slippage_bar_bytes,
        'xs_returns_line_bytes': xs_returns_line_bytes,
        'most_slippage_trades': most_slippage_trades,
        'potential_savings': potential_savings,
        'actionable_recommendations': actionable_recommendation
    }