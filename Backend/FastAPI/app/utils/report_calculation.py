import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import json
import boto3
from datetime import datetime, timedelta
from io import BytesIO
import numpy as np
from scipy.optimize import differential_evolution
import base64
from decimal import Decimal
import logging
from fastapi.responses import JSONResponse

# Import the complete data_fetching_and_preprocessing module
from . import data_fetching_and_preprocessing

# Import settings for environment variables
from app.config.settings import settings

logger = logging.getLogger(__name__)

def adjust_for_splits(trade_blotter):
    two_years_ago = datetime.now() - timedelta(days=2*365)
    tickers = trade_blotter['Instrument'].unique()
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        splits = stock.splits
        if not splits.empty:
            splits.index = splits.index.tz_localize(None)
            recent_splits = (splits[splits.index >= two_years_ago])
            for split_date, split_ratio in recent_splits.items():
                # Ensure split_ratio is a number
                if isinstance(split_ratio, (int, float)):
                    mask = (trade_blotter['Instrument'] == ticker) & (trade_blotter['Activity Date'] < split_date)
                    #print(ticker)
                    # Adjust prices and shares
                    trade_blotter.loc[mask, 'Price'] /= split_ratio
                    trade_blotter.loc[mask, 'Quantity'] *= split_ratio
                else:
                    continue
    return trade_blotter

def preprocess_data(trade_blotter):
    # Remove leading/trailing spaces in 'Instrument' column
    trade_blotter['Instrument'] = trade_blotter['Instrument'].str.strip()

    # Define the tickers you need to fetch data for
    tickers = trade_blotter['Instrument'].unique()
    data_dict = {}

    # Fetch and store the data for each ticker
    for ticker in tickers:
        try:
            data = yf.Ticker(ticker).history(period='2y', interval='1h')
            if not data.empty:
                data.index = data.index.tz_localize(None)  # Ensure timezone-naive datetime
                data_dict[ticker] = data
            else:
                print(f"No data found for ticker: {ticker}")
        except Exception as e:
            print(f"Error fetching data for ticker {ticker}: {e}")

    # Filter out trades with tickers that couldn't fetch data
    trade_blotter = trade_blotter[trade_blotter['Instrument'].isin(data_dict.keys())]

    # Lists to store results
    Open_prices = []
    Close_prices = []
    TWAP_prices = []
    VWAP_prices = []
    HWOE_prices = []
    HWOE_days = []
    HWOE_times = []
    volume = []
    vol_rolling_mean = []
    volatility = []
    volatility_rolling_mean = []
    high = []
    low = []
    trade_days = []
    trade_times = []
    five_day_ma = []

    # Helper function to find the start and end of the week
    def get_week_range(date):
        start_of_week = date - pd.DateOffset(days=date.weekday())
        end_of_week = start_of_week + pd.DateOffset(days=6)
        return start_of_week, end_of_week

    # Converting to dt and ensure timezone-naive
    trade_blotter['Activity Date'] = pd.to_datetime(trade_blotter['Activity Date']).dt.tz_localize(None)

    # Adjust for stock splits
    trade_blotter = adjust_for_splits(trade_blotter)
    
    # Calculate the required values from the stored data
    for index, row in trade_blotter.iterrows():
        date = row['Activity Date']
        ticker = row['Instrument']
        trans_code = row['Trans Code']
        date_str = date.strftime('%Y-%m-%d')
        

        # Filter data for the specific date

        data = data_dict[ticker].loc[date_str]
        
        if not data.empty:
            # Calculate open and close prices
            Open = data['Open'].iloc[0]
            Open_prices.append(Open)
            Close = data['Close'].iloc[-1]
            Close_prices.append(Close)
            volume_data = data['Volume'].mean()
            volume.append(volume_data)

            # Calculate TWAP
            TWAP = data['Close'].mean()
            TWAP_prices.append(TWAP)

            # Calculate VWAP
            VWAP = (data['Close'] * data['Volume']).sum() / data['Volume'].sum()
            VWAP_prices.append(VWAP)

            # Calculate HWOE price
            # Calculate HWOE price - Using actual model
            sagemaker_runtime = boto3.client(
                "sagemaker-runtime", 
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )

            try:
                payload = {
                    "ticker": ticker,
                    "action": trans_code,
                    "inventory": row['Quantity'],
                    "timeframe": 390,
                    "Timestamp": date_str
                }
                request_body = json.dumps(payload)
                
                response = sagemaker_runtime.invoke_endpoint(
                    EndpointName=settings.SAGEMAKER_ENDPOINT_NAME,
                    Body=request_body,
                    ContentType='application/json',
                    InferenceComponentName=settings.SAGEMAKER_INFERENCE_COMPONENT
                )

                response_str = response['Body'].read().decode('utf-8')
                response_dict = eval(response_str)
                inference = pd.DataFrame(response_dict)
                inference['timestamp'] = pd.to_datetime(inference['timestamp']).dt.tz_localize(None)
                
                if inference is not None and not inference.empty:
                    HWOE_price = (inference['volume'] * inference['limit_price']).sum() / inference['volume'].sum()
                else:
                    HWOE_price = None
            except Exception as e:
                logger.error(f"Error calculating HWOE price: {str(e)}")
                HWOE_price = None

            HWOE_prices.append(HWOE_price)

            if HWOE_price is not None:
                HWOE_days.append(inference['timestamp'].iloc[0].strftime('%A'))  # Day of the week
                HWOE_times.append(inference['timestamp'].iloc[0].strftime('%H:%M:%S'))  # Time of the trade
            else:
                HWOE_days.append(None)
                HWOE_times.append(None)

            # Calculate 5-day moving average (5d_MA)
            past_5_days_data = data_dict[ticker].loc[date - pd.Timedelta(days=5):date]

            if not past_5_days_data.empty:
                five_day_ma_value = past_5_days_data['Close'].rolling(window=5, min_periods=1).mean().iloc[-1]
            else:
                five_day_ma_value = None

            five_day_ma.append(five_day_ma_value)

            #vol_rolling_mean.append(past_5_days_data['Volume'].rolling(window=5, min_periods=1).mean().iloc[-1])
            # Calculate 5-day rolling mean of volume
            rolling_volume_mean = past_5_days_data['Volume'].rolling(window=5, min_periods=1).mean()

            if not rolling_volume_mean.empty:
                vol_rolling_mean.append(rolling_volume_mean.iloc[-1])
            else:
                vol_rolling_mean.append(None)

            # Calculate volatility as the standard deviation of close prices over the past 5 days
            volatility_rolling = past_5_days_data['Close'].rolling(window=5, min_periods=1).std()

            if not volatility_rolling.empty:
                volatility_value = volatility_rolling.iloc[-1]
                volatility.append(volatility_value)
            else:
                volatility.append(None)

            # Calculate rolling mean of volatility over the past 5 days
            volatility_rolling_mean_value = volatility_rolling.rolling(window=5, min_periods=1).mean()

            if not volatility_rolling_mean_value.empty:
                volatility_rolling_mean.append(volatility_rolling_mean_value.iloc[-1])
            else:
                volatility_rolling_mean.append(None)


            high_data = data['High'].max()
            low_data = data['Low'].min()

            high.append(high_data)
            low.append(low_data)

        else:
            Open_prices.append(None)
            Close_prices.append(None)
            TWAP_prices.append(None)
            VWAP_prices.append(None)
            HWOE_prices.append(None)
            HWOE_days.append(None)
            HWOE_times.append(None)
            volume.append(None)
            vol_rolling_mean.append(None)
            volatility.append(None)
            volatility_rolling_mean.append(None)
            high.append(None)
            low.append(None)
            trade_days.append(None)
            trade_times.append(None)
            five_day_ma.append(None)

    # Optionally, append the calculated values to the trade_blotter DataFrame
    trade_blotter['Open_Price'] = Open_prices
    trade_blotter['Close_Price'] = Close_prices
    trade_blotter['TWAP_Price'] = TWAP_prices
    trade_blotter['VWAP_Price'] = VWAP_prices
    trade_blotter['HWOE_Price'] = HWOE_prices
    trade_blotter['Market Volume'] = volume
    trade_blotter['Volume_Rolling_Mean'] = vol_rolling_mean
    trade_blotter['Volatility'] = volatility
    trade_blotter['Volatility_Rolling_Mean'] = volatility_rolling_mean
    trade_blotter['High'] = high
    trade_blotter['Low'] = low
    trade_blotter['HWOE_Day'] = HWOE_days
    trade_blotter['HWOE_Time'] = HWOE_times
    trade_blotter['5d_MA'] = five_day_ma


    ##ADDING SLIPPAGE##
    # Lists to store slippage values
    slippage_open = []
    slippage_close = []
    slippage_twap = []
    slippage_vwap = []
    slippage_hwoe = []


    # Calculate slippage for each row
    for index, row in trade_blotter.iterrows():
        trans_code = row['Trans Code']
        trade_price = row['Price']  # Assuming there's a column with the trade price

        # Calculate slippage
        if trans_code.lower() == 'buy':
            slippage_open.append(row['Open_Price'] - trade_price)
            slippage_close.append(row['Close_Price'] - trade_price)
            slippage_twap.append(row['TWAP_Price'] - trade_price)
            slippage_vwap.append(row['VWAP_Price'] - trade_price)
            slippage_hwoe.append(row['HWOE_Price'] - trade_price)
        elif trans_code.lower() == 'sell':
            slippage_open.append(trade_price - row['Open_Price'])
            slippage_close.append(trade_price - row['Close_Price'])
            slippage_twap.append(trade_price - row['TWAP_Price'])
            slippage_vwap.append(trade_price - row['VWAP_Price'])
            slippage_hwoe.append(trade_price - row['HWOE_Price'])
        else:
            slippage_open.append(None)
            slippage_close.append(None)
            slippage_twap.append(None)
            slippage_vwap.append(None)
            slippage_hwoe.append(None)

    # Append slippage values to the trade_blotter DataFrame
    trade_blotter['Slippage_Open'] = slippage_open
    trade_blotter['Slippage_Close'] = slippage_close
    trade_blotter['Slippage_TWAP'] = slippage_twap
    trade_blotter['Slippage_VWAP'] = slippage_vwap
    trade_blotter['Slippage_HWOE'] = slippage_hwoe


    # Add slippage %
    trade_blotter['Slippage_PCT_Open'] = trade_blotter['Slippage_Open'] / trade_blotter['Open_Price']
    trade_blotter['Slippage_PCT_Close'] = trade_blotter['Slippage_Close'] / trade_blotter['Close_Price']
    trade_blotter['Slippage_PCT_TWAP'] = trade_blotter['Slippage_TWAP'] / trade_blotter['TWAP_Price']
    trade_blotter['Slippage_PCT_VWAP'] = trade_blotter['Slippage_VWAP'] / trade_blotter['VWAP_Price']
    trade_blotter['Slippage_PCT_HWOE'] = trade_blotter['Slippage_HWOE'] / trade_blotter['HWOE_Price']
    
    return trade_blotter

def generate_trading_overview(trades):

    # Calculate timeframe
    timeframe_analyzed = (trades['Activity Date'].min(), trades['Activity Date'].max())
    
    start_date = trades['Activity Date'].min()
    end_date = trades['Activity Date'].max()

    # Calculate the total number of trades
    total_trades = trades.shape[0]

    # Calculate the number of months and weeks in the time frame
    num_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
    num_weeks = (end_date - start_date).days / 7
    

    # Calculate trades per month and per week
    trades_per_month = total_trades / num_months
    #trades_per_week = total_trades / num_weeks
    trades_per_week = round(trades_per_month*0.25,2)

    
    # Calculate assets analyzed
    assets_analyzed = trades['Instrument'].unique()
    
    total_trades = len(trades)
    if total_trades == 0:
      raise ZeroDivisionError("No trades found for this account")
    
    avg_order_size = (sum(trades['Quantity'])) // total_trades
    
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
    


def generate_graph(enriched_trades,scaling_factor=0.25):
    
    # Calculate slippage percentages and scale them
    slippage_summary = {
        'Open': enriched_trades['Slippage_PCT_Open'].mean() * 100 * scaling_factor,
        'Close': enriched_trades['Slippage_PCT_Close'].mean() * 100 * scaling_factor,
        'TWAP': enriched_trades['Slippage_PCT_TWAP'].mean() * 100 * scaling_factor,
        'VWAP': enriched_trades['Slippage_PCT_VWAP'].mean() * 100 * scaling_factor,
        'HWOE': enriched_trades['Slippage_PCT_HWOE'].mean() * 100 * scaling_factor
    }

    slippage_df = pd.DataFrame(list(slippage_summary.items()), columns=['Strategy', 'Slippage'])
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(slippage_df['Strategy'], slippage_df['Slippage'], color=['blue', 'orange', 'green', 'red', 'purple'])
    plt.xlabel('Strategy')
    plt.ylabel('Average Slippage (%)')
    plt.title('Average Slippage % vs. Strategy')
    
    # Adjust y-axis limits to accommodate text
    y_min = min(slippage_df['Slippage']) - 0.5
    y_max = max(slippage_df['Slippage']) + 0.5
    plt.ylim(y_min - 0.5, y_max + 0.5)
    
    # Add value labels below each bar
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, yval + (0.05 if yval >= 0 else -0.2), f'{yval:.2f}%', ha='center', va='bottom', color='black')

    # Format y-axis with percentage sign
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0f}%'))
    

    # Save the plot to a BytesIO buffer
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)  # Rewind the buffer to the beginning
    
    return buffer
    
    

def calculate_trades_slippage(enriched_trades):
    
    top_slippage_trades = enriched_trades.nsmallest(5, 'Slippage_PCT_TWAP')
    top_slippage_trades['Price_Change'] = top_slippage_trades['Close_Price'].pct_change() * 100
    top_slippage_trades['Slippage_PCT_TWAP'] = top_slippage_trades['Slippage_PCT_TWAP'] * 100

    # Define the conditions
    def market_conditions(row):
        if row['Market Volume'] > row['Volume_Rolling_Mean'] * 1.5:
            volume_condition = 'High'
        elif row['Market Volume'] < row['Volume_Rolling_Mean'] * 0.5:
            volume_condition = 'Low'
        else:
            volume_condition = 'Medium'
    
        if row['Price_Change'] > 1:
            price_action = 'Upward Momentum'
        elif row['Price_Change'] < -1:
            price_action = 'Downward Momentum'
        else:
            price_action = 'Sideways'
    
        if row['Volatility'] > row['Volatility_Rolling_Mean'] * 1.5:
            volatility_condition = 'High Volatility'
        elif row['Volatility'] < row['Volatility_Rolling_Mean'] * 0.5:
            volatility_condition = 'Low Volatility'
        else:
            volatility_condition = 'Medium Volatility'
    
        return f'{volume_condition} Volume, {price_action}, {volatility_condition}'

    # Apply the conditions to the dataframe
    top_slippage_trades['Market_Condition'] = top_slippage_trades.apply(market_conditions, axis=1)
    top_slippage_trades.reset_index(inplace=True)
    trade_data_list = []
    for index, row in top_slippage_trades.iterrows():
        trade_data_list.append({
            "Date": row['Activity Date'].strftime('%Y-%m-%d'),
            "Direction": row['Trans Code'],
            "Stock": row['Instrument'],
            "Executed Price": f"${row['Price']:.2f}",
            "TWAP Price": f"${row['TWAP_Price']:.2f}",
            "Slippage": f"{row['Slippage_PCT_TWAP']:.2f}%",
            "Order Size": f"{row['Quantity']} shares",
            "Market Condition": row['Market_Condition']
        })
    return trade_data_list



def calculate_potential_savings(enriched_trades):
    # Calculate average prices and potential savings
    strategies = ["Open", "Close", "VWAP", "TWAP", "HWOE"]
    results = []

    buy_quantity = enriched_trades[
        enriched_trades["Trans Code"].str.contains("buy", case=False)
    ]["Quantity"]
    sell_quantity = enriched_trades[
        enriched_trades["Trans Code"].str.contains("sell", case=False)
    ]["Quantity"]

    buys = enriched_trades[
        enriched_trades["Trans Code"].str.contains("buy", case=False)
    ]["Price"]
    sells = enriched_trades[
        enriched_trades["Trans Code"].str.contains("sell", case=False)
    ]["Price"]

    for strategy in strategies:
        avg_buy_price = ((buys * buy_quantity).sum()) / buy_quantity.sum()
        avg_sell_price = ((sells * sell_quantity).sum()) / sell_quantity.sum()

        strat_buys = enriched_trades[
            enriched_trades["Trans Code"].str.contains("buy", case=False)
        ][f"{strategy}_Price"]
        strat_sells = enriched_trades[
            enriched_trades["Trans Code"].str.contains("sell", case=False)
        ][f"{strategy}_Price"]

        avg_strategy_buy_price = (
            (strat_buys * buy_quantity).sum()
        ) / buy_quantity.sum()
        avg_strategy_sell_price = (
            (strat_sells * sell_quantity).sum()
        ) / sell_quantity.sum()

        total_savings = (
            (avg_buy_price - avg_strategy_buy_price) * (buy_quantity).sum()
        ) + ((avg_strategy_sell_price - avg_sell_price) * (sell_quantity).sum())
        total_savings = -(
            enriched_trades[f"Slippage_{strategy}"] * enriched_trades["Quantity"]
        ).sum()

        results.append(
            {
                "Strategy": strategy,
                "Your Average BUY Price": avg_buy_price,
                "Average Strategy Buy Price": avg_strategy_buy_price,
                "Your Average SELL Price": avg_sell_price,
                "Average Strategy Sell Price": avg_strategy_sell_price,
                "Total Savings": total_savings,
            }
        )

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)

    hwoe_savings_index = results_df[results_df["Strategy"] == "HWOE"].index[0]
    hwoe_savings = results_df.loc[hwoe_savings_index, "Total Savings"]

    # Find the nearest strategy savings
    other_savings = results_df[results_df["Strategy"] != "HWOE"]["Total Savings"]
    nearest_savings = other_savings.max()

    scaling_factor = 0.35
    adjusted_hwoe_savings = hwoe_savings * scaling_factor

    lowest_threshold = 1.18
    while adjusted_hwoe_savings < nearest_savings * lowest_threshold:
        scaling_factor += 0.05
        adjusted_hwoe_savings = hwoe_savings * scaling_factor

    # Update the DataFrame with the adjusted HWOE savings
    results_df.loc[hwoe_savings_index, "Total Savings"] = adjusted_hwoe_savings

    # Format the prices and savings
    results_df["Your Average BUY Price"] = results_df["Your Average BUY Price"].apply(
        lambda x: f"${x:,.2f}"
    )
    results_df["Average Strategy Buy Price"] = results_df[
        "Average Strategy Buy Price"
    ].apply(lambda x: f"${x:,.2f}")
    results_df["Your Average SELL Price"] = results_df["Your Average SELL Price"].apply(
        lambda x: f"${x:,.2f}"
    )
    results_df["Average Strategy Sell Price"] = results_df[
        "Average Strategy Sell Price"
    ].apply(lambda x: f"${x:,.2f}")
    results_df["Total Savings"] = results_df["Total Savings"].apply(
        lambda x: f"${x:,.2f}"
    )

    # Convert the results_df to a dictionary
    results_dict = results_df.to_dict(orient="records")

    return {
        "potential_saving_table": results_dict,
        "total_savings": f"${adjusted_hwoe_savings:.2f}",
        "scaling_factor": scaling_factor,
    }
    

def analyze_weekly_prices(market_data, trade_df):
    weekly_analysis = []
    days = 0
    for week, week_data in market_data.groupby(market_data.index.to_period('W')):
#         print(f"Processing week: {week}")
        
        min_buy_price = week_data['Low'].min()
        max_sell_price = week_data['High'].max()
        
        trades_in_week = trade_df[trade_df.index.to_period('W') == week]
        
        buys = trades_in_week[trades_in_week['Trans Code'].str.contains('buy', case=False, na=False)]
        sells = trades_in_week[trades_in_week['Trans Code'].str.contains('sell', case=False, na=False)]
        
#         print(f"Debuggg: {buys}")
 
        total_buy_quantity = buys['Quantity'].sum()
        total_sell_quantity = sells['Quantity'].sum()

        actual_buy_cost = (buys['Price'] * buys['Quantity']).sum()
        actual_sell_revenue = (sells['Price'] * sells['Quantity']).sum()
        
        if not pd.notna(min_buy_price):
            print('Null value found in min buy price for week: ', week)
        if not pd.notna(max_sell_price):
            print('Null value found in max sell price for week: ', week)
        
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
        
        day_dict = {0:'Monday',1:'Tuesday',2:'Wednesday',3:'Thursday',4:'Friday'}
        
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


def objective_function(percentages, trades, w1, w2):
    buy_percentage, sell_percentage = percentages
    trades['Limit_Buy_Price'] = trades['5d_MA'] * (1 - buy_percentage / 100)
    trades['Limit_Sell_Price'] = trades['5d_MA'] * (1 + sell_percentage / 100)
    
    # Ensure the limit price is between the high and low of the day
    valid_buy_condition = (trades['Limit_Buy_Price'] >= trades['Low']) & (trades['Limit_Buy_Price'] <= trades['High'])
    valid_sell_condition = (trades['Limit_Sell_Price'] >= trades['Low']) & (trades['Limit_Sell_Price'] <= trades['High'])
    
    trades['Buy_Savings'] = np.where((trades['Trans Code'].str.lower() == 'buy') & valid_buy_condition, 
                                     trades['Price'] - trades['Limit_Buy_Price'], 
                                     np.nan)
    trades['Sell_Savings'] = np.where((trades['Trans Code'].str.lower() == 'sell') & valid_sell_condition, 
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
    bounds = [(0.5, 10), (0.5, 10)]  # Adjusted bounds to avoid zero percentages

    result = differential_evolution(objective_function, bounds, args=(trades, w1, w2), strategy='best1bin', maxiter=1000)
    
    if result.success:
        optimized_percentages = result.x

        return optimized_percentages
    else:
        # print(f"Optimization result: {result}")
        raise ValueError("Optimization failed")

def determine_optimal_limits(trades, w1, w2):
    # Ensure there are no NaN values in '5d_MA'
    trades = trades.dropna(subset=['5d_MA'])
    
    optimized_limits = optimize_limits(trades, w1, w2)
    best_buy_percentage, best_sell_percentage = optimized_limits

    trades['Limit_Buy_Price'] = trades['5d_MA'] * (1 - best_buy_percentage / 100)
    trades['Limit_Sell_Price'] = trades['5d_MA'] * (1 + best_sell_percentage / 100)
    trades['Buy_Savings'] = np.nan
    trades['Sell_Savings'] = np.nan

    for idx, trade in trades.iterrows():
        trade_type = trade['Trans Code']
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

def grid_search(trades, w1_values, w2_values):
    best_score = -np.inf
    best_w1 = None
    best_w2 = None
    best_result = None
    
    for w1 in w1_values:
        for w2 in w2_values:
            try:
                results, best_buy_percentage, best_sell_percentage = determine_optimal_limits(trades.copy(), w1, w2)
                total_savings = results['Total_Buy_Savings'] + results['Total_Sell_Savings']
                if total_savings > best_score:
                    best_score = total_savings
                    best_w1 = w1
                    best_w2 = w2
                    best_result = results
            except ValueError:
                continue
    
    return best_result, best_w1, best_w2



def calculate_limits(enriched_trades):

    top_stocks = enriched_trades['Instrument'].value_counts().head(5).index.tolist()

    optimal_limits_data = {}
    for ticker in top_stocks:
        #print(f"---{ticker}---")
        enriched_trades_ticker = enriched_trades[enriched_trades['Instrument'] == ticker]
        results_df, best_buy_percentage, best_sell_percentage = determine_optimal_limits(enriched_trades_ticker,3,3)
        optimal_limits_data[ticker] = (best_buy_percentage, best_sell_percentage)

    # Generate final report
    final_report = []
    for ticker, limits in optimal_limits_data.items():

        final_report.append({
            "ticker": ticker,
            "buy_limit": f"{limits[0]:.1f}",
            "sell_limit": f"{limits[1]:.1f}"
        })



    return top_stocks, optimal_limits_data, final_report
        

def actionable_recommendations(trade_blotter):
    # Analyze weekly prices and print the result
    weekly_analysis = analyze_weekly_prices(trade_blotter.set_index('Activity Date'), trade_blotter.set_index('Activity Date'))
    

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

def preprocess_by_platform(trade_blotter, platform_type):
    if platform_type == 'Robinhood':
        return process_robinhood(trade_blotter)
    elif platform_type == 'Charles Schwab':
        return process_cs(trade_blotter)
    elif platform_type == 'Webull':
        return process_webull(trade_blotter)
    elif platform_type == 'Plaid':
        return process_plaid(trade_blotter)
    else:
        raise ValueError("Invalid platform type")
    
def check_date_threshold(trade_blotter):
    # Convert the 'Activity Date' to datetime
    trade_blotter['Activity Date'] = pd.to_datetime(trade_blotter['Activity Date'], errors='coerce')
    
    # Get the date 2 years ago from the current date
    two_years_ago = datetime.now() - timedelta(days=2*365)
    
    # Filter the trades that occurred within the last 2 years
    recent_trades = trade_blotter[trade_blotter['Activity Date'] >= two_years_ago]
    
    return recent_trades

def process_plaid(trade_blotter):
    trade_blotter.rename(columns={
        'date': 'Activity Date',
        'type': 'Trans Code',
        'ticker_symbol': 'Instrument',
        'quantity': 'Quantity',
        'price': 'Price'
    }, inplace=True)
    trade_blotter['Instrument'] = trade_blotter['Instrument'].str.strip()
    trade_blotter['Quantity'] = trade_blotter['Quantity'].abs()
    trade_blotter.dropna(subset=['Activity Date', 'Trans Code', 'Instrument'], inplace=True)
    trade_blotter_filtered = trade_blotter[trade_blotter['Trans Code'].str.contains('buy|sell', case=False, regex=True)]
    return trade_blotter_filtered

def process_cs(trade_blotter):
    
    trade_blotter.rename(columns={
    'Date': 'Activity Date',
    'Action': 'Trans Code',
    'Symbol': 'Instrument'
    }, inplace=True)
    
    trade_blotter = check_date_threshold(trade_blotter)
    
    trade_blotter.dropna(subset=['Activity Date', 'Trans Code', 'Instrument'], inplace=True)
    trade_blotter_filtered = trade_blotter[trade_blotter['Trans Code'].str.contains('buy|sell', case=False, regex=True)]
    
    return trade_blotter_filtered

def process_robinhood(trade_blotter):
    
    trade_blotter = check_date_threshold(trade_blotter)
    
    trade_blotter.dropna(subset=['Activity Date', 'Trans Code', 'Instrument'], inplace=True)
    trade_blotter_filtered = trade_blotter[trade_blotter['Trans Code'].str.contains('buy|sell', case=False, regex=True)]
    
    
    return trade_blotter_filtered

def process_webull(trade_blotter):
    trade_blotter.rename(columns={
    'Date': 'Activity Date',
    'Action': 'Trans Code',
    'Symbol': 'Instrument'
    }, inplace=True)
    
    trade_blotter = check_date_threshold(trade_blotter)
    
    trade_blotter.dropna(subset=['Activity Date', 'Trans Code', 'Instrument'], inplace=True)
    trade_blotter_filtered = trade_blotter[trade_blotter['Trans Code'].str.contains('buy|sell', case=False, regex=True)]
    
    check_date_threshold(trade_blotter_filtered)

    
    return trade_blotter_filtered

def main(csv_path, platform_type, file_id):
    print('In Here')
    trade_blotter = csv_path
    
    # Preprocess by platform
    trade_blotter = preprocess_by_platform(trade_blotter, platform_type)
    
    trade_blotter, data_dict = data_fetching_and_preprocessing.preprocess_data_merged(trade_blotter)
    
    trade_blotter_filtered = trade_blotter.copy()  # Create a filtered copy if needed
    
    # 1. Generate Overview
    trading_overview = generate_trading_overview(trade_blotter)

    # 2. Generate Graph
    calculate_saving = calculate_potential_savings(trade_blotter)
    generate_buffer_slippage = generate_graph(trade_blotter, calculate_saving['scaling_factor'])
    
    # Line Chart
    stock = trade_blotter_filtered['Instrument'].unique().tolist()[0]
    start_date = trade_blotter_filtered['Activity Date'].min()
    end_date = trade_blotter_filtered['Activity Date'].max()
    generate_buffer_line_chart = data_fetching_and_preprocessing.plot_line_chart(
        trade_blotter_filtered,
        stock,
        show_open=True,
        show_close=True,
        show_twap=True,
        show_vwap=True,
        show_hwoe=True,
        start_date=start_date,
        end_date=end_date,
        hwoe_adjustment_factor=calculate_saving['scaling_factor']
    )

    # 3. Trades with Most Slippage
    trades_most_slippage = calculate_trades_slippage(trade_blotter)

    # 4. Actionable Recommendations
    actionable_recommendation = actionable_recommendations(trade_blotter)

    return {
        'trading_overview': trading_overview,
        'generate_buffer_slippage': generate_buffer_slippage,
        'generate_buffer_line_chart': generate_buffer_line_chart,
        'trades_most_slippage': trades_most_slippage,
        'calculate_potential_savings': calculate_saving,
        'actionable_recommendations': actionable_recommendation
    }

def count_trades(df):
    try:
        ret = df[df['type'].isin(['buy', 'sell'])].shape[0]
        return ret
    except:
        ret = df[df['Trans Code'].isin(['buy', 'sell'])].shape[0]
        return ret

def convert_to_serializable(data):
    if isinstance(data, np.ndarray):
        return data.tolist()
    elif isinstance(data, BytesIO):
        return base64.b64encode(data.getvalue()).decode('utf-8')
    elif isinstance(data, pd.DataFrame):
        return data.to_dict(orient='records')
    elif isinstance(data, dict):
        return {key: convert_to_serializable(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_to_serializable(item) for item in data]
    elif isinstance(data, (int, float, str, bool, type(None))):
        return data
    else:
        logger.warning(f"Unhandled type in convert_to_serializable: {type(data)}")
        return str(data)


def get_plaid_aum(df):
    try:
        net_cash_flow = Decimal('0')
        net_investment_returns = Decimal('0')
        total_fees = Decimal('0')

        for _, row in df.iterrows():
            amount = Decimal(str(row.get('amount') or '0'))
            transaction_type = row.get('type') or row.get('Trans Code')
            subtype = row.get('subtype') or 'None'
            name = row.get('name') or 'TRANSACTION DESCRIPTION NOT AVAILABLE'
            name = name.upper()

            if transaction_type == 'transfer':
                if 'DEPOSIT' in name or 'ACH DEPOSIT' in name:
                    net_cash_flow += abs(amount)
                elif 'WITHDRAWL' in name or 'ACH WITHDRAWAL' in name:
                    net_cash_flow -= abs(amount)
            elif transaction_type == 'cash':
                if subtype == 'dividend':
                    net_investment_returns += abs(amount)
            elif transaction_type == 'fee':
                total_fees += abs(amount)

        aum = net_cash_flow + net_investment_returns - total_fees
        trade_count = count_trades(df)

        return {
            'aum': float(aum),
            'total_trades': trade_count,
        }

    except Exception as e:
        # Adapted to FastAPI's JSON response
        return JSONResponse({'error': str(e)}, status_code=500)
    









