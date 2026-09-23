from Analytics.Engine.DataProcessing import DataCleaning
from Analytics.utils.timestamp_converter import convert_to_datetime
import boto3
import csv
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import F, Sum, Max, Avg
from django.db.models.functions import TruncDay
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from io import StringIO
import json
import logging
import numpy as np
from openai import OpenAI
import pandas as pd
import pytz
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
import requests
from .models import Market_Prices, Trade, Uploads, User

from Analytics.utils.fetch_data import fetch_trade_data, fetch_market_data

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)


# @csrf_exempt
# def signup(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         email = request.POST.get('email')
#         password = request.POST.get('password')

#         # Basic validations
#         if not username or not email or not password:
#             return JsonResponse({'error': 'Missing fields'}, status=400)

#         if User.objects.filter(username=username).exists():
#             return JsonResponse({'error': 'Username already exists'}, status=400)

#         if User.objects.filter(email=email).exists():
#             return JsonResponse({'error': 'Email already exists'}, status=400)

#         user = User.objects.create_user(
#             username=username,
#             email=email,
#             password=password
#         )

#         return JsonResponse({'message': 'User created successfully'}, status=201)
#     else:
#         return JsonResponse({'error': 'Invalid request method'}, status=405)


# @csrf_exempt
# def signin(request):
#     if request.method == 'POST':
#         email = request.POST.get('email')
#         password = request.POST.get('password')

#         # Basic validation
#         if not email or not password:
#             return JsonResponse({'error': 'Missing email or password'}, status=400)

#         try:
#             user = User.objects.get(email=email)
#         except User.DoesNotExist:
#             return JsonResponse({'error': 'Invalid credentials'}, status=401)

#         user = authenticate(username=user.username, password=password)

#         if user is not None:
#             # Create token
#             refresh = RefreshToken.for_user(user)
#             return JsonResponse({
#                 'refresh': str(refresh),
#                 'access': str(refresh.access_token),
#             })
#         else:
#             return JsonResponse({'error': 'Invalid credentials'}, status=401)
#     else:
#         return JsonResponse({'error': 'Invalid request method'}, status=405)


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def upload_file(request):
#     if request.method != 'POST':
#         return JsonResponse({'error': 'Invalid request'}, status=400)

#     files = request.FILES.getlist('files')  # Get multiple files

#     if not files:
#         return JsonResponse({'error': 'No files provided'}, status=400)

#     s3 = boto3.client('s3',
#                       aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#                       aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#                       region_name=settings.AWS_REGION)

#     responses = []

#     for file in files:
#         try:
#             user_folder = str(request.user.id)  # or use request.user.username
#             s3_file_path = f"{user_folder}/{file.name}"

#             s3.upload_fileobj(file, settings.AWS_STORAGE_BUCKET, s3_file_path)

#             obj = s3.get_object(
#                 Bucket=settings.AWS_STORAGE_BUCKET, Key=s3_file_path)
#             file_content = obj['Body'].read().decode('utf-8')

#             df = pd.read_csv(StringIO(file_content))

#             df = DataCleaning.clean_data(df)

#             upload_record = Uploads.objects.create(
#                 user=request.user,
#                 file_name=file.name,
#                 file_size=file.size,
#                 file_path=f"https://analyticsv1.s3.amazonaws.com/{s3_file_path}"
#             )

#             trades_list = [
#                 Trade(
#                     file=upload_record,
#                     cusip=row['CUSIP'],
#                     trade_timestamp=convert_to_datetime(
#                         row['Trade Date'], row['Trade Time']),
#                     trade_size=int(row['Trade Size']),
#                     face_value=int(row['Face Value']),
#                     asset_inventory=int(row['Asset Inventory']),
#                     fill=row['Fill'],
#                     execution_time=int(row['Execution Time']),
#                     trade_price=float(row['Trade Price']),
#                     trade_direction=row['Trade Direction'].upper(),
#                     counterparty=row['Counterparty'],
#                     trader=row['Trader']
#                 ) for index, row in df.iterrows()
#             ]

#             Trade.objects.bulk_create(trades_list)

#             responses.append(
#                 {'message': f'File {file.name} uploaded successfully'})
#         except Exception as e:
#             logger.error(
#                 f"Error uploading file {file.name} to S3: {str(e)}", exc_info=True)
#             responses.append({'error': str(e), 'file': file.name})

#     return JsonResponse({'responses': responses})


# @csrf_exempt
# def delete_file(request):
#     if request.method == 'POST':

#         try:
#             data = json.loads(request.body)
#             file_id = data.get('file_id')

#             if not file_id:
#                 return JsonResponse({'error': 'No file ID provided'}, status=400)

#             upload = Uploads.objects.get(id=file_id)

#             Trade.objects.filter(file=upload).delete()

#             s3 = boto3.client('s3',
#                               aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#                               aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#                               region_name=settings.AWS_REGION)

#             s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET,
#                              Key=upload.file_name)

#             upload.delete()

#             return JsonResponse({'message': 'File deleted successfully'})

#         except Exception as e:
#             logger.error(
#                 f"Error deleting file from S3: {str(e)}", exc_info=True)
#             return JsonResponse({'error': str(e)}, status=500)
#     else:
#         return JsonResponse({'error': 'Invalid request method'}, status=405)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def files_list(request):
#     try:
#         user = request.user

#         uploads = Uploads.objects.filter(user=user).values()
#         return JsonResponse({'uploads': list(uploads)})

#     except Exception as e:
#         logger.error(f"Error fetching files: {str(e)}", exc_info=True)
#         return JsonResponse({'error': str(e)}, status=500)


# @csrf_exempt
# @permission_classes([IsAuthenticated])
# def heatmap(request):
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON'}, status=400)

#     # Fetching data from the request body
#     file_id = data.get('fileId')
#     if not file_id:
#         return JsonResponse({'error': 'No file ID provided'}, status=400)

#     time_filter, cusip_from_body = data.get(
#         "timeFilter", "last_1_day"), data.get("cusip")

#     trades_data = fetch_trade_data(time_filter, file_id)
#     market_data = fetch_market_data(time_filter, file_id)

#     df_trades = pd.DataFrame(list(trades_data))
#     df_market = pd.DataFrame(list(market_data))

#     unique_cusips = df_trades['cusip'].unique().tolist()
#     unique_traders = df_trades['trader'].unique().tolist()
#     time_intervals = [1, 30, 60, 90]  # Default intervals, adjust as needed

#     num_traders = len(unique_traders)
#     num_intervals = len(time_intervals)
#     markout_data = np.zeros((num_traders, num_intervals))

#     selected_cusip = cusip_from_body if cusip_from_body else unique_cusips[0]
#     selected_cusip_df = df_trades[df_trades['cusip'] == selected_cusip]
#     df_market = df_market[df_market['cusip'] == selected_cusip]

#     for i, trader in enumerate(unique_traders):
#         trader_df = selected_cusip_df[selected_cusip_df['trader'] == trader]
#         for j, interval in enumerate(time_intervals):
#             markouts = []
#             for index, trade in trader_df.iterrows():
#                 trade_time = pd.to_datetime(trade['trade_timestamp'])
#                 reference_time = trade_time + timedelta(minutes=interval)
#                 reference_price = df_market[(
#                     df_market['trade_timestamp'] >= reference_time)].iloc[0]['trade_price']

#                 if reference_price:
#                     trade_price = trade['trade_price']
#                     markout = trade_price - \
#                         reference_price if trade['trade_direction'] == 'BUY' else reference_price - trade_price
#                     markouts.append(markout)
#                 else:
#                     markouts.append(0)

#             if markouts:
#                 markout_data[i][j] = np.mean(markouts)
#             else:
#                 markout_data[i][j] = 0

#     return JsonResponse({
#         'cusip': selected_cusip,
#         'markouts': markout_data.tolist(),
#         'traders': unique_traders,
#         'intervals': time_intervals,
#         'unique_cusips': unique_cusips,
#     })


# @csrf_exempt
# @permission_classes([IsAuthenticated])
# def piechart(request):
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON'}, status=400)

#     file_id = data.get('fileId')
#     if not file_id:
#         return JsonResponse({'error': 'No file ID provided'}, status=400)

#     # Use the default 'last_1_day' if no time_filter is provided
#     time_filter = data.get("timeFilter", "last_1_day")

#     # Fetching data for the specified file
#     trades_data = Trade.objects.filter(file_id=file_id).values()
#     df_trades = pd.DataFrame(trades_data)

#     # Convert trade_timestamp to datetime for easier manipulation
#     df_trades['trade_timestamp'] = pd.to_datetime(df_trades['trade_timestamp'])

#     # Find the last date in the trades data
#     last_date = df_trades['trade_timestamp'].max()

#     # Time filters relative to the last date
#     time_filters = {
#         'last_1_day': last_date - timedelta(days=1),
#         'last_7_days': last_date - timedelta(days=7),
#         'last_30_days': last_date - timedelta(days=30),
#         'last_90_days': last_date - timedelta(days=90),
#         'last_365_days': last_date - timedelta(days=365),
#     }

#     # Filter the dataframe based on the selected time filter
#     # Default to last_1_day if not found
#     start_date = time_filters.get(time_filter, last_date - timedelta(days=1))
#     df_trades = df_trades[df_trades['trade_timestamp'] >= start_date]

#     # Calculate aggregate completed and non-completed notional values
#     agg_comp = 0
#     agg_noncomp = 0
#     for _, row in df_trades.iterrows():
#         notional_value = row['face_value'] * row['trade_size']
#         if row['fill'] == 1.0:
#             agg_comp += notional_value
#         else:
#             agg_noncomp += notional_value

#     total_notional = agg_comp + agg_noncomp

#     # Initialize trader and counterparty dictionaries
#     unique_traders = df_trades['trader'].unique()
#     unique_counterparties = df_trades['counterparty'].unique()

#     comp_volume_by_trader = dict.fromkeys(unique_traders, 0)
#     noncomp_volume_by_trader = dict.fromkeys(unique_traders, 0)
#     comp_volume_by_counterparty = dict.fromkeys(unique_counterparties, 0)
#     noncomp_volume_by_counterparty = dict.fromkeys(unique_counterparties, 0)

#     # Calculate volumes
#     for _, row in df_trades.iterrows():
#         trader = row['trader']
#         counterparty = row['counterparty']
#         volume = row['face_value'] * row['trade_size']

#         if row['fill'] == 1.0:
#             comp_volume_by_trader[trader] += volume
#             comp_volume_by_counterparty[counterparty] += volume
#         elif row['fill'] == -1:
#             noncomp_volume_by_trader[trader] += volume
#             noncomp_volume_by_counterparty[counterparty] += volume

#     # Convert volumes to percentages
#     total_comp_volume = sum(comp_volume_by_trader.values())
#     total_noncomp_volume = sum(noncomp_volume_by_trader.values())

#     comp_volume_by_trader = {trader: (volume / total_comp_volume * 100)
#                              for trader, volume in comp_volume_by_trader.items()}
#     noncomp_volume_by_trader = {trader: (volume / total_noncomp_volume * 100)
#                                 for trader, volume in noncomp_volume_by_trader.items()}

#     comp_volume_by_counterparty = {counterparty: (
#         volume / total_comp_volume * 100) for counterparty, volume in comp_volume_by_counterparty.items()}
#     noncomp_volume_by_counterparty = {counterparty: (
#         volume / total_noncomp_volume * 100) for counterparty, volume in noncomp_volume_by_counterparty.items()}

#     return JsonResponse({
#         'agg_comp': agg_comp,
#         'agg_noncomp': agg_noncomp,
#         'total_notional': total_notional,
#         'comp_volume_by_trader_percentage': comp_volume_by_trader,
#         'noncomp_volume_by_trader_percentage': noncomp_volume_by_trader,
#         'comp_volume_by_counterparty_percentage': comp_volume_by_counterparty,
#         'noncomp_volume_by_counterparty_percentage': noncomp_volume_by_counterparty
#     })


# @csrf_exempt
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def bargraph(request):
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON'}, status=400)

#     file_id = data.get('fileId')
#     if not file_id:
#         return JsonResponse({'error': 'No file ID provided'}, status=400)

#     cusip_from_body = data.get("cusip")
#     time_filter = data.get("timeFilter", "last_1_day")

#     # Fetching data for the specified file and timeframe
#     trades_data = fetch_trade_data(time_filter, file_id)
#     market_data = fetch_market_data(time_filter, file_id)

#     df_trades = pd.DataFrame(trades_data)
#     df_market = pd.DataFrame(market_data)

#     # Convert trade_timestamp to datetime for easier manipulation
#     df_trades['trade_timestamp'] = pd.to_datetime(df_trades['trade_timestamp'])
#     df_market['trade_timestamp'] = pd.to_datetime(df_market['trade_timestamp'])

#     # Determine the last trade timestamp across both trades and market data
#     last_date = df_trades['trade_timestamp'].max()

#     # Time filters relative to the last trade date
#     time_filters = {
#         'last_1_day': last_date - timedelta(days=1),
#         'last_7_days': last_date - timedelta(days=7),
#         'last_30_days': last_date - timedelta(days=30),
#         'last_90_days': last_date - timedelta(days=90),
#         'last_365_days': last_date - timedelta(days=365),
#     }

#     # Filter the dataframes based on the selected time filter
#     # Default to last_1_day if not found
#     start_date = time_filters.get(time_filter, last_date - timedelta(days=1))
#     df_trades = df_trades[df_trades['trade_timestamp'] >= start_date]
#     df_market = df_market[df_market['trade_timestamp'] >= start_date]

#     unique_cusips = df_trades['cusip'].unique().tolist()
#     cusip = cusip_from_body if cusip_from_body in unique_cusips else unique_cusips[
#         0] if unique_cusips else None

#     if cusip is None:
#         return JsonResponse({'error': 'No data found for the provided CUSIP or no CUSIPs available.'}, status=404)

#     trades_df = df_trades[df_trades['cusip'] == cusip].copy()
#     market_df = df_market[df_market['cusip'] == cusip].copy()

#     trades_df.loc[:, 'Expected TCA'] = 0.0
#     trades_df.loc[:, 'Trade Impact'] = 0.0
#     trades_df.loc[:, 'Net Trade Impact'] = 0.0

#     for index, trade in trades_df.iterrows():
#         trade_time = trade['trade_timestamp']
#         trade_price = trade['trade_price']
#         trade_volume = trade['trade_size']

#         # Find corresponding market prices
#         price_at_trade_records = market_df[market_df['trade_timestamp'] <= trade_time].nlargest(
#             1, 'trade_timestamp')
#         price_after_trade_records = market_df[market_df['trade_timestamp']
#                                               > trade_time].nsmallest(1, 'trade_timestamp')

#         if not price_at_trade_records.empty and not price_after_trade_records.empty:
#             price_at_trade = price_at_trade_records['trade_price'].iloc[0]
#             price_after_trade = price_after_trade_records['trade_price'].iloc[0]

#             if trade['trade_direction'] == 'BUY':
#                 trades_df.at[index, 'Expected TCA'] = float(
#                     trade_volume * (price_at_trade - trade_price))
#                 trades_df.at[index, 'Trade Impact'] = float(
#                     trade_volume * (price_after_trade - price_at_trade))
#             elif trade['trade_direction'] == 'SELL':
#                 trades_df.at[index, 'Expected TCA'] = float(
#                     trade_volume * (trade_price - price_at_trade))
#                 trades_df.at[index, 'Trade Impact'] = float(
#                     trade_volume * (price_at_trade - price_after_trade))

#             trades_df.at[index, 'Net Trade Impact'] = trades_df.at[index,
#                                                                    'Expected TCA'] + trades_df.at[index, 'Trade Impact']

#     aggregated_result = trades_df.agg(
#         {'Expected TCA': 'sum', 'Trade Impact': 'sum', 'Net Trade Impact': 'sum'}).to_dict()

#     return JsonResponse({'aggregated_result': aggregated_result, 'unique_cusips': unique_cusips})


# @csrf_exempt
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def executions_over_time(request):
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON'}, status=400)

#     file_id = data.get('fileId')
#     if not file_id:
#         return JsonResponse({'error': 'No file ID provided'}, status=400)

#     cusip_from_body = data.get("cusip")
#     time_filter = data.get("timeFilter", "last_1_day")

#     # Fetching data for the specified file
#     trades_data = fetch_trade_data(time_filter, file_id)
#     market_data = fetch_market_data(time_filter, file_id)

#     df_trades = pd.DataFrame(trades_data)
#     df_market = pd.DataFrame(market_data)

#     # Convert trade_timestamp to datetime for easier manipulation
#     df_trades['trade_timestamp'] = pd.to_datetime(df_trades['trade_timestamp'])
#     df_market['trade_timestamp'] = pd.to_datetime(df_market['trade_timestamp'])

#     # Determine the last trade timestamp across both trades and market data
#     last_trade = df_trades['trade_timestamp'].max()

#     # Calculate the start of the last trade date for 'last_1_day' filter
#     start_of_last_trade_date = last_trade.normalize()

#     # Time filters relative to the last trade date
#     time_filters = {
#         'last_1_day': start_of_last_trade_date,
#         'last_7_days': last_trade - timedelta(days=7),
#         'last_30_days': last_trade - timedelta(days=30),
#         'last_90_days': last_trade - timedelta(days=90),
#         'last_365_days': last_trade - timedelta(days=365),
#     }

#     # Filter the dataframes based on the selected time filter
#     start_date = time_filters.get(time_filter, last_trade - timedelta(days=1))
#     df_trades = df_trades[df_trades['trade_timestamp'] >= start_date]
#     df_market = df_market[df_market['trade_timestamp'] >= start_date]

#     unique_cusips = df_trades['cusip'].unique().tolist()
#     cusip = cusip_from_body if cusip_from_body in unique_cusips else unique_cusips[
#         0] if unique_cusips else None

#     if cusip is None:
#         return JsonResponse({'error': 'No data found for the provided CUSIP or no CUSIPs available.'}, status=404)

#     trades_df = df_trades[df_trades['cusip'] == cusip].copy()
#     market_df = df_market[df_market['cusip'] == cusip].copy()

#     markout_period = 5

#     trades_df['markout'] = 0.0
#     trades_df['pnl'] = 0.0

#     for trade in trades_df.itertuples():
#         trade_time = trade.trade_timestamp
#         reference_time = trade_time + timedelta(minutes=markout_period)

#         filtered_market_prices = market_df[market_df['trade_timestamp']
#                                            >= reference_time]

#         if not filtered_market_prices.empty:
#             closest_market_price = filtered_market_prices.iloc[0]
#             reference_price = closest_market_price['trade_price']
#         else:
#             reference_price = trade.trade_price

#         markout = float(trade.trade_price - reference_price if trade.trade_direction ==
#                         'BUY' else reference_price - trade.trade_price)
#         pnl = markout * trade.trade_size

#         trades_df.at[trade.Index, 'markout'] = float(markout)
#         trades_df.at[trade.Index, 'pnl'] = float(pnl)

#     if time_filter == 'last_1_day':
#         # Ensure that data is within the same calendar date for 'last_1_day' filter
#         trades_df = trades_df[trades_df['trade_timestamp']
#                               >= start_of_last_trade_date]
#         grouped = trades_df.groupby([pd.Grouper(
#             key='trade_timestamp', freq='15min'), 'trader']).agg({'pnl': 'sum'}).reset_index()
#     else:
#         grouped = trades_df.groupby([pd.Grouper(
#             key='trade_timestamp', freq='D'), 'trader']).agg({'pnl': 'sum'}).reset_index()

#     response_data = {}
#     for trader in grouped['trader'].unique():
#         trader_data = grouped[grouped['trader'] == trader]
#         response_data[trader] = trader_data[[
#             'trade_timestamp', 'pnl']].values.tolist()

#     overall_pnl = grouped.groupby(['trade_timestamp']).agg(
#         {'pnl': 'sum'}).reset_index()
#     response_data['Overall'] = overall_pnl[[
#         'trade_timestamp', 'pnl']].values.tolist()

#     return JsonResponse({"data": response_data, "unique_cusips": list(unique_cusips)}, safe=False)


# @csrf_exempt
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def traded_quantities(request):
#     '''
#     A view to calculate the total traded quantities for a given file ID and time filter

#     Args:
#         request: The request object

#         request.body: The request body containing the file ID and time filter
#             fileId: string, required
#             timeFilter: string, optional (default: last_30_days)
#             category: string, required (asset_class, maturity, trade_size)

#     Returns:
#         JsonResponse: A JSON response containing the total traded quantities
#     '''
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON'}, status=400)

#     file_id = data.get('fileId')
#     category = data.get('category')
#     time_filter = data.get("timeFilter", "last_30_day")

#     trades_data = Trade.objects.filter(file_id=file_id).values()

#     if not trades_data:
#         return JsonResponse({'error': 'No data found for the provided file ID'}, status=404)

#     df_trades = pd.DataFrame(trades_data)
#     df_trades['trade_timestamp'] = pd.to_datetime(df_trades['trade_timestamp'])

#     last_trade = df_trades['trade_timestamp'].max()

#     time_filters = {
#         'last_1_day': last_trade - timedelta(days=1),
#         'last_7_days': last_trade - timedelta(days=7),
#         'last_30_days': last_trade - timedelta(days=30),
#         'last_90_days': last_trade - timedelta(days=90),
#         'last_365_days': last_trade - timedelta(days=365),
#     }

#     start_date = time_filters.get(
#         time_filter, last_trade - timedelta(days=30))
#     df_trades = df_trades[df_trades['trade_timestamp'] >= start_date]

#     unique_cusips = df_trades['cusip'].unique()

#     if category == 'asset_class':
#         notional_values = []
#         for cusip in unique_cusips:
#             cusip_trades = df_trades[df_trades['cusip'] == cusip]
#             notional_value = cusip_trades['face_value'] * \
#                 cusip_trades['trade_size']
#             notional_values.append(notional_value.sum())

#         cusip_notional_list = list(zip(unique_cusips, notional_values))
#         cusip_notional_list_json_ready = [
#             (cusip, int(notional_value)) for cusip, notional_value in cusip_notional_list]

#         return JsonResponse({'values': cusip_notional_list_json_ready})

#     elif category == "maturity":
#         # This is manual, in the future we can add a maturity column to the Trades model
#         cusip_mappings = {
#             '912810SZ41': '30 Year',
#             '037833CS7': '10 Year',
#             '16119PAS03': '8 Year'
#         }

#         notional_values = []
#         for cusip in unique_cusips:
#             if cusip in cusip_mappings:
#                 cusip_trades = df_trades[df_trades['cusip'] == cusip]

#                 notional_value = cusip_trades['face_value'] * \
#                     cusip_trades['trade_size']
#                 notional_values.append(int(notional_value.sum()))
#         maturity_face_values = list(
#             zip(cusip_mappings.values(), notional_values))
#         return JsonResponse({'values': maturity_face_values})

#     elif category == "trade_size":
#         trade_sizes = df_trades['trade_size']
#         notional_values = df_trades['face_value'] * trade_sizes

#         notional_values = {
#             '<1M': 0,
#             '1-5M': 0,
#             '5-10M': 0,
#             '>10M': 0
#         }

#         for index, trade in df_trades.iterrows():
#             notional_value = trade['face_value'] * trade['trade_size']
#             if trade['trade_size'] < 1_000_000:
#                 notional_values['<1M'] += notional_value
#             elif 1_000_000 <= trade['trade_size'] < 5_000_000:
#                 notional_values['1-5M'] += notional_value
#             elif 5_000_000 <= trade['trade_size'] < 10_000_000:
#                 notional_values['5-10M'] += notional_value
#             else:
#                 notional_values['>10M'] += notional_value

#         notional_values_list = list([key, value]
#                                     for key, value in notional_values.items())

#         return JsonResponse({'values': notional_values_list})
#     else:
#         return JsonResponse({'error': 'Invalid category provided'}, status=400)


# def calculate_benchmarks(market_data, trades_data, benchmark):
#     benchmarks = {}
#     if benchmark == 'LAST_PRICE':
#         last_price = market_data.sort_values('trade_timestamp', ascending=False).iloc[0]
#         benchmarks['Last Price'] = float(last_price['trade_price']) if not market_data.empty else None
#         benchmarks['Bid'] = float(last_price['bid']) if not market_data.empty else None
#         benchmarks['Ask'] = float(last_price['ask']) if not market_data.empty else None
#     elif benchmark == 'TWAP':
#         twap = trades_data['trade_price'].astype(float).mean()
#         bid_twap = market_data['bid'].astype(float).mean()
#         ask_twap = market_data['ask'].astype(float).mean()
#         benchmarks['TWAP'] = twap
#         benchmarks['Bid'] = bid_twap
#         benchmarks['Ask'] = ask_twap
#     elif benchmark == 'VWAP':
#         trades_data['trade_price'] = trades_data['trade_price'].apply(float)
#         trades_data['volume'] = trades_data['volume'].apply(float)
#         market_data['bid'] = market_data['bid'].apply(float)
#         market_data['ask'] = market_data['ask'].apply(float)
        
#         vwap = (trades_data['trade_price'] * trades_data['volume']).sum() / trades_data['volume'].sum()
#         bid_vwap = (market_data['bid'] * trades_data['volume']).sum() / trades_data['volume'].sum()
#         ask_vwap = (market_data['ask'] * trades_data['volume']).sum() / trades_data['volume'].sum()
        
#         benchmarks['VWAP'] = vwap
#         benchmarks['Bid'] = bid_vwap
#         benchmarks['Ask'] = ask_vwap
#     return benchmarks

# def calculate_notional_values(trades_data):
#     trades_data['trade_price'] = trades_data['trade_price'].astype(float)
#     trades_data['trade_size'] = trades_data['trade_size'].astype(float)
    
#     buy_trades = trades_data[(trades_data['trade_direction'] == 'BUY')]
#     sell_trades = trades_data[(trades_data['trade_direction'] == 'SELL')]

#     # Calculate notional values
#     buy_trades['notional_value'] = buy_trades['trade_price'] * buy_trades['trade_size']
#     sell_trades['notional_value'] = sell_trades['trade_price'] * sell_trades['trade_size']

#     # Convert to list of [trade_price, notional_value] for each trade
#     buy_trades_list = buy_trades[['trade_price', 'notional_value']].values.tolist()
#     sell_trades_list = sell_trades[['trade_price', 'notional_value']].values.tolist()

#     # Ensure the notional values are numbers
#     buy_trades_list = [[float(trade[0]), float(trade[1])] for trade in buy_trades_list]
#     sell_trades_list = [[float(trade[0]), float(trade[1])] for trade in sell_trades_list]

#     return buy_trades_list, sell_trades_list

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def bid_ask_chart(request):
#     valid_time_filters = ['last_1_day', 'last_2_days',
#                           'last_3_days', 'last_4_days', 'last_5_days']
#     valid_benchmarks = ['LAST_PRICE', 'TWAP', 'VWAP']

#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON'}, status=400)

#     file_id = data.get('fileId')
#     # cusip = data.get('cusip')
#     time_filter = data.get("timeFilter", "last_1_day")
#     benchmark = data.get("benchmark", "Last Price")

#     if not file_id:
#         return JsonResponse({'error': 'No file ID provided'}, status=400)

#     if time_filter not in valid_time_filters:
#         return JsonResponse({'error': 'Invalid time filter provided'}, status=400)

#     if benchmark not in valid_benchmarks:
#         return JsonResponse({'error': 'Invalid benchmark provided'}, status=400)

#     # Fetching data for the specified file
#     trades_data = fetch_trade_data(time_filter, file_id)
#     market_data = fetch_market_data(time_filter, file_id)

#     trades_data = pd.DataFrame(trades_data)
#     market_data = pd.DataFrame(market_data)

#     # Calculating Bid-Ask spread
#     spread = 0.03 # Assuming default spread of 0.03
#     market_data['bid'] = market_data['trade_price'] - spread / 2
#     market_data['ask'] = market_data['trade_price'] + spread / 2

#     # Calculate Volume 
#     last_date = trades_data['trade_timestamp'].max()

#     # Get the last trade price, multiply it by 30x, you get the total volume, now in the dataframe create a new column volume and linearly interpolate the volume for each trade
#     last_trade_price = trades_data[trades_data['trade_timestamp']
#                                    == last_date]['trade_price'].values[0]
#     total_volume = int(last_trade_price * 30)
#     trades_data['volume'] = np.linspace(1, total_volume, len(trades_data))

#     # Calculate benchmarks
#     benchmarks = calculate_benchmarks(market_data, trades_data, benchmark)

#     # Aggregate trade data by day for buy and sell transactions
#     notional_values_buy, notional_values_sell = calculate_notional_values(trades_data)

#     # Generate response data
#     response_data = {
#         'bid_ask_chart': {
#             'benchmarks': benchmarks,
#             'notional_values_buy': list(notional_values_buy),
#             'notional_values_sell': list(notional_values_sell),
#         }
#     }

#     return JsonResponse(response_data, safe=False)


# @csrf_exempt
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def chat(request):  # contains experimental data, will clean up once we finalise the chatbot approach
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON'}, status=400)

#     try:
#         file_id = data.get('fileId')

#         if not file_id:
#             return JsonResponse({'error': 'No file ID provided'}, status=400)

#         # # Fetching data for the specified file
#         # file_link = Uploads.objects.get(id=file_id).file_path

#         # # Download the file from S3
#         # response = requests.get(file_link)
#         # content = response.content.decode('utf-8')
#         # csv_reader = csv.DictReader(content.splitlines())

#         # # Convert each row into a JSON string (or you could format it as plain text)
#         # lines = [json.dumps(row) for row in csv_reader]

#         # # Join the lines into a single string to prepare for upload
#         # file_content = "\n".join(lines).encode('utf-8')

#         # # Upload the file to OpenAI
#         # file = client.files.create(file=file_content, purpose="assistants")

#         # class CustomJSONEncoder(DjangoJSONEncoder):
#         #     def default(self, obj):
#         #         if isinstance(obj, datetime):
#         #             return obj.isoformat()
#         #         return super().default(obj)

#         trades = Trade.objects.filter(file_id=file_id).values()
#         trades_csv_io = StringIO()
#         # Assuming non-empty queryset; adjust as needed
#         fieldnames = trades[0].keys()
#         writer = csv.DictWriter(trades_csv_io, fieldnames=fieldnames)
#         writer.writeheader()
#         for trade in trades:
#             writer.writerow(trade)
#         trades_csv_content = trades_csv_io.getvalue().encode('utf-8')

#         # Example for converting Market_Prices model data to CSV
#         market_prices = Market_Prices.objects.all().values()
#         market_prices_csv_io = StringIO()
#         fieldnames = market_prices[0].keys()  # Adjust as needed
#         writer = csv.DictWriter(market_prices_csv_io, fieldnames=fieldnames)
#         writer.writeheader()
#         for price in market_prices:
#             writer.writerow(price)
#         market_prices_csv_content = market_prices_csv_io.getvalue().encode('utf-8')

#         # Upload the CSV data to OpenAI
#         trade_prices_file = client.files.create(
#             file=trades_csv_content, purpose="assistants")
#         market_prices_file = client.files.create(
#             file=market_prices_csv_content, purpose="assistants")

#         # Creating an assistant
#         instructions = f"You have access to trades_dataset file_id: {trade_prices_file.id} and market_prices dataset file_id: {market_prices_file.id}. You have access to these files and answer any user queries accordingly. \
#                         Both the files are csvs, the trades_dataset contains columns cusip, trade_timestamp, trade_size, face_value, asset_inventory, fill, execution_time, trade_price, trade_direction, counterparty, trader. \
#                         The market_prices dataset contains columns cusip, trade_timestamp, trade_price. \
#                     If a trade references one of the metrics below, please take the following steps to calculate the relevant values: \
#                     *Note: Assume that the benchmark price referred to in all of these calculations is the bid ask midpoint (BAM) or the market price 5 minutes after the trade occurs, unless otherwise specified by trader or instructions* \
#                     - NBBO (national best bid offer) - Refers to two values, the bid (sell) and ask (buy) price of the market \
#                     - BAM (bid ask midpoint) - Is calculated as the average of the bid and ask prices in the market prices file. If bid / ask is not given, assume the given price is the BAM \
#                     - Slippage / Markout / Implementation Shortfall  - all refer the difference between the trade price and the market price. For a BUY order, this metric  “= trade price - benchmark”. For SELL order this metric  “= benchmark - trade price” \
#                     - Effective Cost - same as implementation shortfall calculation, except the benchmark is the BAM at the time of the trade \
#                     - Realized Cost - same as implementation shortfall using the post-trade benchmark \
#                     - Price Impact - “Effective Cost - Realized Cost” \
#                     - Price improvement  - for BUY orders, “= market ask (at time of trade) - trade price”. For SELL orders “= trade price - market bid (at time of trade)”. If bid / ask is not given in file, please tell the trader that it has not been supplied and that you cannot finish the calculation without those values \
#                     - Bid ask spread - “ask price - bid price”, can refer to the bid/ask spread of the market or the trader. If bid / ask is not given in file, please tell the trader that it has not been supplied and that you cannot finish the calculation without those values \
#                     - TWAP - refers to the time weighted average price. TWAP is calculated by dividing a specified time period into intervals, computing the average price for each interval, weighting these averages by the time duration, and then summing up the weighted prices, which is finally divided by the total time. \
#                     - VWAP - refers to the volume weighted average price. VWAP is determined by calculating the product of each trade's price and volume, summing these volume-weighted prices, summing the total volume of shares traded, and then dividing the sum of volume-weighted prices by the total volume. This provides an average price reflecting the impact of trade volumes over a specified time period. \
#                     - Fills / Fill Quality / Fill Time - Refers to completed trades. Fill quality refers to the characteristics around the implementation shortfall, whether it is positive or negative, etc. Fill time refers to the time it takes for the trade to be executed \
#             "

#         # assistant = client.beta.assistants.create(
#         #     name="BlockhouseGPT",
#         #     instructions=instructions,
#         #     model="gpt-3.5-turbo-1106",
#         #     tools=[{"type": "retrieval"}],
#         #     file_ids=[trade_prices_file.id, market_prices_file.id]
#         # )

#         assistant_id = "asst_7c0rKP59pE26qagpLBzfm7z7"

#         # Create a new thread
#         thread = client.beta.threads.create()
#         thread_id = thread.id
#         # Replace with your actual assistant ID
#         # assistant_id = "asst_bMy5ZOwX4pdCFTZlIqyiJs0i"
#         # assistant_id = "asst_73dlMPtjQDdOFQR2WMAxBKSR"

#         message = client.beta.threads.messages.create(
#             thread_id=thread_id,
#             role="user",
#             content="hello"
#         )

#         run = client.beta.threads.runs.create(
#             thread_id=thread_id,
#             assistant_id=assistant_id,
#             instructions=instructions
#         )

#         run_id = run.id

#         return JsonResponse({'thread_id': thread_id, "run_id": run_id, "assistant_id": assistant_id}, status=201)

#     except Exception as e:
#         print(f"Error: {e}")
#         return JsonResponse({'error': str(e)}, status=400)


# @csrf_exempt
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def check_messages(request):
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON'}, status=400)

#     try:
#         thread_id = data.get('threadId')
#         run_id = data.get('runId')

#         run = client.beta.threads.runs.retrieve(
#             thread_id=thread_id, run_id=run_id)

#         run_status = run.status

#         if run_status == "completed":
#             api_messages = client.beta.threads.messages.list(
#                 thread_id=thread_id, order="asc")

#             messages = [{
#                 'message': msg.content[0].text.value,
#                 'sender': msg.role,
#             } for msg in api_messages]

#             return JsonResponse({"status": "completed", 'messages': messages})
#         else:
#             return JsonResponse({"status": run_status})
#     except Exception as e:
#         return JsonResponse({'error': e}, status=400)


# @csrf_exempt
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def send_chat_message(request):
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON'}, status=400)

#     try:
#         assistant_id = data.get('assistantId')
#         thread_id = data.get('threadId')
#         message = data.get('message')

#         message = client.beta.threads.messages.create(
#             thread_id=thread_id,
#             role="user", content=message
#         )

#         run = client.beta.threads.runs.create(
#             thread_id=thread_id,
#             assistant_id=assistant_id,
#         )

#         return JsonResponse({"run_id": run.id, "status": "in_progress"}, status=201)
#     except Exception as e:
#         return JsonResponse({'error': e}, status=400)
