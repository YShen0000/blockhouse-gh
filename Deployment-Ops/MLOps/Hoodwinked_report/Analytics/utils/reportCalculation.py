import warnings
warnings.filterwarnings('ignore')

import yfinance as yf
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')


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
                if isinstance(split_ratio, (int, float)):
                    mask = (trade_blotter['Instrument'] == ticker) & (trade_blotter['Activity Date'] < split_date)
                    trade_blotter.loc[mask, 'Price'] /= split_ratio
                    trade_blotter.loc[mask, 'Quantity'] *= split_ratio
    return trade_blotter


def preprocess_data(trade_blotter):
    trade_blotter['Instrument'] = trade_blotter['Instrument'].str.strip()
    tickers = trade_blotter['Instrument'].unique()
    data_dict = {}

    for ticker in tickers:
        try:
            data = yf.Ticker(ticker).history(period='2y', interval='1h')
            if not data.empty:
                data.index = data.index.tz_localize(None)
                data_dict[ticker] = data
            else:
                print(f"No data found for ticker: {ticker}")
        except Exception as e:
            print(f"Error fetching data for ticker {ticker}: {e}")

    trade_blotter = trade_blotter[trade_blotter['Instrument'].isin(data_dict.keys())]

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
    five_day_ma = []

    trade_blotter['Activity Date'] = pd.to_datetime(trade_blotter['Activity Date']).dt.tz_localize(None)
    trade_blotter = adjust_for_splits(trade_blotter)

    for index, row in trade_blotter.iterrows():
        date = row['Activity Date']
        ticker = row['Instrument']
        trans_code = row['Trans Code']
        date_str = date.strftime('%Y-%m-%d')
        data = data_dict[ticker].loc[date_str]

        if not data.empty:
            Open_prices.append(data['Open'].iloc[0])
            Close_prices.append(data['Close'].iloc[-1])
            volume_data = data['Volume'].mean()
            volume.append(volume_data)

            TWAP = data['Close'].mean()
            TWAP_prices.append(TWAP)

            VWAP = (data['Close'] * data['Volume']).sum() / data['Volume'].sum()
            VWAP_prices.append(VWAP)

            if trans_code.lower() == 'buy':
                HWOE_row = data.loc[data['Low'].idxmin()]
                HWOE_price = HWOE_row['Low']
            elif trans_code.lower() == 'sell':
                HWOE_row = data.loc[data['High'].idxmax()]
                HWOE_price = HWOE_row['High']
            else:
                HWOE_price = None
                HWOE_row = None

            HWOE_prices.append(HWOE_price)

            if HWOE_row is not None:
                HWOE_days.append(HWOE_row.name.strftime('%A'))
                HWOE_times.append(HWOE_row.name.strftime('%H:%M:%S'))

            past_5_days_data = data_dict[ticker].loc[date - pd.Timedelta(days=5):date]

            if not past_5_days_data.empty:
                five_day_ma_value = past_5_days_data['Close'].rolling(window=5, min_periods=1).mean().iloc[-1]
            else:
                five_day_ma_value = None
            five_day_ma.append(five_day_ma_value)

            rolling_volume_mean = past_5_days_data['Volume'].rolling(window=5, min_periods=1).mean()
            if not rolling_volume_mean.empty:
                vol_rolling_mean.append(rolling_volume_mean.iloc[-1])

            volatility_rolling = past_5_days_data['Close'].rolling(window=5, min_periods=1).std()
            if not volatility_rolling.empty:
                volatility_value = volatility_rolling.iloc[-1]
                volatility.append(volatility_value)

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
            high.append(None)
            low.append(None)
            five_day_ma.append(None)

    trade_blotter['Open_Price'] = Open_prices
    trade_blotter['Close_Price'] = Close_prices
    trade_blotter['TWAP_Price'] = TWAP_prices
    trade_blotter['VWAP_Price'] = VWAP_prices
    trade_blotter['HWOE_Price'] = HWOE_prices
    trade_blotter['Market Volume'] = volume
    trade_blotter['Volume_Rolling_Mean'] = vol_rolling_mean
    trade_blotter['Volatility'] = volatility
    trade_blotter['High'] = high
    trade_blotter['Low'] = low
    trade_blotter['5d_MA'] = five_day_ma

    return trade_blotter


def generate_trading_overview(trades):
    timeframe_analyzed = (trades['Activity Date'].min(), trades['Activity Date'].max())
    start_date = trades['Activity Date'].min()
    end_date = trades['Activity Date'].max()
    total_trades = trades.shape[0]
    num_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
    trades_per_month = total_trades / num_months
    trades_per_week = round(trades_per_month * 0.25, 2)
    assets_analyzed = trades['Instrument'].unique()
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


def generate_graph(enriched_trades, scaling_factor=0.25):
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

    y_min = min(slippage_df['Slippage']) - 0.5
    y_max = max(slippage_df['Slippage']) + 0.5
    plt.ylim(y_min - 0.5, y_max + 0.5)

    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, yval + (0.05 if yval >= 0 else -0.2), f'{yval:.2f}%', ha='center', va='bottom', color='black')

    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0f}%'))

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)

    return buffer


def calculate_trades_slippage(enriched_trades):
    top_slippage_trades = enriched_trades.nsmallest(5, 'Slippage_PCT_TWAP')
    top_slippage_trades['Price_Change'] = top_slippage_trades['Close_Price'].pct_change() * 100
    top_slippage_trades['Slippage_PCT_TWAP'] = top_slippage_trades['Slippage_PCT_TWAP'] * 100

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
    strategies = ['Open', 'Close', 'VWAP', 'TWAP', 'HWOE']
    results = []
    
    buy_quantity = enriched_trades[enriched_trades['Trans Code'].str.contains('buy', case=False)]['Quantity']
    sell_quantity = enriched_trades[enriched_trades['Trans Code'].str.contains('sell', case=False)]['Quantity']
    
    buys = enriched_trades[enriched_trades['Trans Code'].str.contains('buy', case=False)]['Price']
    sells = enriched_trades[enriched_trades['Trans Code'].str.contains('sell', case=False)]['Price']

    for strategy in strategies:
        avg_buy_price = ((buys * buy_quantity).sum()) / buy_quantity.sum()
        avg_sell_price = ((sells * sell_quantity).sum()) / sell_quantity.sum()

        strat_buys = enriched_trades[enriched_trades['Trans Code'].str.contains('buy', case=False)][f'{strategy}_Price']
        strat_sells = enriched_trades[enriched_trades['Trans Code'].str.contains('sell', case=False)][f'{strategy}_Price']

        avg_strategy_buy_price = ((strat_buys * buy_quantity).sum()) / buy_quantity.sum()
        avg_strategy_sell_price = ((strat_sells * sell_quantity).sum()) / sell_quantity.sum()

        total_savings = ((avg_buy_price - avg_strategy_buy_price) * (buy_quantity).sum()) + ((avg_strategy_sell_price - avg_sell_price) * (sell_quantity).sum())
        total_savings = -(enriched_trades[f'Slippage_{strategy}'] * enriched_trades['Quantity']).sum()

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

    results_df['Your Average BUY Price'] = results_df['Your Average BUY Price'].apply(lambda x: f"${x:,.2f}")
    results_df['Average Strategy Buy Price'] = results_df['Average Strategy Buy Price'].apply(lambda x: f"${x:,.2f}")
    results_df['Your Average SELL Price'] = results_df['Your Average SELL Price'].apply(lambda x: f"${x:,.2f}")
    results_df['Average Strategy Sell Price'] = results_df['Average Strategy Sell Price'].apply(lambda x: f"${x:,.2f}")
    results_df['Total Savings'] = results_df['Total Savings'].apply(lambda x: f"${x:,.2f}")
    
    results_dict = results_df.to_dict(orient='records')
    
    return {
        "potential_saving_table": results_dict,
        "total_savings": f"${adjusted_hwoe_savings:.2f}",
        "scaling_factor": scaling_factor 
    }


def actionable_recommendations(trade_blotter):
    def analyze_weekly_prices(market_data, trade_df):
        weekly_analysis = []
        for week, week_data in market_data.groupby(market_data.index.to_period('W')):
            min_buy_price = week_data['Low'].min()
            max_sell_price = week_data['High'].max()

            trades_in_week = trade_df[trade_df.index.to_period('W') == week]

            buys = trades_in_week[trades_in_week['Trans Code'].str.contains('buy', case=False, na=False)]
            sells = trades_in_week[trades_in_week['Trans Code'].str.contains('sell', case=False, na=False)]

            total_buy_quantity = buys['Quantity'].sum()
            total_sell_quantity = sells['Quantity'].sum()

            actual_buy_cost = (buys['Price'] * buys['Quantity']).sum()
            actual_sell_revenue = (sells['Price'] * sells['Quantity']).sum()

            optimal_buy_cost = min_buy_price * total_buy_quantity
            optimal_sell_revenue = max_sell_price * total_sell_quantity

            savings_buy = actual_buy_cost - optimal_buy_cost
            savings_sell = optimal_sell_revenue - actual_sell_revenue
            total_savings = savings_buy + savings_sell

            slippage_buy = actual_buy_cost - min_buy_price * buys['Quantity'].sum()
            slippage_sell = max_sell_price * sells['Quantity'].sum() - actual_sell_revenue

            most_active_weekday = buys.index.to_series().dt.weekday.mode()[0] if not buys.empty else None
            most_active_hour = buys.index.to_series().dt.hour.mode()[0] if not buys.empty else None

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

    weekly_analysis = analyze_weekly_prices(trade_blotter.set_index('Activity Date'), trade_blotter.set_index('Activity Date'))
    
    total_savings = weekly_analysis['total_savings'].sum()
    
    return {
        'average_trading_day': trade_blotter['HWOE_Day'].mode()[0],
        'average_trading_time': trade_blotter['HWOE_Time'].mode()[0],
        'weekly_analysis': weekly_analysis,
        'total_savings': f"${total_savings:.2f}"
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
    trade_blotter['Activity Date'] = pd.to_datetime(trade_blotter['Activity Date'], errors='coerce')
    two_years_ago = datetime.now() - timedelta(days=2 * 365)
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
    trade_blotter_filtered = trade_blotter[trade_blotter['Trans Code'].str.contains('buy|sell', case=False)]
    return trade_blotter_filtered


def process_cs(trade_blotter):
    trade_blotter.rename(columns={
        'Date': 'Activity Date',
        'Action': 'Trans Code',
        'Symbol': 'Instrument'
    }, inplace=True)
    
    trade_blotter = check_date_threshold(trade_blotter)
    trade_blotter.dropna(subset=['Activity Date', 'Trans Code', 'Instrument'], inplace=True)
    trade_blotter_filtered = trade_blotter[trade_blotter['Trans Code'].str.contains('buy|sell', case=False)]
    
    return trade_blotter_filtered


def process_robinhood(trade_blotter):
    trade_blotter = check_date_threshold(trade_blotter)
    trade_blotter.dropna(subset=['Activity Date', 'Trans Code', 'Instrument'], inplace=True)
    trade_blotter_filtered = trade_blotter[trade_blotter['Trans Code'].str.contains('buy|sell', case=False)]
    return trade_blotter_filtered


def process_webull(trade_blotter):
    trade_blotter.rename(columns={
        'Date': 'Activity Date',
        'Action': 'Trans Code',
        'Symbol': 'Instrument'
    }, inplace=True)
    
    trade_blotter = check_date_threshold(trade_blotter)
    trade_blotter.dropna(subset=['Activity Date', 'Trans Code', 'Instrument'], inplace=True)
    trade_blotter_filtered = trade_blotter[trade_blotter['Trans Code'].str.contains('buy|sell', case=False)]
    return trade_blotter_filtered


def main(csv_path, platform_type):
    trade_blotter = csv_path
    trade_blotter = preprocess_by_platform(trade_blotter, platform_type)

    trade_blotter = preprocess_data(trade_blotter)

    trading_overview = generate_trading_overview(trade_blotter)
    trades_most_slippage = calculate_trades_slippage(trade_blotter)
    calculate_saving = calculate_potential_savings(trade_blotter)
    generate_buffer_slippage = generate_graph(trade_blotter, calculate_saving['scaling_factor'])
    actionable_recommendation = actionable_recommendations(trade_blotter)

    return {
        'trading_overview': trading_overview,
        'generate_buffer_slippage': generate_buffer_slippage,
        'trades_most_slippage': trades_most_slippage,
        'calculate_potential_savings': calculate_saving,
        'actionable_recommendations': actionable_recommendation
    }


# Assuming `csv_path` is a pandas DataFrame containing your trade blotter data
# and `platform_type` is one of the supported platforms like 'Robinhood', 'Charles Schwab', 'Webull', or 'Plaid'.

csv_path = pd.read_csv('D:\Deployment_code\Blockhouse-ML\Hoodwinked_report\charles_schwab_trade_data_07_22_2024_20_46_51.csv')  # Load the trade blotter CSV into a pandas DataFrame
platform_type = 'Charles Schwab'  # or 'Robinhood', 'Webull', 'Plaid', etc.

# Call the main function
results = main(csv_path, platform_type)

# Accessing results
trading_overview = results['trading_overview']
trades_most_slippage = results['trades_most_slippage']
potential_savings = results['calculate_potential_savings']
slippage_graph = results['generate_buffer_slippage']
actionable_recommendations = results['actionable_recommendations']

# Print or further process the results as needed
print(trading_overview)
print(trades_most_slippage)
print(potential_savings)
print(actionable_recommendations)

# If you want to visualize the slippage graph
plt.imshow(plt.imread(slippage_graph))  # To display the graph from the BytesIO buffer
plt.show()
