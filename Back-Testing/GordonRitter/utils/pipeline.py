from datetime import datetime, timedelta
import pytz
import os

import pandas as pd
import numpy as np

from GordonRitter.data_handler import TechnicalIndicators
from GordonRitter.utils.bet_sizing_model_utils import BetSizingModel
from GordonRitter.utils.bet_sizing_env import TradingEnvironment
from GordonRitter.utils.fetch_merge_data import PolygonClient
from GordonRitter.utils.micro_trader import MicroTrader as mt

class OptimalBetSizeInference():
    def __init__(self, data_dir='Data'):
        self.data_dir = data_dir
        self.data_client = PolygonClient(self.data_dir)
    
    def optimal_time_generation(self, df: pd.DataFrame, steps_forward=390):
        
        ti = TechnicalIndicators(df)
        ti.add_volatility()

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        df = df.sort_values('timestamp').reset_index(drop=True) # date sort
        #df['log_return'] = np.log(df['close'] / df['close'].shift(1))  # percentage->amplify for GARCH fitting
        df = df.dropna(subset=['log_return']).reset_index(drop=True)
        df = df[['timestamp','date','ask_price_1', 'ask_size_1','bid_price_1','bid_size_1',
                'ask_price_2', 'ask_size_2','bid_price_2','bid_size_2',
                'ask_price_3', 'ask_size_3','bid_price_3','bid_size_3',
                'ask_price_4', 'ask_size_4','bid_price_4','bid_size_4',
                'ask_price_5', 'ask_size_5','bid_price_5','bid_size_5',
                'open','high','low','close',
                'volume','volatility','log_return']]
        df.set_index('timestamp', inplace=True)
        df['time'] = df.index.time
        df['date'] = df.index.date
        last_date = df['date'].max()
        next_date = last_date + pd.Timedelta(days=1)
        while next_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            next_date += pd.Timedelta(days=1)

        start_time = pd.Timestamp(f"{next_date} 13:30:00")
        end_time = pd.Timestamp(f"{next_date} 19:59:00")

        df_forecast = pd.DataFrame({
            'timestamp': pd.date_range(start=start_time, periods=steps_forward, freq='1min'),
            'ask_price_1': np.zeros(steps_forward,dtype=float),
            'ask_size_1' : np.zeros(steps_forward,dtype=int),
            'bid_price_1' : np.zeros(steps_forward,dtype=float),
            'bid_size_1' : np.zeros(steps_forward,dtype=int),
            'open': np.zeros(steps_forward,dtype=float),
            'volume': np.zeros(steps_forward,dtype=int),
            'high': np.zeros(steps_forward,dtype=float),
            'low': np.zeros(steps_forward,dtype=float),
            'close': np.zeros(steps_forward,dtype=float),
            'volatility': np.zeros(steps_forward,dtype=float),
            'daily_volume' : np.zeros(steps_forward,dtype=float),
        })
        df_forecast.set_index('timestamp', inplace=True)
        df_forecast['time'] = df_forecast.index.time
        df_forecast['date'] = df_forecast.index.date

        def non_recurrent_hist_mean(train,test,col,window_size):
            train_dates = sorted(train['date'].unique())
            forecast=[]
            conf_lower=[]
            conf_upper=[]
            for idx, row in test.iterrows():
                time_to_forecast = row['time']
                date_to_forecast = row['date']
                past_dates = [date_to_forecast - timedelta(days=x) for x in range(1, window_size + 1)]
                past_dates = [d for d in past_dates if d.weekday() < 5 and d in train_dates] # exclude weekend
                past_data = train[(train['time'] == time_to_forecast) & (train['date'].isin(past_dates))][col]
                historical_mean = past_data.mean()
                if np.isnan(historical_mean):
                    historical_mean = train['bid'].iloc[-1] # last close price
                forecast.append(historical_mean)
            forecast=np.array(forecast)
            return forecast

        ask_price_1_forecast = non_recurrent_hist_mean(df, df_forecast, 'ask_price_1', 3)
        ask_size_1_forecast = non_recurrent_hist_mean(df, df_forecast, 'ask_size_1', 3).astype(int)

        df_forecast['ask_price_1'] = ask_price_1_forecast
        df_forecast['ask_size_1'] = ask_size_1_forecast
        df_forecast['bid_price_1'] = non_recurrent_hist_mean(df, df_forecast, 'bid_price_1', 3)
        df_forecast['bid_size_1'] = non_recurrent_hist_mean(df, df_forecast, 'bid_size_1', 3).astype(int)
        df_forecast['open'] = non_recurrent_hist_mean(df, df_forecast, 'open', 3)
        df_forecast['high'] = non_recurrent_hist_mean(df, df_forecast, 'high', 3)
        df_forecast['low'] = non_recurrent_hist_mean(df, df_forecast, 'low', 3)
        df_forecast['close'] = non_recurrent_hist_mean(df, df_forecast, 'close', 3)
        df_forecast['volume'] = non_recurrent_hist_mean(df, df_forecast, 'volume', 3).astype(int)
        df_forecast['volatility'] = non_recurrent_hist_mean(df, df_forecast, 'volatility', 3)
        df_forecast = df_forecast.reset_index()

        # we keep 5% for optimal timing
        optimal_timing=df_forecast.loc[df_forecast['volatility']<=np.percentile(df_forecast['volatility'].values, 5),:]
        
        optimal_timing=optimal_timing.copy()
        optimal_timing['daily_volume'] = optimal_timing['volume'].sum()
        optimal_timing = optimal_timing[['timestamp','ask_price_1', 'ask_size_1','bid_price_1','bid_size_1',
                                        'open', 'high', 'low', 'close', 'volume','daily_volume','volatility']]
        
        return optimal_timing

    def optimal_bet_sizing(self,
                           model_dir: str,
                           data: pd.DataFrame,
                           optm_pts_per_day = 20,
                           initial_invetory=10000):
        state_columns = ['bid_price_1', 'bid_size_1', 'open', 'volume','daily_volume', 'volatility']

        # Unifying the type of numerical columns 
        float_cols = data.select_dtypes(include=['float','int']).columns
        data[float_cols] = data[float_cols].astype(np.float32)

        #Handling missing values
        rows_with_nan = data.isna().any(axis=1)
        data.loc[rows_with_nan] = data.ffill().loc[rows_with_nan]

        # Min-Max normalization
        data_min = pd.read_csv(os.path.join(
            model_dir,
            'min_values_to_resize_features.csv'),
            index_col=0).squeeze(1)
        data_max = pd.read_csv(os.path.join(
            model_dir,
            'max_values_to_resize_features.csv'),
            index_col=0).squeeze(1)


        for col in float_cols:
            data[col] = (data[col] - data_min[col])/(data_max[col]-data_min[col])
                
        env = TradingEnvironment(
            data=data,
            reset_count=optm_pts_per_day,
            initial_inventory=initial_invetory,
            state_columns=state_columns
        )

        model = BetSizingModel(model_dir=model_dir, name='model', env=env)
        model.test(env=env)
        result = []
        for trade in env.tradelist:
            result.append(pd.DataFrame(trade, columns=['timestamp', 'volume']))
        return result
    
    def optimal_bet_sizing_with_order_type(
            self,
            model_dir: str,
            data: pd.DataFrame,
            optm_pts_per_day=20,
            initial_invetory=10000):
        tradeslist = self.optimal_bet_sizing(
            model_dir=model_dir,
            data=data,
            optm_pts_per_day=optm_pts_per_day,
            initial_invetory=initial_invetory)
        for trades in tradeslist:
            idxs = data.index[data['timestamp'].isin(trades['timestamp'])]
            new_cols = {
                'order_type': [],
                'price': []
            }
            for idx in idxs:
                order_type, price = mt.decide_order_type(
                    idx,
                    data,
                )
                new_cols['order_type'].append(order_type)
                new_cols['price'].append(price)

            trades['order_type'] = new_cols['order_type']
            trades['price'] = new_cols['price']

        return tradeslist


        


    def run_pipeline(self,
                     data,
                     ticker,
                     end_timestamp=datetime.now(pytz.UTC).strftime('%Y-%m-%d'),
                     timeframe=390,
                     inventory=10000,
                     bet_sz_model_dir='bet_sizing_v1'):
        
        start_timestamp = (datetime.strptime(end_timestamp, '%Y-%m-%d') - timedelta(days=2)).strftime('%Y-%m-%d')
        end_timestamp = end_timestamp

        # Commented out for testing the Backtest Framework for the RL Model 5
        # data = self.data_client.fetch_and_merge_data(
        #     ticker,
        #     start_date=start_timestamp,
        #     end_date=end_timestamp)
        
        print("data",data)
        optimal_timings = self.optimal_time_generation(data, steps_forward=timeframe)
        optimal_bet_sizes = self.optimal_bet_sizing(data=optimal_timings,
                                                    model_dir=bet_sz_model_dir,
                                                    initial_invetory=inventory,
                                                    optm_pts_per_day=20)
        return optimal_bet_sizes

    def run_pipeline_with_order_types(self,
                     ticker,
                     end_timestamp=datetime.now(pytz.UTC).strftime('%Y-%m-%d'),
                     timeframe=390,
                     inventory=10000,
                     bet_sz_model_dir='bet_sizing_v1'):
        
        start_timestamp = (datetime.strptime(end_timestamp, '%Y-%m-%d') - timedelta(days=2)).strftime('%Y-%m-%d')
        end_timestamp = end_timestamp
        data = self.data_client.fetch_and_merge_data(
            ticker,
            start_date=start_timestamp,
            end_date=end_timestamp)

        optimal_timings = self.optimal_time_generation(data, steps_forward=timeframe)
        optimal_bet_sizes = self.optimal_bet_sizing_with_order_type(
            data=optimal_timings,
            model_dir=bet_sz_model_dir,
            initial_invetory=inventory,
            optm_pts_per_day=20)
        return optimal_bet_sizes


    