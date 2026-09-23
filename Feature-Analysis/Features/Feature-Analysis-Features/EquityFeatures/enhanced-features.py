import numpy as np
import pandas as pd
from scipy.stats import linregress

class EnhancedFeatures:
    def __init__(self, df):
        self.df = df.copy()
        
    def calculate_all_features(self):
        """Calculate all enhanced features"""
        self.add_price_momentum_features()
        self.add_volume_features()
        self.add_volatility_features()
        self.add_orderbook_features()
        self.add_market_regime_features()
        return self.df
        
    def add_price_momentum_features(self):
        """Enhanced price momentum indicators"""
        # Hull Moving Average (HMA)
        def hull_moving_average(series, period):
            half_period = int(period/2)
            sqrt_period = int(np.sqrt(period))
            
            wma1 = series.ewm(span=half_period, adjust=False).mean()
            wma2 = series.ewm(span=period, adjust=False).mean()
            diff = 2 * wma1 - wma2
            return diff.ewm(span=sqrt_period, adjust=False).mean()
        
        # Calculate HMA for different periods
        self.df['HMA_fast'] = hull_moving_average(self.df['close'], 9)
        self.df['HMA_slow'] = hull_moving_average(self.df['close'], 21)
        
        # Adaptive Moving Average Crossover
        self.df['adaptive_ma_signal'] = np.where(
            self.df['HMA_fast'] > self.df['HMA_slow'], 1,
            np.where(self.df['HMA_fast'] < self.df['HMA_slow'], -1, 0)
        )
        
        # Price Momentum Score
        rolling_windows = [5, 10, 20]
        momentum_scores = []
        
        for window in rolling_windows:
            returns = self.df['close'].pct_change(window)
            momentum_scores.append(returns.rank(pct=True))
            
        self.df['momentum_score'] = sum(momentum_scores) / len(rolling_windows)

    def add_volume_features(self):
        """Enhanced volume-based features"""
        # Volume Weighted Trend Indicator
        self.df['volume_ma'] = self.df['volume'].rolling(window=20).mean()
        self.df['relative_volume'] = self.df['volume'] / self.df['volume_ma']
        
        # Volume-Price Trend (VPT)
        price_change = self.df['close'].pct_change()
        self.df['VPT'] = (1 + price_change) * self.df['volume']
        self.df['VPT'] = self.df['VPT'].cumsum()
        
        # Volume Force Index
        self.df['force_index'] = self.df['close'].diff() * self.df['volume']
        self.df['force_index_ema'] = self.df['force_index'].ewm(span=13).mean()
        
        # Relative Volume Profile
        def calculate_volume_profile(group):
            return group['volume'] / group['volume'].sum()
            
        self.df['time_of_day'] = pd.to_datetime(self.df['datetime']).dt.time
        self.df['relative_volume_profile'] = self.df.groupby('time_of_day')['volume'].transform(calculate_volume_profile)

    def add_volatility_features(self):
        """Enhanced volatility features"""
        # Parkinson Volatility
        self.df['parkinson_vol'] = np.sqrt(
            (1 / (4 * np.log(2))) * 
            ((np.log(self.df['high'] / self.df['low'])) ** 2)
        )
        
        # Yang Zhang Volatility
        def yang_zhang_volatility(high, low, open, close, window=20):
            rs = np.log(close / close.shift(1))
            ro = np.log(open / close.shift(1))
            
            sigma_rs = rs.rolling(window=window).var()
            sigma_ro = ro.rolling(window=window).var()
            
            h = np.log(high / open)
            l = np.log(low / open)
            sigma_c = (h * (h - np.log(close / open)) + l * (l - np.log(close / open))).rolling(window=window).mean()
            
            k = 0.34 / (1.34 + (window + 1) / (window - 1))
            sigma_sq = sigma_ro + k * sigma_rs + (1 - k) * sigma_c
            return np.sqrt(sigma_sq * 252)
            
        self.df['yang_zhang_vol'] = yang_zhang_volatility(
            self.df['high'], self.df['low'], 
            self.df['open'], self.df['close']
        )
        
        # Volatility Regime
        self.df['vol_regime'] = pd.qcut(
            self.df['yang_zhang_vol'].rolling(window=20).mean(),
            q=5, labels=['very_low', 'low', 'medium', 'high', 'very_high']
        )
        
        # Realized Volatility Ratio
        realized_vol = self.df['close'].pct_change().rolling(window=20).std() * np.sqrt(252)
        self.df['real_implied_vol_ratio'] = realized_vol / self.df['yang_zhang_vol']

    def add_orderbook_features(self):
        """Enhanced order book features"""
        # Price Impact Score
        def estimate_price_impact(row):
            return (row['volume'] / row['volume_ma']) * abs(row['close'] - row['vwap'])
            
        self.df['vwap'] = (self.df['close'] * self.df['volume']).cumsum() / self.df['volume'].cumsum()
        self.df['price_impact_score'] = self.df.apply(estimate_price_impact, axis=1)
        
        # Liquidity Score
        self.df['liquidity_score'] = (
            self.df['volume'] * 
            (1 / (self.df['high'] - self.df['low']).replace(0, np.nan))
        ).rolling(window=20).mean()
        
        # Order Flow Imbalance
        self.df['price_change'] = self.df['close'].diff()
        self.df['order_flow'] = np.where(
            self.df['price_change'] > 0, self.df['volume'],
            np.where(self.df['price_change'] < 0, -self.df['volume'], 0)
        )
        self.df['order_flow_imbalance'] = self.df['order_flow'].rolling(window=20).sum()

    def add_market_regime_features(self):
        """Enhanced market regime features"""
        # Trend Strength Indicator
        def calculate_trend_strength(series, window=20):
            rolling_std = series.rolling(window=window).std()
            rolling_mean = series.rolling(window=window).mean()
            return abs(series - rolling_mean) / rolling_std
            
        self.df['trend_strength'] = calculate_trend_strength(self.df['close'])
        
        # Market Efficiency Ratio
        def market_efficiency_ratio(series, window=20):
            abs_returns = abs(series.diff()).rolling(window=window).sum()
            net_returns = abs(series - series.shift(window))
            return net_returns / abs_returns
            
        self.df['market_efficiency'] = market_efficiency_ratio(self.df['close'])
        
        # Regime Change Probability
        self.df['regime_change_prob'] = (
            (self.df['trend_strength'].rolling(window=10).std() * 
             self.df['real_implied_vol_ratio'].rolling(window=10).std())
        ).rank(pct=True)

    def generate_combined_signals(self):
        """Generate trading signals based on combined features"""
        # Momentum signals
        momentum_signal = np.where(
            (self.df['momentum_score'] > 0.7) & (self.df['adaptive_ma_signal'] == 1), 1,
            np.where((self.df['momentum_score'] < 0.3) & (self.df['adaptive_ma_signal'] == -1), -1, 0)
        )
        
        # Volume signals
        volume_signal = np.where(
            (self.df['relative_volume'] > 1.5) & (self.df['force_index_ema'] > 0), 1,
            np.where((self.df['relative_volume'] > 1.5) & (self.df['force_index_ema'] < 0), -1, 0)
        )
        
        # Volatility signals
        volatility_signal = np.where(
            (self.df['vol_regime'] == 'low') & (self.df['real_implied_vol_ratio'] < 0.8), 1,
            np.where((self.df['vol_regime'] == 'high') & (self.df['real_implied_vol_ratio'] > 1.2), -1, 0)
        )
        
        # Market regime signals
        regime_signal = np.where(
            (self.df['market_efficiency'] > 0.7) & (self.df['trend_strength'] > 1.5), 1,
            np.where((self.df['market_efficiency'] < 0.3) & (self.df['trend_strength'] < 0.5), -1, 0)
        )
        
        # Combine signals with weights
        self.df['final_signal'] = (
            0.3 * momentum_signal +
            0.3 * volume_signal +
            0.2 * volatility_signal +
            0.2 * regime_signal
        )
        
        # Threshold for final decisions
        self.df['trading_signal'] = np.where(
            self.df['final_signal'] >= 0.5, 1,
            np.where(self.df['final_signal'] <= -0.5, -1, 0)
        )
        
        return self.df
