import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

class PostProcessing:
    def __init__(self,clientTrades):
        self.clientTrades = clientTrades
    def preprocess_by_platform(self,trade_blotter):
        # TODO : Will be defined specific of Quantbot

        # For now im just running the platform specific preprocessing for robinhood
        
        trade_blotter = self.check_date_threshold(trade_blotter)
        trade_blotter.dropna(subset=['Activity Date', 'Trans Code', 'Instrument'], inplace=True)
        return trade_blotter[trade_blotter['Trans Code'].str.contains('buy|sell', case=False, regex=True)]
        pass
    def is_fund(self,ticker_symbol):
        """
        Determine if a given ticker symbol represents a fund.

        Args:
        ticker_symbol (str): The ticker symbol to check.

        Returns:
        bool: True if the ticker represents a fund, False otherwise.
        """
        # Fetch the ticker info
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        # Funds often lack industry and sector info, or might have "Fund" or "ETF" in the long business summary
        industry = info.get('industry', None)
        sector = info.get('sector', None)

        return not industry and not sector
    def check_date_threshold(self,trade_blotter):
        """
        Filter clientTrades that occurred within the last 2 years.

        Args:
        trade_blotter (pd.DataFrame): DataFrame containing trade data.

        Returns:
        pd.DataFrame: Filtered DataFrame with recent clientTrades.
        """

        # Convert the 'Activity Date' to datetime
        trade_blotter['Activity Date'] = pd.to_datetime(trade_blotter['Activity Date'], errors='coerce')

        # Get the date 2 years ago from the current date
        two_years_ago = datetime.now() - timedelta(days=2*365)

        # Return the filtered clientTrades that occurred within the last 2 years
        return trade_blotter[trade_blotter['Activity Date'] >= two_years_ago]
    def adjust_for_splits(self,trade_blotter):
        """
        Adjust trade data for stock splits that occurred in the past two years.

        Args:
        trade_blotter (pd.DataFrame): DataFrame containing trade data.

        Returns:
        pd.DataFrame: DataFrame with adjusted prices and quantities for splits.
        """
        two_years_ago = datetime.now() - timedelta(days=2*365)
        tickers = trade_blotter['Instrument'].unique()

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                splits = stock.splits

                if not splits.empty:
                    splits.index = splits.index.tz_localize(None)
                    recent_splits = (splits[splits.index >= two_years_ago])
                    
                    for split_date, split_ratio in recent_splits.items():
                        # Ensure split_ratio is a number
                        if isinstance(split_ratio, (int, float)):
                            mask = (trade_blotter['Instrument'] == ticker) & (trade_blotter['Activity Date'] < split_date)
                            
                            # ONLY adjust shares purchased not price
                            # Brokerages do not record old share prices only your purchased quantity
                            # So prices do not need to be adjusted
                            trade_blotter.loc[mask, 'Quantity'] *= split_ratio
            
            except Exception as e:
                print(f"Error adjusting for splits for ticker {ticker}: {e}")
        
        return trade_blotter
    
    def calculate_metrics(self,trade_blotter, data_dict):
        """
        Calculate various metrics for each trade based on historical data.

        Args:
        trade_blotter (pd.DataFrame): DataFrame containing trade data.
        data_dict (dict): Dictionary containing historical data for each ticker.

        Returns:
        pd.DataFrame: DataFrame with additional columns for calculated metrics.
        """
        
        metrics = ['Open_Price', 'Close_Price', 'TWAP_Price', 'VWAP_Price', 'HWOE_Price', 'Market Volume',
                'Volume_Rolling_Mean', 'Volatility', 'Volatility_Rolling_Mean', 'High', 'Low', 'HWOE_Day',
                'HWOE_Time', '5d_MA']
        
        for metric in metrics:
            trade_blotter[metric] = None

        for index, row in trade_blotter.iterrows():
            date = row['Activity Date']
            ticker = row['Instrument']
            trans_code = row['Trans Code']
            quantity = row['Quantity']
            date_str = date.strftime('%Y-%m-%d')

            try:
                data = data_dict[ticker].loc[date_str]
                
                if not data.empty:
                    # Calculate various metrics
                    trade_blotter.at[index, 'Open_Price'] = data['Open'].iloc[0]
                    trade_blotter.at[index, 'Close_Price'] = data['Close'].iloc[-1]
                    trade_blotter.at[index, 'Market Volume'] = data['Volume'].mean()
                    trade_blotter.at[index, 'TWAP_Price'] = data['Close'].mean()
                    trade_blotter.at[index, 'VWAP_Price'] = (data['Close'] * data['Volume']).sum() / data['Volume'].sum()
                    
                    # Calculate HWOE price
                    if trans_code.lower() == 'buy':
                        HWOE_row = data.loc[data['Low'].idxmin()]
                        trade_blotter.at[index, 'HWOE_Price'] = HWOE_row['Low']
                    elif trans_code.lower() == 'sell':
                        HWOE_row = data.loc[data['High'].idxmax()]
                        trade_blotter.at[index, 'HWOE_Price'] = HWOE_row['High']
                    
                    if HWOE_row is not None:
                        trade_blotter.at[index, 'HWOE_Day'] = HWOE_row.name.strftime('%A')
                        trade_blotter.at[index, 'HWOE_Time'] = HWOE_row.name.strftime('%H:%M:%S')
                    
                    # Calculate 5-day moving average and other metrics
                    past_5_days_data = data_dict[ticker].loc[date - pd.Timedelta(days=5):date]
                    
                    if not past_5_days_data.empty:
                        trade_blotter.at[index, '5d_MA'] = past_5_days_data['Close'].rolling(window=5, min_periods=1).mean().iloc[-1]
                        trade_blotter.at[index, 'Volume_Rolling_Mean'] = past_5_days_data['Volume'].rolling(window=5, min_periods=1).mean().iloc[-1]
                        trade_blotter.at[index, 'Volatility'] = past_5_days_data['Close'].rolling(window=5, min_periods=1).std().iloc[-1]
                        trade_blotter.at[index, 'Volatility_Rolling_Mean'] = past_5_days_data['Close'].rolling(window=5, min_periods=1).std().rolling(window=5, min_periods=1).mean().iloc[-1]
                    
                    trade_blotter.at[index, 'High'] = data['High'].max()
                    trade_blotter.at[index, 'Low'] = data['Low'].min()
            
            except KeyError:
                print(f"No data found for ticker {ticker} on date {date_str}")
            except Exception as e:
                print(f"Error calculating metrics for ticker {ticker} on date {date_str}: {e}")
        
        return trade_blotter



    def calculate_slippage(self,trade_blotter):
        """
        Calculate slippage for each trade based on various price metrics.

        Args:
        trade_blotter (pd.DataFrame): DataFrame containing trade data and calculated metrics.

        Returns:
        pd.DataFrame: DataFrame with additional columns for slippage calculations.
        """
        price_types = ['Open', 'Close', 'TWAP', 'VWAP', 'HWOE']
        
        for price_type in price_types:
            trade_blotter[f'Slippage_{price_type}'] = None
            trade_blotter[f'Slippage_PCT_{price_type}'] = None
        
        for index, row in trade_blotter.iterrows():
            trans_code = row['Trans Code']
            trade_price = row['Price']
            
            for price_type in price_types:
                reference_price = row[f'{price_type}_Price']
                
                if pd.notnull(reference_price):
                    if trans_code.lower() == 'buy':
                        slippage = reference_price - trade_price
                    elif trans_code.lower() == 'sell':
                        slippage = trade_price - reference_price
                    else:
                        slippage = None
                    
                    trade_blotter.at[index, f'Slippage_{price_type}'] = slippage
                    trade_blotter.at[index, f'Slippage_PCT_{price_type}'] = slippage / reference_price if reference_price != 0 else None
        
        return trade_blotter


    def preprocess_data(self, trade_blotter):
        """
        Preprocess trade data by fetching historical data, calculating various metrics, and adjusting for splits.

        Args:
        trade_blotter (pd.DataFrame): DataFrame containing trade data.

        Returns:
        tuple:  1. Processed DataFrame merged with metrics and slippage data
                2. Dictionary of historical data.
                3. Error message (if applicable)
        """
        # Uncomment once preprocess_by_platform has been defined
        trade_blotter = self.preprocess_by_platform(self.clientTrades)  # Replace `clientTrades` with `self.clientTrades`

        # Error message to be returned if something goes wrong
        error_message = ''

        # Remove leading/trailing spaces in 'Instrument' column
        trade_blotter['Instrument'] = trade_blotter['Instrument'].str.strip().copy()

        # Define the tickers you need to fetch data for
        tickers = trade_blotter['Instrument'].unique()
        data_dict = {}

        # Fetch and store the data for each ticker
        fund_tickers = []
        for ticker in tickers:
            # Track which tickers are funds
            if self.is_fund(ticker):
                fund_tickers.append(ticker)
                continue
            try:
                data = yf.Ticker(ticker).history(period='2y', interval='1h')
                if not data.empty:
                    data.index = data.index.tz_localize(None)  # Ensure timezone-naive datetime
                    data_dict[ticker] = data
                else:
                    print(f"No data found for ticker: {ticker}")
            except Exception as e:
                print(f"Error fetching data for ticker {ticker}: {e}")

        # Check if all tickers are funds
        if len(fund_tickers) == len(tickers):
            error_message = "All tickers in the trade blotter are funds. We cannot process funds at this time."
            return None, None, error_message

        # Filter out clientTrades with tickers that couldn't fetch data
        trade_blotter = trade_blotter[trade_blotter['Instrument'].isin(data_dict.keys())]
        if trade_blotter.empty:
            error_message = "No valid trades found after filtering out funds and tickers without data."
            return None, None, error_message

        # Converting to dt and ensure timezone-naive
        trade_blotter['Activity Date'] = pd.to_datetime(trade_blotter['Activity Date']).dt.tz_localize(None).copy()

        # Added this to merge processing pipelines
        two_years_ago = pd.to_datetime('today') - pd.DateOffset(years=2)
        trade_blotter = trade_blotter[trade_blotter['Activity Date'] >= two_years_ago]

        # Adjust for stock splits
        trade_blotter = self.adjust_for_splits(trade_blotter)

        # Calculate metrics
        trade_blotter = self.calculate_metrics(trade_blotter, data_dict)

        # Calculate slippage
        trade_blotter = self.calculate_slippage(trade_blotter)

        return trade_blotter, data_dict, error_message

    def calculate_potential_savings(self,enriched_trades):
        """
        Calculates potential savings for different trading strategies based on enriched trade data.

        Args:
        enriched_trades (pd.DataFrame): A DataFrame containing enriched trade data.

        Returns:
        dict: A dictionary containing potential savings data and related information.
        """
        strategies = ['Open', 'Close', 'VWAP', 'TWAP', 'HWOE']
        results = []
        
        buy_quantity = enriched_trades[enriched_trades['Trans Code'].str.contains('buy', case=False)]['Quantity']
        sell_quantity = enriched_trades[enriched_trades['Trans Code'].str.contains('sell', case=False)]['Quantity']
        
        buys = enriched_trades[enriched_trades['Trans Code'].str.contains('buy', case=False)]['Price']
        sells = enriched_trades[enriched_trades['Trans Code'].str.contains('sell', case=False)]['Price']

        for strategy in strategies:
            avg_buy_price = ((buys*buy_quantity).sum())/buy_quantity.sum()
            avg_sell_price = ((sells*sell_quantity).sum())/sell_quantity.sum()
            
            strat_buys = enriched_trades[enriched_trades['Trans Code'].str.contains('buy', case=False)][f'{strategy}_Price']
            strat_sells = enriched_trades[enriched_trades['Trans Code'].str.contains('sell', case=False)][f'{strategy}_Price']
            
            avg_strategy_buy_price = ((strat_buys*buy_quantity).sum())/buy_quantity.sum()
            avg_strategy_sell_price = ((strat_sells*sell_quantity).sum())/sell_quantity.sum()
            
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
        
        outputDict = {"potential_savings_table" : results_dict,"total_savings":f"${adjusted_hwoe_savings:.2f}","scaling_factor": scaling_factor }
        return outputDict
    def genReport(self):
        try : 
            # TODO : Uncomment once preprocess_by_platform has been defined
            trade_blotter = self.preprocess_by_platform(self.clientTrades)
            trade_blotter,data_dict,error_message = self.preprocess_data(trade_blotter)
            # report = self.calculate_potential_savings(trade_blotter)['scaling_factor']
            report = self.calculate_potential_savings(trade_blotter)
            return report
        except Exception as e:
            return f"Error : {e}"
