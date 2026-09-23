import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from scipy.interpolate import splrep, splev

import boto3
from io import StringIO
import logging
import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from Analytics.models import Uploads, Trade, UploadHoodWinked
from Analytics.Engine.DataProcessing import DataCleaning
from Analytics.utils.timestamp_converter import convert_to_datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

logger = logging.getLogger(__name__)

@csrf_exempt
def chartCalculation(request):
    if request.method == 'POST':

        try:
            data = json.loads(request.body)
            user_asset_class = data.get('user_asset_class')
            user_benchmark = data.get('user_benchmark')
            user_frequency = int(data.get('user_frequency'))
            user_time_period = data.get('user_time_period')
            user_order_size = int(data.get('user_order_size'))
            # user_asset_class = "Equities"  # for now only allow equities, gray out other options
            # user_benchmark = "TWAP"  # Can be TWAP or VWAP
            # user_frequency = 5  # float
            # user_time_period = "week"  # day, week, month, year
            # user_order_size = 10000

            # Python Script
            
            total_df = pd.read_csv('./file/aapl_data.csv')

            total_df

            aapl_avg = total_df['close'].mean()

            lstm_pred = pd.read_csv('./file/lstm_proj.csv')

            mean_lstm = lstm_pred.mean(axis=0)

            mean_lstm_real = mean_lstm[:8]
            mean_lstm_pred = mean_lstm[8:]

            sizes = [10,100,1000,10000,50000,100000,200000,500000]
            for i in range(8):
                lstm_pred[f'almgren_{sizes[i]}'] = total_df[f'almgren_{sizes[i]}']

            lstm_pred[29610:30000] # will use later for visualization

            def process_columns(df, X, twap=True):
                actual_col = f'almgren_{X}'
                pred_col = f'aapl_lstm_{X}'
                
                # Initialize lists to store results
                min_predicted_values = []
                corresponding_actual_values = []
                vwaps = []
                # Iterate over the dataframe in chunks of 390 rows
                for i in range(0, len(df), 390):
                    # Get the current chunk of 390 rows
                    chunk = df.iloc[i:i+390]
                    
                    smallest_values = chunk.nsmallest(10, pred_col)
                    locations = smallest_values.index.tolist()
                    for j in range(len(locations)):
                        min_predicted_values.append(chunk.loc[locations[j], pred_col])
                        corresponding_actual_values.append(chunk.loc[locations[j], actual_col])
                
                # Calculate averages
                avg_twap_actual = df[actual_col].mean()
                act = df[actual_col][390:]
                vol = total_df['volume'][:len(df)-390]
                avg_vwap_actual = np.dot(act, vol)/np.sum(vol)
                avg_corresponding_actual = np.mean(corresponding_actual_values)
                if twap==True:
                    return (avg_twap_actual - avg_corresponding_actual)
                else: 
                    return (avg_vwap_actual - avg_corresponding_actual)

            case_chunk = lstm_pred[29610:30000]
            smallest_values = case_chunk.nsmallest(10, 'aapl_lstm_100000')
            locations = (np.array(smallest_values.index) - 29610).tolist()
            corresponding_actual = case_chunk['almgren_100000']

            x_axis = [10,100,1000,10000,50000,100000,200000,500000]

            lstm_vs_twap = []
            lstm_vs_vwap = []
            for i in range(8):
                lstm_vs_twap.append(process_columns(lstm_pred, x_axis[i]))
                lstm_vs_vwap.append(process_columns(lstm_pred, x_axis[i], twap=False))

            lstm_twap_savings = [aapl_avg * lstm_vs_twap[i] * x_axis[i] for i in range(len(x_axis))]
            lstm_vwap_savings = [aapl_avg * lstm_vs_vwap[i] * x_axis[i] for i in range(len(x_axis))]

            log_x_axis = np.array(x_axis)
            # formatted_data = [{"x": x, "logX": log_x, "value": value} for x, log_x, value in zip(x_axis, log_x_axis, lstm_vs_twap)]
            formatted_data = [{"x": int(x), "logX": float(log_x), "value": float(value)} for x, log_x, value in zip(x_axis, log_x_axis, lstm_vs_twap)]
            # formatted_data = [{"x": int(x), "logX": log_x, "value": float(value)} for x, log_x, value in zip(x_axis, np.log10(x_axis), lstm_vs_twap)]

            # Example data points (non-equally spaced)
            x = x_axis
            y = lstm_twap_savings

            # Apply log transformation to x values
            log_x = np.log10(x)

            # Fit a polynomial of degree 3 to the log-transformed x values
            degree = 15
            coefficients = np.polyfit(log_x, y, degree)
            lstm_twap_polynomial = np.poly1d(coefficients)

            # Generate log-spaced points for the fitted curve
            log_x_fit = np.linspace(min(log_x), max(log_x), 100)
            x_fit = np.power(10, log_x_fit)
            y_fit = lstm_twap_polynomial(log_x_fit)


            # Example data points (non-equally spaced)
            x = x_axis
            y = lstm_vwap_savings

            # Apply log transformation to x values
            log_x = np.log10(x)

            # Fit a polynomial of degree 3 to the log-transformed x values
            degree = 15
            coefficients = np.polyfit(log_x, y, degree)
            lstm_vwap_polynomial = np.poly1d(coefficients)

            # Generate log-spaced points for the fitted curve
            log_x_fit = np.linspace(min(log_x), max(log_x), 100)
            x_fit = np.power(10, log_x_fit)
            y_fit = lstm_vwap_polynomial(log_x_fit)

  

            def lstm_twap_cost_savings_calc(weekly_shares_traded):
                return(lstm_twap_polynomial(np.log10(weekly_shares_traded)))
            def lstm_vwap_cost_savings_calc(weekly_shares_traded):
                return(lstm_vwap_polynomial(np.log10(weekly_shares_traded)))

            lstm_twap_cost_savings_calc(500000)

            lstm_vwap_cost_savings_calc(500000)

            trade_size = 10000
            trade_frequency = 12 # times per year
            print(f'If you trade {trade_size} shares a week, our model will save you ${lstm_twap_cost_savings_calc(trade_size):.2f} compared to TWAP every week.')
            print(f'If you trade {trade_size} shares a week, our model will save you ${lstm_vwap_cost_savings_calc(trade_size):.2f} compared to VWAP every week.')

            sp_returns = 0.227

            def calculate_cost_savings(user_benchmark, user_time_period, user_order_size, sp_returns, user_frequency):
                # Choose the appropriate calculation function based on the benchmark
                calc_func = lstm_twap_cost_savings_calc if user_benchmark == "TWAP" else lstm_vwap_cost_savings_calc
                
                # Determine the number of periods per year
                if user_time_period == "week":
                    time_multiplier = 52
                elif user_time_period == "day":
                    time_multiplier = 252  # Approximate number of trading days in a year
                elif user_time_period == "month":
                    time_multiplier = 12
                else:
                    time_multiplier = 1  # Default to annual if period is "year"

                # Calculate the total number of trades per year
                total_trades_per_year = user_frequency * time_multiplier
                
                # Get the cost savings per trade
                cost_savings_per_trade = calc_func(user_order_size)
                
                # Calculate the total annual cost savings
                total_cost_savings_dollars = cost_savings_per_trade * total_trades_per_year
                
                # Assume an average stock price (from your dataset)
                average_stock_price = aapl_avg  # You might want to ensure this value is accurate
                
                # Calculate the total value traded over the year
                total_value_traded = user_order_size * average_stock_price * total_trades_per_year
                
                # Compute the cost savings percentage
                cost_savings_percent = (total_cost_savings_dollars / total_value_traded) * 100
                
                # Calculate the excess returns relative to the benchmark (e.g., S&P 500)
                excess_returns = (cost_savings_percent / (sp_returns * 100)) * 100
                
                return total_cost_savings_dollars, cost_savings_percent, excess_returns

            if user_asset_class == "Equities":
                result = calculate_cost_savings(user_benchmark, user_time_period, user_order_size, sp_returns, user_frequency)
                print(result)
                return JsonResponse({'result': result, 'chartData': formatted_data})
                

        except Exception as e:
            logger.error(
                f"Error Getting Calculator Calculation: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)