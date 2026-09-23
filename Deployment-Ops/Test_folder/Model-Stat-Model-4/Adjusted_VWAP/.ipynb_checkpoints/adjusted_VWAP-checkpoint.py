import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import pytz

from Adjusted_VWAP.utils.fetch_merge_data import PolygonClient
from Adjusted_VWAP.utils.data_handler import DataProcessor, InferenceDataHandler

class TradingModel:
    def __init__(self, df, target_inventory=1000):
        self.df = df  # predicted df
        self.target_inventory = target_inventory
        self.position_size = 1/10 * target_inventory
        self.current_inventory = 0
        self.volatility_threshold = None
        self.nan_count = 0
        self.api_key = 'r65B9O5aplSJn7BWSo8z8pNH8v2wW5yc'

    def calculate_vwap(self):
        self.df['spread'] = ((self.df['high'] - self.df['low']) / 2).rolling(window=5, min_periods=1).mean()

        self.df['ILLIQ'] = self.df['spread'] / self.df['volume']

        # Log returns
        self.df['log_return'] = np.log(self.df['close'] / self.df['close'].shift(1))
        
        # Rolling volatility
        self.df['volatility'] = self.df['log_return'].rolling(window=5, min_periods=1).std() * np.sqrt(5)

        self.df['liquidity_volatility_factor'] = self.df['ILLIQ'] / (self.df['volatility'] + 1e-6)

        self.df['price_volume_liquidity_volatility'] = self.df['close'] * self.df['volume'] * self.df['liquidity_volatility_factor']
        self.df['volume_liquidity_volatility'] = self.df['volume'] * self.df['liquidity_volatility_factor']
        self.df['L_VWAP_ILLIQ_VOL'] = self.df['price_volume_liquidity_volatility'].cumsum() / self.df['volume_liquidity_volatility'].cumsum()
        self.df['VWAP_5min'] = self.df['price_volume_liquidity_volatility'].rolling(window=5, min_periods=1).sum() / self.df['volume_liquidity_volatility'].rolling(window=5, min_periods=1).sum()

    def calculate_vwap_bands(self, alpha=2):
        self.df['VWAP_5min_std'] = self.df['VWAP_5min'].rolling(window=5, min_periods=1).std()
        self.df['VWAP_5min_upper_band'] = self.df['VWAP_5min'] + (alpha * self.df['VWAP_5min_std'])
        self.df['VWAP_5min_lower_band'] = self.df['VWAP_5min'] - (alpha * self.df['VWAP_5min_std'])

    def calculate_technical_indicators(self):
        # EWMA
        self.df['EWMA_20'] = self.df['close'].ewm(span=20, adjust=False).mean()

        # RSI
        window_length = 14
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window_length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window_length).mean()
        rs = gain / loss
        self.df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        short_ema = self.df['close'].ewm(span=12, adjust=False).mean()
        long_ema = self.df['close'].ewm(span=26, adjust=False).mean()
        self.df['MACD'] = short_ema - long_ema
        self.df['MACD_signal'] = self.df['MACD'].ewm(span=9, adjust=False).mean()

        # ATR
        self.df['high_low'] = self.df['high'] - self.df['low']
        self.df['high_close'] = (self.df['high'] - self.df['close'].shift()).abs()
        self.df['low_close'] = (self.df['low'] - self.df['close'].shift()).abs()
        self.df['true_range'] = self.df[['high_low', 'high_close', 'low_close']].max(axis=1)
        self.df['ATR_14'] = self.df['true_range'].rolling(window=14, min_periods=1).mean()
        self.volatility_threshold = self.df['ATR_14'].mean()

    def generate_signals(self, voters=2):
        self.df['signal_vwap_band'] = 0
        self.df.loc[self.df['close'] < self.df['VWAP_5min_lower_band'], 'signal_vwap_band'] = 1
        self.df.loc[self.df['close'] > self.df['VWAP_5min_upper_band'], 'signal_vwap_band'] = -1

        self.df['signal_rsi'] = 0
        self.df.loc[self.df['RSI'] < 30, 'signal_rsi'] = 1
        self.df.loc[self.df['RSI'] > 70, 'signal_rsi'] = -1

        self.df['signal_macd'] = 0
        self.df.loc[self.df['MACD'] > self.df['MACD_signal'], 'signal_macd'] = 1
        self.df.loc[self.df['MACD'] < self.df['MACD_signal'], 'signal_macd'] = -1

        self.df['combined_signal'] = self.df[['signal_vwap_band', 'signal_rsi', 'signal_macd']].sum(axis=1)
        self.df['final_signal'] = 0
        self.df.loc[self.df['combined_signal'] >= voters, 'final_signal'] = 1
        self.df.loc[self.df['combined_signal'] <= -voters, 'final_signal'] = -1
        #self.df.to_csv('./temp/data.csv')

    def decide_order_type(self, idx, action='sell', future_minutes=25):
        # Method implementation as shown above
        # (Copy the decide_order_type method provided earlier)
        # [Include the complete method here]

        # Get the future data
        future_df = self.df.iloc[idx+1 : idx+1+future_minutes].copy()
        
        if future_df.empty or len(future_df) < 2:
            # Not enough data ahead, default to market order
            return 'market', None
        
        # Calculate mid_prices
        future_df['mid_price'] = (future_df['open'] + future_df['close']) / 2
        
        # Fit linear regression
        X = np.arange(len(future_df)).reshape(-1,1)
        y = future_df['mid_price'].values.reshape(-1,1)
        reg = LinearRegression().fit(X, y)
        slope = reg.coef_[0][0]
        
        # Calculate volatility over that interval
        returns = future_df['close'].pct_change().dropna()
        if len(returns) < 1:
            return 'market', None
        volatilities = returns.rolling(window=5).std().dropna()
        
        if len(volatilities) < 1:
            return 'market', None
        
        # Compute the 70th percentile of volatility over that interval
        volatility_threshold = np.percentile(volatilities, 70)
        current_volatility = volatilities.iloc[-1]  # use the last calculated volatility
        
        if current_volatility > volatility_threshold:
            # Volatility is high
            if action == 'sell':
                if slope > 0:
                    # For selling: if trend is up, set limit order
                    order_type = 'limit'
                    # Get the second highest mid_price in the interval
                    second_highest_mid_price = future_df['mid_price'].nlargest(2).iloc[-1]
                    price = second_highest_mid_price
                else:
                    # Trend is down
                    order_type = 'market'
                    price = None
            elif action == 'buy':
                if slope < 0:
                    # For buying: if trend is down, set limit order
                    order_type = 'limit'
                    # Get the second lowest mid_price in the interval
                    second_lowest_mid_price = future_df['mid_price'].nsmallest(2).iloc[-1]
                    price = second_lowest_mid_price
                else:
                    # Trend is up
                    order_type = 'market'
                    price = None
        else:
            # Volatility is low, execute market order
            order_type = 'market'
            price = None
        
        return order_type, price

    def generate_buy_timeline(self, target_inventory=1000):
        # Method implementation as shown above
        # (Copy the generate_buy_timeline method provided earlier)
        # [Include the complete method here]

        timeline = []
        total_inventory = 0  # Start with no inventory
        total_bought = 0  # Keep track of the total bought amounts
        buy_amounts = []  # To store all the buy amounts
        buy_indices = []  # To store the indices of timeline entries
        n=0
        for idx in range(len(self.df)):
            if pd.isna(self.df.loc[idx, 'volatility']):
                continue  # Skip rows with missing volatility

            final_signal = self.df.loc[idx, 'final_signal']
            signal_strength = abs(self.df.loc[idx, 'combined_signal'])
            volatility_factor = self.df.loc[idx, 'ATR_14'] / self.volatility_threshold

            if pd.isna(volatility_factor) or volatility_factor == 0:
                self.nan_count += 1
                volatility_factor = 1  # Default fallback

            try:
                dynamic_position_size = max(1, int(self.position_size * signal_strength / volatility_factor))  # Minimum size 1
                _, _, bid_sizes, ask_sizes, bid_prices, ask_prices = self.get_expected_price('AAPL', self.df.loc[idx, 'datetime'])
                current_price = self.calculate_vwap1(bid_prices, bid_sizes, dynamic_position_size)
            except ValueError as e:
                continue  # Skip problematic rows

            if final_signal == 1 and total_inventory < target_inventory and n < 10:
                purchase_amount = min(dynamic_position_size, target_inventory - total_inventory)
                total_inventory += purchase_amount
                total_bought += purchase_amount
                buy_amounts.append(purchase_amount)
                buy_indices.append(len(timeline))  # Store the index for potential adjustment

                # Decide order type and price
                order_type, price = self.decide_order_type(idx, action='buy')
                timeline.append({
                    'timestamp': self.df.loc[idx, 'datetime'],
                    'action': 'buy',
                    'shares': purchase_amount,
                    'price': current_price,
                    'order_type': order_type,
                    'limit_price': price,
                    'signal_strength': signal_strength,
                    'volatility_factor': volatility_factor,
                    'dynamic_position_size': dynamic_position_size,
                    'total_inventory': total_inventory
                })
                n+=1
            elif total_inventory < target_inventory and n < 10:
                timeline.append({
                    'timestamp': self.df.loc[idx, 'datetime'],
                    'action': 'hold',
                    'shares': 0,
                    'price': current_price,
                    'order_type': None,
                    'limit_price': None,
                    'signal_strength': signal_strength,
                    'volatility_factor': volatility_factor,
                    'dynamic_position_size': dynamic_position_size,
                    'total_inventory': total_inventory
                })
            elif total_inventory >= target_inventory or n == 10:
                timeline.append({
                    'timestamp': self.df.loc[idx, 'datetime'],
                    'action': 'finished',
                    'shares': 0,
                    'price': current_price,
                    'order_type': None,
                    'limit_price': None,
                    'signal_strength': signal_strength,
                    'volatility_factor': volatility_factor,
                    'dynamic_position_size': dynamic_position_size,
                    'total_inventory': target_inventory
                })

        # Adjust for any remaining inventory
        if total_inventory < target_inventory and total_bought > 0:
            print(f'We have remaining shares: {buy_amounts}')
            remaining_inventory = target_inventory - total_inventory
            total_initial_buy = sum(buy_amounts)
            total_inventory=0
            for i, buy_amount in enumerate(buy_amounts):
                if i == len(buy_amounts)-1:
                    final_buy_amount=target_inventory-total_inventory
                    total_inventory+=final_buy_amount
                    timeline[buy_indices[i]]['total_inventory']=total_inventory
                    timeline[buy_indices[i]]['shares'] = final_buy_amount
                else:
                    adjustment = (buy_amount / total_initial_buy) * remaining_inventory
                    adjustment = int(round(adjustment))
                    final_buy_amount = timeline[buy_indices[i]]['shares'] + adjustment
                    total_inventory+=final_buy_amount
                    timeline[buy_indices[i]]['total_inventory']=total_inventory
                    timeline[buy_indices[i]]['shares'] = final_buy_amount

        # Fall back strategy
        if total_inventory < target_inventory and total_bought == 0:
            print('Going to fall back strategy')
            # Implement VWAP strategy
            print("No signals generated. Implementing VWAP strategy.")
            
            # Calculate total volume for the day
            total_volume = self.df['volume'].sum()
            
            # Calculate cumulative volume and VWAP
            self.df['cumulative_volume'] = self.df['volume'].cumsum()
            self.df['volume_fraction'] = self.df['volume'] / total_volume
            self.df['VWAP'] = (self.df['close'] * self.df['volume']).cumsum() / self.df['cumulative_volume']
            
            # Set the number of trades
            num_trades = 10
            volume_checkpoints = [i/num_trades for i in range(1, num_trades+1)]
            
            remaining_inventory = target_inventory
            trade_count = 0
            last_checkpoint = 0
            
            for idx in range(len(self.df)):
                current_volume_fraction = self.df.loc[idx, 'cumulative_volume'] / total_volume
                
                if current_volume_fraction >= volume_checkpoints[trade_count] or idx == len(self.df) - 1:
                    volume_slice = current_volume_fraction - last_checkpoint
                    if remaining_inventory == 1:
                        buy_amount = 1
                    else:
                        buy_amount = int(target_inventory * volume_slice)
                        buy_amount = min(buy_amount, remaining_inventory)
                    if buy_amount > 0:
                        current_price = self.df.loc[idx, 'VWAP']
                        order_type, price = self.decide_order_type(idx, action='buy')
                        timeline.append({
                            'timestamp': self.df.loc[idx, 'datetime'],
                            'action': 'buy',
                            'shares': buy_amount,
                            'price': current_price,
                            'order_type': order_type, 
                            'limit_price': price,
                            'signal_strength': None,
                            'volatility_factor': None,
                            'dynamic_position_size': None,
                            'total_inventory': target_inventory - remaining_inventory + buy_amount
                        })
                        
                        remaining_inventory -= buy_amount
                        last_checkpoint = current_volume_fraction
                        trade_count += 1
                    
                    if trade_count >= num_trades or remaining_inventory <= 0:
                        break
            
            # If there's still remaining inventory, add it to the last buy
            if remaining_inventory > 0:
                last_buy = next((item for item in reversed(timeline) if item['action'] == 'buy'), None)
                if last_buy:
                    last_buy['shares'] += remaining_inventory
                    last_buy['total_inventory'] = target_inventory

        return timeline

    

    def generate_sell_timeline(self, total_inventory=1000):
        # Existing implementation (as provided earlier)
        # [Include the complete method here, same as before]

        timeline = []
        target_inventory = total_inventory
        total_sold = 0
        sell_amounts = []
        sell_indices = []
        n=0
        for idx in range(len(self.df)):
            if pd.isna(self.df.loc[idx, 'volatility']):
                continue  # Skip rows with missing volatility

            final_signal = self.df.loc[idx, 'final_signal']
            signal_strength = abs(self.df.loc[idx, 'combined_signal'])
            volatility_factor = self.df.loc[idx, 'ATR_14'] / self.volatility_threshold

            if pd.isna(volatility_factor) or volatility_factor == 0:
                self.nan_count += 1
                volatility_factor = 1  # Default fallback

            try:
                dynamic_position_size = max(1, int(self.position_size * signal_strength / volatility_factor))  # Minimum size 1
                _, _, bid_sizes, ask_sizes, bid_prices, ask_prices = self.get_expected_price('AAPL', self.df.loc[idx, 'datetime'])
                current_price = self.calculate_vwap1(ask_prices, ask_sizes, dynamic_position_size)
            except ValueError as e:
                continue  # Skip problematic rows

            if final_signal == -1 and total_inventory > 0  and n < 10:
                sell_amount = min(dynamic_position_size, total_inventory)
                total_inventory -= sell_amount
                total_sold += sell_amount
                sell_amounts.append(sell_amount)
                sell_indices.append(len(timeline))  # Store the index for potential adjustment

                # Decide order type and price
                order_type, price = self.decide_order_type(idx, action='sell')
                timeline.append({
                    'timestamp': self.df.loc[idx, 'datetime'],
                    'action': 'sell',
                    'shares': sell_amount,
                    'price': current_price,
                    'order_type': order_type,
                    'limit_price': price,
                    'signal_strength': signal_strength,
                    'volatility_factor': volatility_factor,
                    'dynamic_position_size': dynamic_position_size,
                    'total_inventory': total_inventory
                })
                n+=1
            elif total_inventory > 0 and n < 10:
                timeline.append({
                    'timestamp': self.df.loc[idx, 'datetime'],
                    'action': 'hold',
                    'shares': 0,
                    'price': current_price,
                    'order_type': None,
                    'limit_price': None,
                    'signal_strength': signal_strength,
                    'volatility_factor': volatility_factor,
                    'dynamic_position_size': dynamic_position_size,
                    'total_inventory': total_inventory
                })
            elif total_inventory <= 0 or n==10:
                timeline.append({
                    'timestamp': self.df.loc[idx, 'datetime'],
                    'action': 'finished',
                    'shares': 0,
                    'price': current_price,
                    'order_type': None,
                    'limit_price': None,
                    'signal_strength': signal_strength,
                    'volatility_factor': volatility_factor,
                    'dynamic_position_size': dynamic_position_size,
                    'total_inventory': total_inventory
                })

        # Adjust for any remaining inventory
        if total_inventory > 0 and total_sold > 0:
            total_initial_sell = sum(sell_amounts)
            for i, sell_amount in enumerate(sell_amounts):
                if i == len(sell_amounts)-1:
                    final_sell_amount = target_inventory
                    target_inventory-=final_sell_amount
                    timeline[sell_indices[i]]['total_inventory']=target_inventory
                    timeline[sell_indices[i]]['shares'] = final_sell_amount
                else:
                    adjustment = (sell_amount / total_initial_sell) * total_inventory
                    adjustment = int(round(adjustment))
                    final_sell_amount = timeline[sell_indices[i]]['shares'] + adjustment
                    target_inventory-=final_sell_amount
                    timeline[sell_indices[i]]['total_inventory']=target_inventory
                    timeline[sell_indices[i]]['shares'] = final_sell_amount
        
        # Fall back strategy
        if total_inventory > 0 and total_sold == 0:
            print('Going to fall back strategy')
            print("Implementing VWAP strategy for SELL operations.")

            # Calculate total volume for the day
            total_volume = self.df['volume'].sum()

            # Calculate cumulative volume and VWAP
            self.df['cumulative_volume'] = self.df['volume'].cumsum()
            self.df['volume_fraction'] = self.df['volume'] / total_volume
            self.df['VWAP'] = (self.df['close'] * self.df['volume']).cumsum() / self.df['cumulative_volume']

            # Set the number of trades
            num_trades = 10
            volume_checkpoints = [i / num_trades for i in range(1, num_trades + 1)]

            self.current_inventory = total_inventory
            remaining_inventory = total_inventory
            trade_count = 0
            last_checkpoint = 0
            timeline = []

            for idx in range(len(self.df)):
                current_volume_fraction = self.df.loc[idx, 'cumulative_volume'] / total_volume

                if current_volume_fraction >= volume_checkpoints[trade_count] or idx == len(self.df) - 1:
                    volume_slice = current_volume_fraction - last_checkpoint
                    if remaining_inventory == 1:
                        sell_amount = 1
                    else:
                        sell_amount = int(self.current_inventory * volume_slice)
                        sell_amount = min(sell_amount, remaining_inventory)
                    if sell_amount > 0:
                        current_price = self.df.loc[idx, 'VWAP']
                        # Add sell order to the timeline
                        order_type, price = self.decide_order_type(idx, action='sell')
                        timeline.append({
                            'timestamp': self.df.loc[idx, 'datetime'],
                            'action': 'sell',
                            'shares': sell_amount,
                            'price': current_price,
                            'order_type': order_type,  # Using market orders for VWAP strategy
                            'limit_price': price,
                            'signal_strength': None,
                            'volatility_factor': None,
                            'dynamic_position_size': None,
                            'total_inventory': self.current_inventory - remaining_inventory + sell_amount
                        })

                        remaining_inventory -= sell_amount
                        last_checkpoint = current_volume_fraction
                        trade_count += 1

                    if trade_count >= num_trades or remaining_inventory <= 0:
                        break

            # If there's still remaining inventory, add it to the last sell
            if remaining_inventory > 0:
                last_sell = next((item for item in reversed(timeline) if item['action'] == 'sell'), None)
                if last_sell:
                    last_sell['shares'] += remaining_inventory
                    last_sell['total_inventory'] = self.current_inventory

        return timeline

    def generate_dynamic_action_timeline(self, action='buy', target_inventory=1000):
        if action == 'buy':
            data = self.generate_buy_timeline(target_inventory=target_inventory)
            return pd.DataFrame(data)
        elif action == 'sell':
            data = self.generate_sell_timeline(total_inventory=target_inventory)
            return pd.DataFrame(data)
        else:
            raise ValueError("Invalid action specified. Please use 'buy' or 'sell'.")

    def get_expected_price(self, symbol, timestamp_str):
        # Mock implementation (since we don't have API access in this context)
        idx = self.df[self.df['datetime'] == timestamp_str].index[0]
        current_price = self.df.loc[idx, 'close']
        bid_price = current_price * 0.999
        ask_price = current_price * 1.001
        bid_sizes = [1000]
        ask_sizes = [1000]
        bid_prices = [bid_price]
        ask_prices = [ask_price]
        return bid_price, ask_price, bid_sizes, ask_sizes, bid_prices, ask_prices

    @staticmethod
    def calculate_vwap1(prices, sizes, size_of_slice):
        cum_sum_size = 0
        for idx, size in enumerate(sizes):
            cum_sum_size += size
            if cum_sum_size >= size_of_slice:
                break

        prices = np.array(prices[:idx+1])
        sizes = np.array(sizes[:idx+1])

        if np.sum(sizes) == 0:
            return 0.0  # Handle edge case

        vwap = np.sum(prices * sizes) / np.sum(sizes)
        return vwap
    


class Model:

    def infer_model(self, side='buy', timeframe=390, inventory = 1000, ticker = 'MSFT', end_timestamp = datetime.now(pytz.UTC).strftime('%Y-%m-%d'), backtest=False):
        # Pull data -- fetch and merge data
        data_dir = '/temp'  # Not needed -- placeholder
        data_client = PolygonClient(data_dir)
        data = data_client.fetch_and_merge_data(ticker,end_date=end_timestamp, backtest=backtest)

        # print('TEMP DATA')
        # print(data)
        # Forecast and form a dataset
        inference_data_handler = InferenceDataHandler()
        data = inference_data_handler.create_data_w_forecasts(data, steps = timeframe)

        # print('DATA:')
        # print(data)

        # Initialize the trading model
        model = TradingModel(df=data, target_inventory=inventory)

        # Calculate indicators and signals
        model.calculate_vwap()
        model.calculate_vwap_bands()
        model.calculate_technical_indicators()
        model.generate_signals()


        # Run the simulation for selling
        if side == 'sell':
            action_df = model.generate_dynamic_action_timeline(action='sell', target_inventory=inventory)
        else:
            
            action_df = model.generate_dynamic_action_timeline(action='buy', target_inventory=inventory)

        
        results_df = action_df[action_df['shares'] != 0] if 'shares' in action_df else print('No data')
        results_df['timestamp'] = pd.to_datetime(results_df['timestamp'], utc=True).dt.tz_convert('US/Eastern')
        #results_df.to_csv('./temp/action_results.csv')

        return results_df


if __name__ == '__main__':
    # We can infer model this way -- set additional parameter for end_timestamp to be the date that you want to back test on
    model = Model()
    print(model.infer_model(side='sell',inventory = 1, ticker='AAPL', end_timestamp = '2024-10-17'))