
from sklearn.linear_model import LinearRegression
import numpy as np

class MicroTrader:
    @staticmethod
    def decide_order_type(idx, data, action='sell', future_minutes=25):
        # Method implementation as shown above
        # (Copy the decide_order_type method provided earlier)
        # [Include the complete method here]

        # Get the future data
        future_df = data[idx+1 : idx+1+future_minutes].copy()
        
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