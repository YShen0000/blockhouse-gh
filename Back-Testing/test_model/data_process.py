# This file is used to process data for Ritter's RL model
# Input: output.csv file contains minute-wise MBP-10 and OHLCV data and news_sentiment.csv
# Output: RL_Data_opt_timing_total.csv after deciding on time

import pandas as pd
import numpy as np
import statsmodels.api as sm
from IPython.core.display import HTML
import requests
import time
import datetime

class DataProcessor:
	''' init -> preprocess -> process
	'''
	def __init__(self, data_dir, news_sentiment_dir):
		self.data_dir = data_dir
		self.news_dir = news_sentiment_dir
		self.df = pd.read_csv(self.data_dir) # load data
		self.news = pd.read_csv(self.news_dir) # load news
		self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], utc=True) # time standard
		self.df = self.df.sort_values('timestamp').reset_index(drop=True) # time sort
		self.news = self.news.rename(columns={"time_published": "timestamp"})
		self.news['timestamp'] = pd.to_datetime(self.news['timestamp'], utc=True) # time standard
		self.news = self.news.sort_values('timestamp').reset_index(drop=True) # time sort
		self.news = self.news.drop_duplicates(subset='timestamp', keep='last') # drop duplicate sentiment and keep the informative one
	
	def preprocess(self):
		''' This function is used to preprocess raw data.
			Parameters:
				Null
			Returns:
				df: pd.DataFrame(OHLCV,ask_price_1,...bid_size_10)
		'''
		df = pd.DataFrame()
		# OHLCV
		df['timestamp'] = self.df['timestamp']
		df['open'] = self.df['open']
		df['high'] = self.df['high']
		df['low'] = self.df['low']
		df['close'] = self.df['close']
		df['volume'] = self.df['volume']
		df['volatility'] = self.df['Volatility']
		# L2 (MBO-10) Limit Order Book data
		for i in range(10):
			df["bid_price_"+str(i+1)] = self.df["bid_px_0"+str(i)]
			df["ask_price_"+str(i+1)] = self.df["ask_px_0"+str(i)]
			df["bid_size_"+str(i+1)] = self.df["bid_sz_0"+str(i)]
			df["ask_size_"+str(i+1)] = self.df["ask_sz_0"+str(i)]
		return df
	
	def process(self, df: pd.DataFrame):
		processed_df = self.generate_features(df)
		processed_df = self.optimal_timing_filter(processed_df)
		return processed_df
    
	def generate_features(self, df: pd.DataFrame):
		''' This function is used to generate features for Ritter's Model's state space.
			Parameters:
				df: pd.DataFrame(OHLCV,ask_price_1,...bid_size_10)
			Returns:
				df: pd.DataFrame(OHLCV,ask_price_1,...bid_size_10, liquidity, sentiment,...)
		'''
		# Effective Bid Ask Spread
		def EffectiveBidAskSpread(data, window_size=60):
			''' Spread is to measure liquidity, larger spread, less liquidity
			'''
			result = data[['timestamp','close']].copy()
			result['Delta_P_t'] = result['close'].diff()
			result['Delta_P_shift'] = result['Delta_P_t'].shift()
			
			result['EffectiveBidAskSpread'] = (
				result['Delta_P_t'].
						   rolling(window=window_size).cov(result['Delta_P_shift']).
						   apply(lambda x: max(0,(-x))**0.5)
			)
			data['EffectiveSpread'] = result['EffectiveBidAskSpread']
			
			return data
		# High Low Volatility
		def HLVolatility1(data, window_size=60):
			result = pd.DataFrame()
			result['timestamp'] = data['timestamp']
			
			result['HL_Volatility'] = (np.log(data['high'])-np.log(data['low']))**2
			result['HL_Volatility'] = result['HL_Volatility'].rolling(window=window_size).mean()
			result['HL_Volatility'] = (result['HL_Volatility']/(4*np.log(2)))**0.5
			df['HLVolatility'] = result['HL_Volatility']
			
			return df
		# Corwin-Schultz Spread
		def CSSpread(data, window_size=60):
			result = pd.DataFrame()
			result['timestamp'] = data['timestamp']
			result['gama'] = (np.log(np.maximum(data['high'], data['high'].shift(1))/np.minimum(data['high'], data['high'].shift(1))))**2
			
			result['beta'] = (np.log(data['high']/data['low']))**2
			result['beta'] = (result['beta']+result['beta'].shift(1)).rolling(window=window_size).mean()
			
			result['alpha'] = result['beta']**0.5 * (2**0.5-1) / (3-2*2**0.5) - (result['gama'] / (3-2*2**0.5))**0.5
			result['alpha'] = result['alpha'].apply(lambda x:max(x,0)) # avoid negative spread
			
			result['S'] = 2*(np.exp(result['alpha'])-1)/(np.exp(result['alpha'])+1)
			df['CS_Spread'] = result['S']
			
			return df
		
		# Kyle's Lambda -> 1/lambda implies liquidity
		def Kyle_Lambda(data):
			df = pd.DataFrame()
			df['date'] = data['timestamp'].dt.date
			df['delta_p_t'] = data['close'] - data['close'].shift(1)
			df['delta_price'] = data['close'] - data['close'].shift(1)
			df['b_t'] = np.sign(df['delta_price'])
			df['b_t'] = df['b_t'].replace(0, method='ffill') # method keyword is depricated 
			df['b_t'] = df['b_t'].fillna(1)
			df['signed_volume'] = df['b_t'] * data['volume']
			kyle_lambda_list = []
			grouped = df.dropna(subset=['delta_p_t', 'signed_volume']).groupby('date')
			for _, group in grouped:
				if len(group) > 1:
					X, y = group['signed_volume'], group['delta_p_t']
					X = sm.add_constant(X)
					model = sm.OLS(y, X)
					results = model.fit()
					lambda_hat = results.params['signed_volume']
					df.loc[group.index, 'Kyle_Lambda'] = lambda_hat
				else:
					df.loc[group.index, 'Kyle_Lambda'] = np.nan
			data['Kyle_Lambda'] = df['Kyle_Lambda']
			return data
		
		# Volume-Synchronized Probability of Informed Trading (VPIN) -> lead volatility
		def VolumePIN(data, window_size=60):
			df = pd.DataFrame()
			df['Total_Bid_Size'] = data[['bid_size_1', 'bid_size_2', 'bid_size_3', 'bid_size_4', 'bid_size_5']].sum(axis=1)
			df['Total_Ask_Size'] = data[['ask_size_1', 'ask_size_2', 'ask_size_3', 'ask_size_4', 'ask_size_5']].sum(axis=1)
			df['OBI'] = (df['Total_Bid_Size'] - df['Total_Ask_Size']) / (df['Total_Bid_Size'] + df['Total_Ask_Size'])
			df['OBI'] = df['OBI'].replace([np.inf, -np.inf], np.nan).fillna(0)
			df['V_B'] = data['volume'] * (1 + df['OBI']) / 2 # estimate V^B
			df['V_S'] = data['volume'] * (1 - df['OBI']) / 2 # estimate V^S
			df['sum_V_B'] = df['V_B'].rolling(window=window_size).sum()
			df['sum_V_S'] = df['V_S'].rolling(window=window_size).sum()
			df['V'] = data['volume'].rolling(window=window_size).mean()
			df['numerator'] = (df['V_B'] - df['V_S']).abs().rolling(window=window_size).sum()
			df['denominator'] = window_size * df['V']
			df['denominator'] = df['denominator'].replace(0, np.nan)
			data['Volume_PIN'] = df['numerator'] / df['denominator']
			return data
		# Fibonacci Retracement (maybe not so useful) -> support and resistance
		def Fibo_Retrace(data, window_size=390):
			period_high = data['high'].rolling(window=window_size, min_periods=1).max()
			period_low = data['low'].rolling(window=window_size, min_periods=1).min()
			for i,level in enumerate([0.236, 0.382, 0.5, 0.618, 0.786]):
				data[f'Fib_Level_{i}'] = period_high - (period_high - period_low) * level
			return data
		
		df = EffectiveBidAskSpread(df)
		df = HLVolatility1(df)
		df = CSSpread(df)
		df = Kyle_Lambda(df)
		df = VolumePIN(df)
		#df = Fibo_Retrace(df) # not needed
		df = pd.merge(df, self.news, on='timestamp', how='left')
		df['news_sentiment_score'] = df['news_sentiment_score'].fillna(0)
		
		return df
	
	def generate_features_pca(self, df: pd.DataFrame, proportion):
		''' This function is used to projection features into orthogonal basis.
			Parameters:
				df: pd.DataFrame
				proportion: proportion of variance explained
			Returns:
				df_pca: pd.DataFrame
		'''
		pass
	
	def optimal_timing_filter(self, df: pd.DataFrame, optm_pts_per_day = 380):
		''' This function is used to filter out high volatility trades.
			Parameters:
				df: pd.DataFrame with total features
				optm_pts_per_day: how many trades to keep for each day
			Returns:
				df_filtered: pd.DataFrame
		'''
		df['date'] = df['timestamp'].dt.date
		df = df.sort_values('timestamp').reset_index(drop=True) # date sort
		df = df.dropna()
		df_sorted = df.sort_values(['date', 'volatility'])
		df_filtered = df_sorted.groupby('date').head(optm_pts_per_day).reset_index(drop=True)
		daily_volume = df_filtered.groupby('date')['volume'].sum().reset_index()
		daily_volume.rename(columns={'volume': 'daily_volume'}, inplace=True)
		df_filtered = df_filtered.merge(daily_volume, on='date', how='left')
		df_filtered = df_filtered.sort_values('timestamp').reset_index(drop=True) # time sort
		return df_filtered
		
	
# testing part
if __name__ == '__main__':
	data_dir = '/Users/anshulrana/Desktop/blockhouse/blockhouseTrialPeriod/Blockhouse/Back-Testing/test_model/output.csv'
	news_sentiment_dir = '/Users/anshulrana/Desktop/blockhouse/blockhouseTrialPeriod/Blockhouse/Back-Testing/test_model/news_sentiment_to_merge.csv'
	test_instance = DataProcessor(data_dir,news_sentiment_dir)
	df = test_instance.preprocess()
	df = test_instance.process(df)
	df.to_csv('/Users/anshulrana/Desktop/blockhouse/blockhouseTrialPeriod/Blockhouse/Back-Testing/test_model/RL_Data_opt_timing_total_mbp10.csv',index=False)

	
