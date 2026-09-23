import boto3
from io import StringIO
import logging
import json
import pandas as pd
import csv

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

from Analytics.models import Uploads, Trade, UploadHoodWinked, UploadBlockhouse
from Analytics.Engine.DataProcessing import DataCleaning
from Analytics.utils.timestamp_converter import convert_to_datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

from datetime import datetime, timedelta
from Analytics.utils import reportCalculation, testreports, word_report
from Analytics.utils import data_fetching_and_preprocessing
from decimal import Decimal
import numpy as np
from io import BytesIO
import base64
import re

import jwt
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

def get_user_email_from_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        email = request.query_params.get('email')
        if not email:
            raise ValueError('Authorization header missing and email not provided in query params')
        return email
    
    token = auth_header.split(' ')[1]
    try:
        decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        email = decoded.get('email')
        if not email:
            raise ValueError('Email not found in token')
        return email
    except jwt.ExpiredSignatureError:
        raise ValueError('Token has expired')
    except jwt.InvalidTokenError:
        raise ValueError('Invalid token')

@csrf_exempt
@api_view(['POST'])
# @permission_classes([IsAuthenticated])
def hoodwinked_upload_file(request):
    try:
        user_email = get_user_email_from_token(request)
        platform = request.POST.get('platform')
        print("user_email", user_email)
        print("platform", platform)
        files = request.FILES.getlist('files')  # Get multiple files

        if not files:
            return JsonResponse({'error': 'No files provided'}, status=400)

        if user_email != 'demo':
            # Read the file through dataFrame
            file_df = pd.read_csv(files[0])

            # Check the unique columns
            unique_column=''
            if platform == 'Charles Schwab':
                unique_column = 'Fees and Comm'
            elif platform == 'Robinhood':
                unique_column = 'Trans Code'
            elif platform == 'Webull':
                unique_column = 'Filled Time'
            
            # if unique_column not in file_df.columns:
            #     return JsonResponse({'error': 'Apologies, it seems like the platform you have specified is incorrect, or the data has been manipulated. Please try re-uploading the original file again and specify the correct platform.'}, status=400)

            # Data Cleaning
            cleaned_data = dataCleaning(file_df, platform)

            # Check if the 'Activity Date' column exists
            # if 'Activity Date' not in cleaned_data.columns:
            #     return JsonResponse({'error': "Column 'Activity Date' not found in the file"}, status=400)
            
            # Convert 'Activity Date' to datetime
            # cleaned_data['Activity Date'] = pd.to_datetime(cleaned_data['Activity Date'], errors='coerce')
            
            # Check if there are any equity trades in the last 2 years
            # two_years_ago = datetime.now() - timedelta(days=2*365)
            # recent_trades = cleaned_data[cleaned_data['Activity Date'] >= two_years_ago]
            # print("recent_trades", recent_trades)
            
            # if recent_trades.empty:
            #     return JsonResponse({'error': "No trades within the last 2 years"}, status=400)
            
            # equity_trades = recent_trades[recent_trades['Trans Code'].str.contains('buy|sell', case=False, regex=True)]
            
            # if equity_trades.empty:
            #     return JsonResponse({'error': "No equity trades within the last 2 years"}, status=400)
            
        
        # Data Uploading
        s3 = boto3.client('s3',
                          aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                          region_name=settings.AWS_REGION)

        responses = []

        for file in files:
            try:
                # user_folder = str(user_email)  # or use request.user.username
                user_folder = f"hoodwinked/app/{user_email}"

                # Add a timestamp to the file name to make it unique
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                s3_file_name = f"{timestamp}_{file.name}"
                s3_file_path = f"{user_folder}/{s3_file_name}"

                # Convert DataFrame to CSV
                if user_email == 'demo':
                    s3.upload_fileobj(file, settings.AWS_STORAGE_BUCKET, s3_file_path)
                else:
                    csv_buffer = StringIO()
                    cleaned_data.to_csv(csv_buffer, index=False)
                    # s3.upload_fileobj(cleaned_data, settings.AWS_STORAGE_BUCKET, s3_file_path)
                    s3.put_object(Bucket=settings.AWS_STORAGE_BUCKET, Key=s3_file_path, Body=csv_buffer.getvalue())

                upload_record = UploadHoodWinked.objects.create(
                    user_email=user_email,
                    file_name=s3_file_name,
                    file_size=file.size,
                    file_path=f"https://analyticsv1.s3.amazonaws.com/{s3_file_path}",
                    platform=platform
                )

                # trades_list = [
                #     Trade(
                #         file=upload_record,
                #         cusip=row['CUSIP'],
                #         trade_timestamp=convert_to_datetime(
                #             row['Trade Date'], row['Trade Time']),
                #         trade_size=int(row['Trade Size']),
                #         face_value=int(row['Face Value']),
                #         asset_inventory=int(row['Asset Inventory']),
                #         fill=row['Fill'],
                #         execution_time=int(row['Execution Time']),
                #         trade_price=float(row['Trade Price']),
                #         trade_direction=row['Trade Direction'].upper(),
                #         counterparty=row['Counterparty'],
                #         trader=row['Trader']
                #     ) for index, row in df.iterrows()
                # ]

                # Trade.objects.bulk_create(trades_list)

                responses.append(
                    {'message': f'File {file.name} uploaded successfully'})
            except Exception as e:
                logger.error(
                    f"Error uploading file {file.name} to S3: {str(e)}", exc_info=True)
                responses.append({'error': str(e), 'file': file.name})

        return JsonResponse({'responses': responses})

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)

def dataCleaning(df, platform):
    def preprocess_by_platform(trade_blotter, platform_type):
        if platform_type == 'Robinhood':
            return process_robinhood(trade_blotter)
        elif platform_type == 'Charles Schwab':
            return process_cs(trade_blotter)
        elif platform_type == 'Webull':
            return process_webull(trade_blotter)
        else:
            return 'Error'
        
    def process_cs(trade_blotter):
        
        trade_blotter.rename(columns={
        'Date': 'Activity Date',
        'Action': 'Trans Code',
        'Symbol': 'Instrument'
        }, inplace=True)
        
        trade_blotter.dropna(subset=['Activity Date', 'Trans Code', 'Instrument'], inplace=True)
        trade_blotter_filtered = trade_blotter[trade_blotter['Trans Code'].str.contains('buy|sell', case=False, regex=True)]
        
        return trade_blotter_filtered

    def process_robinhood(trade_blotter):
        
        trade_blotter.dropna(subset=['Activity Date', 'Trans Code', 'Instrument'], inplace=True)
        trade_blotter_filtered = trade_blotter[trade_blotter['Trans Code'].str.contains('buy|sell', case=False, regex=True)]
        
        return trade_blotter_filtered

    def process_webull(trade_blotter):
        trade_blotter.rename(columns={
        'Date': 'Activity Date',
        'Action': 'Trans Code',
        'Symbol': 'Instrument'
        }, inplace=True)
        trade_blotter.dropna(subset=['Activity Date', 'Trans Code', 'Instrument'], inplace=True)
        trade_blotter_filtered = trade_blotter[trade_blotter['Trans Code'].str.contains('buy|sell', case=False, regex=True)]
        
        return trade_blotter_filtered
    
    processed_df = preprocess_by_platform(df, platform)
    return processed_df

@csrf_exempt
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def hoodwinked_files_list(request):
    try:
        user_email = get_user_email_from_token(request)
        print("user_email", user_email)

        uploads = UploadHoodWinked.objects.filter(user_email=user_email).values()
        return JsonResponse({'uploads': list(uploads)})

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)
    except Exception as e:
        logger.error(f"Error fetching files: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
    

@csrf_exempt
# @permission_classes([IsAuthenticated])
def hoodwinked_delete_file(request):
    try:
        get_user_email_from_token(request)  # Verify token

        if request.method == 'POST':
            try:
                # Check if the request body is empty
                if not request.body:
                    return JsonResponse({'error': 'Empty request body'}, status=400)
                
                # Handle JSON parsing errors
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError as e:
                        return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
                file_id = data.get('file_id')

                if not file_id:
                    return JsonResponse({'error': 'No file ID provided'}, status=400)

                upload = UploadHoodWinked.objects.get(id=file_id)

                # Trade.objects.filter(file=upload).delete()

                s3 = boto3.client('s3',
                                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                  region_name=settings.AWS_REGION)
                
                filtered_path = upload.file_path.replace('https://analyticsv1.s3.amazonaws.com/', '')
                s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET,
                                 Key=filtered_path)

                upload.delete()

                return JsonResponse({'message': 'File deleted successfully'})

            except Exception as e:
                logger.error(
                    f"Error deleting file from S3: {str(e)}", exc_info=True)
                return JsonResponse({'error': str(e)}, status=500)
        else:
            return JsonResponse({'error': 'Invalid request method'}, status=405)

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)

@csrf_exempt
# @permission_classes([IsAuthenticated])
def blockhouse_delete_file(request):
    try:
        # get_user_email_from_token(request)  # Verify token

        if request.method == 'POST':
            try:
                # Check if the request body is empty
                if not request.body:
                    return JsonResponse({'error': 'Empty request body'}, status=400)
                
                # Handle JSON parsing errors
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError as e:
                        return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
                file_id = data.get('file_id')

                if not file_id:
                    return JsonResponse({'error': 'No file ID provided'}, status=400)

                upload = UploadBlockhouse.objects.get(id=file_id)

                # Trade.objects.filter(file=upload).delete()

                s3 = boto3.client('s3',
                                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                  region_name=settings.AWS_REGION)
                
                filtered_path = upload.file_path.replace('https://analyticsv1.s3.amazonaws.com/', '')
                s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET,
                                 Key=filtered_path)

                upload.delete()

                return JsonResponse({'message': 'File deleted successfully'})

            except Exception as e:
                logger.error(
                    f"Error deleting file from S3: {str(e)}", exc_info=True)
                return JsonResponse({'error': str(e)}, status=500)
        else:
            return JsonResponse({'error': 'Invalid request method'}, status=405)

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def hoodwinked_generate_report(request):
    try:
        get_user_email_from_token(request)  # Verify token

        file_id = request.query_params.get('file_id')
        platform = request.query_params.get('platform')
        site = request.query_params.get('site')
        siteType = request.query_params.get('siteType')
        # upload = UploadHoodWinked.objects.get(id=file_id)

        # s3 = boto3.client('s3',
        #                     aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        #                     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        #                     region_name=settings.AWS_REGION)

        # # s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET,
        # #                     Key=upload.file_name)

        # user_folder = str(upload.user_email)  # or use request.user.username
        # s3_file_path = f"{user_folder}/{upload.file_name}"

        # obj = s3.get_object(
        #         Bucket=settings.AWS_STORAGE_BUCKET, Key=s3_file_path)
        
        # file_content = obj['Body'].read().decode('utf-8')

        # df = pd.read_csv(StringIO(file_content))
        cache_key = f"{platform}_{file_id}"
        df = cache.get(key=cache_key)
        #print(df)
        if df is None:
            print('Not in Cache')
            df = fetch_file_from_s3(file_id, site, siteType)
            cache.set(key=cache_key, value=df, timeout=60*15)
        else:
            print('In Cache')
            df = cache.get(key=cache_key)
        
        #df = fetch_file_from_s3(file_id)

        # Report Calculation
        report_calculation = reportCalculation.main(df, platform,file_id)

        # Generate Report
        return word_report.generate_report(report_calculation)

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)
    except Exception as e:
        logger.error(f"Error fetching files: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def hoodwinked_generate_report_pdf(request):
    try:
        get_user_email_from_token(request)  # Verify token

        file_id = request.query_params.get('file_id')
        platform = request.query_params.get('platform')
        site = request.query_params.get('site')
        siteType = request.query_params.get('siteType')
        # upload = UploadHoodWinked.objects.get(id=file_id)

        # s3 = boto3.client('s3',
        #                     aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        #                     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        #                     region_name=settings.AWS_REGION)

        # # s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET,
        # #                     Key=upload.file_name)

        # user_folder = str(upload.user_email)  # or use request.user.username
        # s3_file_path = f"{user_folder}/{upload.file_name}"

        # obj = s3.get_object(
        #         Bucket=settings.AWS_STORAGE_BUCKET, Key=s3_file_path)
        
        # file_content = obj['Body'].read().decode('utf-8')

        # df = pd.read_csv(StringIO(file_content))
        cache_key = f"{platform}_{file_id}"
        df = cache.get(key=cache_key)
        #print(df)
        if df is None:
            print('Not in Cache')
            df = fetch_file_from_s3(file_id, site, siteType)
            cache.set(key=cache_key, value=df, timeout=60*15)
        else:
            print('In Cache')
            df = cache.get(key=cache_key)
        
        #df = fetch_file_from_s3(file_id)

        # Report Calculation
        report_calculation = reportCalculation.main(df, platform,file_id)

        # Generate Report
        return testreports.generate_report(report_calculation)

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)
    except Exception as e:
        logger.error(f"Error fetching files: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
def hoodwinked_generate_report_plaid(request):
    try:
        email = get_user_email_from_token(request)

        platform = request.query_params.get('platform')
        
        file_id = email
        cache_key = f"{platform}_{file_id}"
        df = cache.get(key=cache_key)
        #print(df)
        if df is None:
            print('Not in Cache')
            #df = fetch_file_from_s3(file_id)
            df = fetch_latest_file_from_s3(email)
            cache.set(key=cache_key, value=df, timeout=60*15)
        else:
            print('In Cache')
            df = cache.get(key=cache_key)
        
        # Report Calculation
        report_calculation = reportCalculation.main(df, platform,file_id)

        # Generate Report
        document_base64 = testreports.generate_report(report_calculation)
        # return JsonResponse({'document': document_base64, 'message': 'Report generation successful'})
        return document_base64

        # return JsonResponse({'uploads': "successful"})
    except ZeroDivisionError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except IndexError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)
    except Exception as e:
        logger.error(f"Error fetching files: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

def count_trades(df):
    try:
      ret = df[df['type'].isin(['buy', 'sell'])].shape[0]
      return ret
    except:
      ret = df[df['Trans Code'].isin(['buy', 'sell'])].shape[0]
      return ret

def get_plaid_aum(df):

    try:
        # starting_aum = Decimal('0')  
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
        return JsonResponse({'error': str(e)}, status=500)

# Helper function to convert non-serializable objects to JSON serializable
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


@api_view(['GET'])
def hoodwinked_onboard_plaid_data(request):
    try:
        email = get_user_email_from_token(request)

        platform = request.query_params.get('platform')
        cache_key = f"{platform}_{email}"
        
        df = cache.get(cache_key)
        if df is None:
            print('Not in Cache')
            try:
                df = fetch_latest_file_from_s3(email)
                if df is not None and not df.empty:
                    cache.set(cache_key, df, timeout=60*15)
                else:
                    return JsonResponse({'error': 'No data found for the user'}, status=404)
            except Exception as e:
                logger.error(f"Error fetching data from S3: {str(e)}", exc_info=True)
                return JsonResponse({'error': 'Failed to fetch user data'}, status=500)
        else:
            print('In Cache')
        
        try:
            report_calculation = reportCalculation.main(df, platform, email)
        except Exception as e:
            logger.error(f"Error in report calculation: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'Failed to generate report'}, status=500)
        
        try:
            plaid_aum_data = get_plaid_aum(df)
            report_calculation['plaid_aum'] = plaid_aum_data
        except Exception as e:
            logger.error(f"Error in Plaid AUM calculation: {str(e)}", exc_info=True)
            report_calculation['plaid_aum'] = None  # Set to None if calculation fails
        
        try:
            serializable_data = convert_to_serializable(report_calculation)
        except Exception as e:
            logger.error(f"Error in data serialization: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'Failed to serialize report data'}, status=500)
        
        return JsonResponse({
            'data': serializable_data,
            'message': 'Report generation successful'
        })
    except Exception as e:
        logger.error(f"Unexpected error in hoodwinked_onboard_plaid_data: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def hoodwinked_analyze(request):
    print('In Hoodwinked Analyze')
    try:
        get_user_email_from_token(request)  # Verify token

        file_id = request.query_params.get('file_id')
        platform = request.query_params.get('platform')
        
        cache_key = f"{platform}_{file_id}"
        df = cache.get(key=cache_key)
        trade_blotter = cache.get(key=f"{platform}_{file_id}_trade_blotter")
        scaling_factor_report = cache.get(key=f"{platform}_{file_id}_scaling_factor")
        #print(df)
        if df is None or trade_blotter is None or scaling_factor_report is None: 
            print('Not in Cache')
            df= fetch_file_from_s3(file_id)
            cache.set(key=cache_key, value=df, timeout=60*15)
            trade_blotter, tickers, data_dict = preprocess_data_merged(df, platform)
            cache.set(key=f"{platform}_{file_id}_trade_blotter", value=trade_blotter, timeout=60*15)
            trade_blotter_filtered = trade_blotter.copy()
            cache.set(key=f"{platform}_{file_id}_tickers", value=tickers, timeout=60*15)
            cache.set(key=f"{platform}_{file_id}_data_dict", value=data_dict, timeout=60*15)
            scaling_factor_report = reportCalculation.calculate_potential_savings(trade_blotter)['scaling_factor']
            cache.set(key=f"{platform}_{file_id}_scaling_factor", value=scaling_factor_report, timeout=60*15)
            
            ##Set cache for report calculation
            #reportCalculation.main(df, platform)
        else:
            print('In Cache')
            df = cache.get(key=cache_key)
            trade_blotter = cache.get(key=f"{platform}_{file_id}_trade_blotter")
            tickers = cache.get(key=f"{platform}_{file_id}_tickers")
            data_dict = cache.get(key=f"{platform}_{file_id}_data_dict")
            scaling_factor_report = cache.get(key=f"{platform}_{file_id}_scaling_factor")
            trade_blotter_filtered = trade_blotter.copy()
            


        #scaling_factor_report = reportCalculation.calculate_potential_savings(trade_blotter)['scaling_factor']
        
        # df = fetch_file_from_s3(file_id)
        # trade_blotter, tickers, data_dict = preprocess_data(df, platform)
        # trade_blotter_filtered = trade_blotter.copy()

        # Convert ndarray to list
        instruments_list = tickers.tolist()

        # Slippage Pie Chart
        # start_date = trade_blotter_filtered['Activity Date'].min()
        # start_date = '2022-08-17'
        # end_date = trade_blotter_filtered['Activity Date'].max()
        # end_date = '2024-04-16'
        #end_date = '2024-08-16'
        
        stock = trade_blotter_filtered['Instrument'].unique().tolist()[0]
        instruments_list = trade_blotter_filtered['Instrument'].unique().tolist()
        benchmark = ['Close', 'Open', 'TWAP', 'VWAP', 'HWOE'][0]
        # # slippage_pie_chart
        # slippage_summary = data_fetching_and_preprocessing.slippage_pie_chart(trade_blotter_filtered, stock, start_date, end_date, benchmark)

        # Line Chart
        start_date = trade_blotter_filtered['Activity Date'].min()
        end_date = trade_blotter_filtered['Activity Date'].max()
        #trade_blotter_filtered_line = filter_tickers_for_line_charts(trade_blotter_filtered)
        trade_blotter_filtered_line = trade_blotter.copy()
        instruments_list_line = trade_blotter_filtered_line['Instrument'].tolist()
        slippage_over_time = data_fetching_and_preprocessing.plot_excess_returns(trade_blotter_filtered_line, stock, show_open=True, show_close=True, show_twap=True, show_vwap=True, show_hwoe=True, start_date=start_date, end_date=end_date,hwoe_adjustment_factor=scaling_factor_report,aggregate=True)

        # Slippage heatmap
        # slippage_heatmap = data_fetching_and_preprocessing.calculate_slippage(trade_blotter_filtered, data_dict)
        # slippage_heatmap_trade_option = data_fetching_and_preprocessing.calculate_slippage_trade_option(trade_blotter_filtered)

        # Slippage Bar
        slippage_bar = data_fetching_and_preprocessing.calculate_slippage_sums(trade_blotter,hwoe_adjustment_factor=scaling_factor_report)
        slippage_bar_trade_option = data_fetching_and_preprocessing.calculate_slippage_bar_trade_option(trade_blotter_filtered)


        # Candlestick chart
        candlestick_trade_options = data_fetching_and_preprocessing.candle_stick_trade_option(trade_blotter_filtered)
        candlestick_chart = data_fetching_and_preprocessing.setup_slippage_analysis(trade_blotter_filtered, data_dict, candlestick_trade_options[0])

        # return JsonResponse({'stocks': instruments_list, 'date_range': { 'start_date': start_date, 'end_date': end_date }, 'slippage_pie_chart': slippage_summary, 'slippage_over_time': slippage_over_time, 'slippage_heatmap_summary': {'heatmap_data': slippage_heatmap, 'trade_option': slippage_heatmap_trade_option}, 'candle_stick_summary': { 'candle_stick_trade_option': candlestick_trade_options, 'candlestick_chart': candlestick_chart  } })
        return JsonResponse({'stocks': instruments_list, 'stocks_for_line_chart': instruments_list, 'date_range': { 'start_date': start_date, 'end_date': end_date },'slippage_over_time': slippage_over_time, 'slippage_bar_summary': {'bar_data': slippage_bar, 'trade_option': slippage_bar_trade_option}, 'candle_stick_summary': { 'candle_stick_trade_option': candlestick_trade_options, 'candlestick_chart': candlestick_chart  } })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)
    except Exception as e:
        logger.error(f"Error fetching files: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
    

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def blockhouse_analyze(request):
    print('In Blockhouse Analyze')
    try:
        get_user_email_from_token(request)  # Verify token

        file_id = request.query_params.get('file_id')
        platform = request.query_params.get('platform')
        
        cache_key = f"b_{platform}_{file_id}"
        df = cache.get(key=cache_key)
        trade_blotter = cache.get(key=f"b_{platform}_{file_id}_trade_blotter")
        scaling_factor_report = cache.get(key=f"b_{platform}_{file_id}_scaling_factor")
        #print(df)
        if df is None or trade_blotter is None or scaling_factor_report is None: 
            print('Not in Cache')
            df= fetch_file_from_blockhouse_s3(file_id)
            cache.set(key=cache_key, value=df, timeout=60*15)
            trade_blotter, tickers, data_dict = preprocess_data_merged(df, platform)
            cache.set(key=f"b_{platform}_{file_id}_trade_blotter", value=trade_blotter, timeout=60*15)
            trade_blotter_filtered = trade_blotter.copy()
            cache.set(key=f"b_{platform}_{file_id}_tickers", value=tickers, timeout=60*15)
            cache.set(key=f"b_{platform}_{file_id}_data_dict", value=data_dict, timeout=60*15)
            scaling_factor_report = reportCalculation.calculate_potential_savings(trade_blotter)['scaling_factor']
            cache.set(key=f"b_{platform}_{file_id}_scaling_factor", value=scaling_factor_report, timeout=60*15)
            
            ##Set cache for report calculation
            #reportCalculation.main(df, platform)
        else:
            print('In Cache')
            df = cache.get(key=cache_key)
            trade_blotter = cache.get(key=f"b_{platform}_{file_id}_trade_blotter")
            tickers = cache.get(key=f"b_{platform}_{file_id}_tickers")
            data_dict = cache.get(key=f"b_{platform}_{file_id}_data_dict")
            scaling_factor_report = cache.get(key=f"b_{platform}_{file_id}_scaling_factor")
            trade_blotter_filtered = trade_blotter.copy()
            


        #scaling_factor_report = reportCalculation.calculate_potential_savings(trade_blotter)['scaling_factor']
        
        # df = fetch_file_from_s3(file_id)
        # trade_blotter, tickers, data_dict = preprocess_data(df, platform)
        # trade_blotter_filtered = trade_blotter.copy()

        # Convert ndarray to list
        instruments_list = tickers.tolist()

        # Slippage Pie Chart
        # start_date = trade_blotter_filtered['Activity Date'].min()
        # start_date = '2022-08-17'
        # end_date = trade_blotter_filtered['Activity Date'].max()
        # end_date = '2024-04-16'
        #end_date = '2024-08-16'
        
        stock = trade_blotter_filtered['Instrument'].unique().tolist()[0]
        instruments_list = trade_blotter_filtered['Instrument'].unique().tolist()
        benchmark = ['Close', 'Open', 'TWAP', 'VWAP', 'HWOE'][0]
        # # slippage_pie_chart
        # slippage_summary = data_fetching_and_preprocessing.slippage_pie_chart(trade_blotter_filtered, stock, start_date, end_date, benchmark)

        # Line Chart
        start_date = trade_blotter_filtered['Activity Date'].min()
        end_date = trade_blotter_filtered['Activity Date'].max()
        #trade_blotter_filtered_line = filter_tickers_for_line_charts(trade_blotter_filtered)
        trade_blotter_filtered_line = trade_blotter.copy()
        instruments_list_line = trade_blotter_filtered_line['Instrument'].tolist()
        slippage_over_time = data_fetching_and_preprocessing.plot_excess_returns(trade_blotter_filtered_line, stock, show_open=True, show_close=True, show_twap=True, show_vwap=True, show_hwoe=True, start_date=start_date, end_date=end_date,hwoe_adjustment_factor=scaling_factor_report,aggregate=True)

        # Slippage heatmap
        # slippage_heatmap = data_fetching_and_preprocessing.calculate_slippage(trade_blotter_filtered, data_dict)
        # slippage_heatmap_trade_option = data_fetching_and_preprocessing.calculate_slippage_trade_option(trade_blotter_filtered)

        # Slippage Bar
        slippage_bar = data_fetching_and_preprocessing.calculate_slippage_sums(trade_blotter,hwoe_adjustment_factor=scaling_factor_report)
        slippage_bar_trade_option = data_fetching_and_preprocessing.calculate_slippage_bar_trade_option(trade_blotter_filtered)


        # Candlestick chart
        candlestick_trade_options = data_fetching_and_preprocessing.candle_stick_trade_option(trade_blotter_filtered)
        candlestick_chart = data_fetching_and_preprocessing.setup_slippage_analysis(trade_blotter_filtered, data_dict, candlestick_trade_options[0])

        # return JsonResponse({'stocks': instruments_list, 'date_range': { 'start_date': start_date, 'end_date': end_date }, 'slippage_pie_chart': slippage_summary, 'slippage_over_time': slippage_over_time, 'slippage_heatmap_summary': {'heatmap_data': slippage_heatmap, 'trade_option': slippage_heatmap_trade_option}, 'candle_stick_summary': { 'candle_stick_trade_option': candlestick_trade_options, 'candlestick_chart': candlestick_chart  } })
        return JsonResponse({'stocks': instruments_list, 'stocks_for_line_chart': instruments_list, 'date_range': { 'start_date': start_date, 'end_date': end_date },'slippage_over_time': slippage_over_time, 'slippage_bar_summary': {'bar_data': slippage_bar, 'trade_option': slippage_bar_trade_option}, 'candle_stick_summary': { 'candle_stick_trade_option': candlestick_trade_options, 'candlestick_chart': candlestick_chart  } })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)
    except Exception as e:
        logger.error(f"Error fetching files: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
    

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def hoodwinked_analyze_plaid(request):
    print('In Hoodwinked Analyze')
    try:
        email = get_user_email_from_token(request)

        platform = request.query_params.get('platform')
        
        file_id = email
        cache_key = f"{platform}_{file_id}"
        df = cache.get(key=cache_key)
        trade_blotter = cache.get(key=f"{platform}_{file_id}_trade_blotter")
        scaling_factor_report = cache.get(key=f"{platform}_{file_id}_scaling_factor")
        #print(df)
        if df is None or trade_blotter is None or scaling_factor_report is None: 
            print('Not in Cache')
            #df= fetch_file_from_s3(file_id)
            df = fetch_latest_file_from_s3(email)
            cache.set(key=cache_key, value=df, timeout=60*15)
            trade_blotter, tickers, data_dict = preprocess_data_merged(df, platform)
            cache.set(key=f"{platform}_{file_id}_trade_blotter", value=trade_blotter, timeout=60*15)
            trade_blotter_filtered = trade_blotter.copy()
            cache.set(key=f"{platform}_{file_id}_tickers", value=tickers, timeout=60*15)
            cache.set(key=f"{platform}_{file_id}_data_dict", value=data_dict, timeout=60*15)
            scaling_factor_report = reportCalculation.calculate_potential_savings(trade_blotter)['scaling_factor']
            cache.set(key=f"{platform}_{file_id}_scaling_factor", value=scaling_factor_report, timeout=60*15)
            
            ##Set cache for report calculation
            #reportCalculation.main(df, platform)
        else:
            print('In Cache')
            df = cache.get(key=cache_key)
            trade_blotter = cache.get(key=f"{platform}_{file_id}_trade_blotter")
            tickers = cache.get(key=f"{platform}_{file_id}_tickers")
            data_dict = cache.get(key=f"{platform}_{file_id}_data_dict")
            scaling_factor_report = cache.get(key=f"{platform}_{file_id}_scaling_factor")
            trade_blotter_filtered = trade_blotter.copy()
            
        # Sanitize the DataFrame by replacing NaN with None
        df = df.replace({np.nan: None})
        trade_blotter_filtered = trade_blotter_filtered.replace({np.nan: None})

        #scaling_factor_report = reportCalculation.calculate_potential_savings(trade_blotter)['scaling_factor']
        
        # df = fetch_file_from_s3(file_id)
        # trade_blotter, tickers, data_dict = preprocess_data(df, platform)
        # trade_blotter_filtered = trade_blotter.copy()

        # Convert ndarray to list
        instruments_list = tickers.tolist()

        # Slippage Pie Chart
        # start_date = trade_blotter_filtered['Activity Date'].min()
        # start_date = '2022-08-17'
        # end_date = trade_blotter_filtered['Activity Date'].max()
        # end_date = '2024-04-16'
        #end_date = '2024-08-16'
        
        stock = trade_blotter_filtered['Instrument'].unique().tolist()[0]
        instruments_list = trade_blotter_filtered['Instrument'].unique().tolist()
        benchmark = ['Close', 'Open', 'TWAP', 'VWAP', 'HWOE'][0]
        # # slippage_pie_chart
        # slippage_summary = data_fetching_and_preprocessing.slippage_pie_chart(trade_blotter_filtered, stock, start_date, end_date, benchmark)

        # Line Chart
        start_date = trade_blotter_filtered['Activity Date'].min()
        end_date = trade_blotter_filtered['Activity Date'].max()
        #trade_blotter_filtered_line = filter_tickers_for_line_charts(trade_blotter_filtered)
        trade_blotter_filtered_line = trade_blotter.copy()
        instruments_list_line = trade_blotter_filtered_line['Instrument'].tolist()
        slippage_over_time = data_fetching_and_preprocessing.plot_excess_returns(trade_blotter_filtered_line, stock, show_open=True, show_close=True, show_twap=True, show_vwap=True, show_hwoe=True, start_date=start_date, end_date=end_date,hwoe_adjustment_factor=scaling_factor_report,aggregate=True)

        # Slippage heatmap
        # slippage_heatmap = data_fetching_and_preprocessing.calculate_slippage(trade_blotter_filtered, data_dict)
        # slippage_heatmap_trade_option = data_fetching_and_preprocessing.calculate_slippage_trade_option(trade_blotter_filtered)

        # Slippage Bar
        slippage_bar = data_fetching_and_preprocessing.calculate_slippage_sums(trade_blotter,hwoe_adjustment_factor=scaling_factor_report)
        slippage_bar_trade_option = data_fetching_and_preprocessing.calculate_slippage_bar_trade_option(trade_blotter_filtered)


        # Candlestick chart
        candlestick_trade_options = data_fetching_and_preprocessing.candle_stick_trade_option(trade_blotter_filtered)
        for i in range(len(candlestick_trade_options)):
            try:
                candlestick_chart = data_fetching_and_preprocessing.setup_slippage_analysis(trade_blotter_filtered, data_dict, candlestick_trade_options[i])
                break
            except Exception as e:
                if i < len(candlestick_trade_options):
                    print("ERROR: " + str(e) + f". Trying next candlestick_trade_options {i}")
                else:
                    return JsonResponse({"Error": "No valid dates in data"})

        # return JsonResponse({'stocks': instruments_list, 'date_range': { 'start_date': start_date, 'end_date': end_date }, 'slippage_pie_chart': slippage_summary, 'slippage_over_time': slippage_over_time, 'slippage_heatmap_summary': {'heatmap_data': slippage_heatmap, 'trade_option': slippage_heatmap_trade_option}, 'candle_stick_summary': { 'candle_stick_trade_option': candlestick_trade_options, 'candlestick_chart': candlestick_chart  } })
        # return JsonResponse({'stocks': instruments_list, 'stocks_for_line_chart': instruments_list, 'date_range': { 'start_date': start_date, 'end_date': end_date },'slippage_over_time': slippage_over_time, 'slippage_bar_summary': {'bar_data': slippage_bar, 'trade_option': slippage_bar_trade_option}, 'candle_stick_summary': { 'candle_stick_trade_option': candlestick_trade_options, 'candlestick_chart': candlestick_chart  } })
        # Function to replace NaN with None recursively
        def replace_nan_with_none(obj):
            if isinstance(obj, dict):
                return {k: replace_nan_with_none(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_nan_with_none(item) for item in obj]
            elif isinstance(obj, float) and np.isnan(obj):
                return None
            else:
                return obj

        # Replace NaN with None in all data structures
        slippage_over_time = replace_nan_with_none(slippage_over_time)
        slippage_bar = replace_nan_with_none(slippage_bar)
        slippage_bar_trade_option = replace_nan_with_none(slippage_bar_trade_option)
        candlestick_chart = replace_nan_with_none(candlestick_chart)

        response_data = {
            'stocks': instruments_list,
            'stocks_for_line_chart': instruments_list,
            'date_range': {'start_date': start_date, 'end_date': end_date},
            'slippage_over_time': slippage_over_time,
            'slippage_bar_summary': {'bar_data': slippage_bar, 'trade_option': slippage_bar_trade_option},
            'candle_stick_summary': {'candle_stick_trade_option': candlestick_trade_options, 'candlestick_chart': candlestick_chart}
        }

        # Replace any remaining NaN values with None in the entire response
        response_data = replace_nan_with_none(response_data)

        return JsonResponse(response_data)
    except Exception as e:
        logger.error(f"Error fetching files: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
    
import time
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def hoodwinked_graph(request):
    try:
        get_user_email_from_token(request)  # Verify token
        file_id = request.query_params.get('file_id')
        platform = request.query_params.get('platform')
        site = request.query_params.get('site')
        chart_type = request.query_params.get('chart_type')
        trade_option = request.query_params.get('trade_option')
        stock = request.query_params.get('stock')
        show_open = request.query_params.get('show_open')
        show_close = request.query_params.get('show_close')
        show_twap = request.query_params.get('show_twap')
        show_vwap = request.query_params.get('show_vwap')
        show_hwoe = request.query_params.get('show_hwoe')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        benchmark = request.query_params.get('benchmark')
        
        cache_key = f"{platform}_{file_id}"
        df = cache.get(key=cache_key)
        trade_blotter = cache.get(key=f"{platform}_{file_id}_trade_blotter")
        scaling_factor_report = cache.get(key=f"{platform}_{file_id}_scaling_factor")
        #print(df)
        if df is None or trade_blotter is None or scaling_factor_report is None: 
            print('Not in Cache')
            df= fetch_file_from_s3(file_id, site)
            cache.set(key=cache_key, value=df, timeout=60*15)
            trade_blotter, tickers, data_dict = preprocess_data_merged(df, platform)
            cache.set(key=f"{platform}_{file_id}_trade_blotter", value=trade_blotter, timeout=60*15)
            trade_blotter_filtered = trade_blotter.copy()
            cache.set(key=f"{platform}_{file_id}_tickers", value=tickers, timeout=60*15)
            cache.set(key=f"{platform}_{file_id}_data_dict", value=data_dict, timeout=60*15)
            scaling_factor_report = reportCalculation.calculate_potential_savings(trade_blotter)['scaling_factor']
            cache.set(key=f"{platform}_{file_id}_scaling_factor", value=scaling_factor_report, timeout=60*15)
            
            ##Set cache for report calculation
            #reportCalculation.main(df, platform)
        else:
            print('In Cache')
            df = cache.get(key=cache_key)
            trade_blotter = cache.get(key=f"{platform}_{file_id}_trade_blotter")
            tickers = cache.get(key=f"{platform}_{file_id}_tickers")
            data_dict = cache.get(key=f"{platform}_{file_id}_data_dict")
            scaling_factor_report = cache.get(key=f"{platform}_{file_id}_scaling_factor")
            trade_blotter_filtered = trade_blotter.copy()

        # Convert ndarray to list
        instruments_list = tickers.tolist()

        if(chart_type == 'slippage_pie_chart'):
            # Slippage Pie Chart
            slippage_summary = data_fetching_and_preprocessing.slippage_pie_chart(trade_blotter_filtered, stock, start_date, end_date, benchmark)
            return JsonResponse({'slippage_pie_chart': slippage_summary})
        elif(chart_type == 'slippage_over_time'):
            # Line Chart
            if stock is None or stock == 'all_trades':
                aggregate = True
            else:
                aggregate = False
            #trade_blotter_filtered_line = filter_tickers_for_line_charts(trade_blotter_filtered)
            slippage_over_time = data_fetching_and_preprocessing.plot_excess_returns(trade_blotter_filtered, stock, show_open=show_open, show_close=show_close, show_twap=show_twap, show_vwap=show_vwap, show_hwoe=show_hwoe, start_date=start_date, end_date=end_date,hwoe_adjustment_factor=scaling_factor_report,aggregate=aggregate)
            return JsonResponse({'slippage_over_time': slippage_over_time})
        elif(chart_type == 'slippage_bar'):
            # Slippage bar
            slippage_bar = data_fetching_and_preprocessing.calculate_slippage_sums(trade_blotter_filtered, trade_option,hwoe_adjustment_factor=scaling_factor_report)
            print(slippage_bar)
            return JsonResponse({'slippage_bar_data': slippage_bar})
        # elif(chart_type == 'slippage_heatmap'):
        #     # Slippage heatmap
        #     slippage_heatmap = data_fetching_and_preprocessing.calculate_slippage(trade_blotter_filtered, data_dict, trade_option)
        #     return JsonResponse({'heatmap_data': slippage_heatmap})
        elif(chart_type == 'candle_stick'):
            # Candlestick chart 
            print(trade_option)
            candlestick_chart = data_fetching_and_preprocessing.setup_slippage_analysis(trade_blotter_filtered, data_dict, trade_option)
            return JsonResponse({'candlestick_chart': candlestick_chart})

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)
    except Exception as e:
        logger.error(f"Error fetching files: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def hoodwinked_graph_plaid(request):
    try:
        email = get_user_email_from_token(request)
        file_id = email
        platform = request.query_params.get('platform')
        site = request.query_params.get('site')
        chart_type = request.query_params.get('chart_type')
        trade_option = request.query_params.get('trade_option')
        stock = request.query_params.get('stock')
        show_open = request.query_params.get('show_open', 'true')
        show_close = request.query_params.get('show_close', 'true')
        show_twap = request.query_params.get('show_twap', 'true')
        show_vwap = request.query_params.get('show_vwap', 'true')
        show_hwoe = request.query_params.get('show_hwoe', 'true')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        benchmark = request.query_params.get('benchmark')

        trade_option = 'All Trades' if not trade_option else trade_option
        
        cache_key = f"{platform}_{file_id}"
        df = cache.get(key=cache_key)
        trade_blotter = cache.get(key=f"{platform}_{file_id}_trade_blotter")
        scaling_factor_report = cache.get(key=f"{platform}_{file_id}_scaling_factor")
        if df is None or trade_blotter is None or scaling_factor_report is None: 
            print('Not in Cache')
            df= fetch_latest_file_from_s3(email)
            cache.set(key=cache_key, value=df, timeout=60*15)
            
            trade_blotter, tickers, data_dict = preprocess_data_merged(df, platform)
            cache.set(key=f"{platform}_{file_id}_trade_blotter", value=trade_blotter, timeout=60*15)
            
            trade_blotter_filtered = trade_blotter.copy()
            cache.set(key=f"{platform}_{file_id}_tickers", value=tickers, timeout=60*15)
            cache.set(key=f"{platform}_{file_id}_data_dict", value=data_dict, timeout=60*15)
            
            scaling_factor_report = reportCalculation.calculate_potential_savings(trade_blotter)['scaling_factor']
            cache.set(key=f"{platform}_{file_id}_scaling_factor", value=scaling_factor_report, timeout=60*15)
            
        else:
            print('In Cache')
            df = cache.get(key=cache_key)
            trade_blotter = cache.get(key=f"{platform}_{file_id}_trade_blotter")
            tickers = cache.get(key=f"{platform}_{file_id}_tickers")
            data_dict = cache.get(key=f"{platform}_{file_id}_data_dict")
            scaling_factor_report = cache.get(key=f"{platform}_{file_id}_scaling_factor")
            trade_blotter_filtered = trade_blotter.copy()

        if trade_blotter_filtered.empty:
            return JsonResponse({"error": f"File is empty (empty dataframe) for user {email}"})
        
        trade_blotter_filtered = trade_blotter_filtered.dropna(how='all', subset=['Open_Price', 'Close_Price', 'TWAP_Price', 'VWAP_Price', 'HWOE_Price', 'Market Volume', 'Volume_Rolling_Mean', 'Volatility', 'Volatility_Rolling_Mean', 'High', 'Low', 'HWOE_Day', 'HWOE_Time', '5d_MA'])

        # Check parameters validity
        stock = 'all_trades' if stock is None else stock
        if stock not in trade_blotter_filtered['Instrument'].unique().tolist() and stock != 'all_trades':
            return JsonResponse({"error": f"Stock {stock} not found in the trade blotter, found stocks are {trade_blotter_filtered['Instrument'].unique().tolist()}"})
        if start_date is None or (pd.to_datetime(start_date, errors='coerce') < trade_blotter_filtered['Activity Date'].min()):
            start_date = trade_blotter_filtered['Activity Date'].min()
        if end_date is None or (pd.to_datetime(end_date, errors='coerce') > trade_blotter_filtered['Activity Date'].max()):
            end_date = trade_blotter_filtered['Activity Date'].max()
        
        # Return the requested chart
        if(chart_type == 'slippage_pie_chart'):
            if benchmark not in ['Close', 'Open', 'TWAP', 'VWAP', 'HWOE']:
              return JsonResponse({"error": f"Benchmark {benchmark} is not valid, valid benchmarks are ['Close', 'Open', 'TWAP', 'VWAP', 'HWOE']"})
            # if stock is 'all_trades', return data for all stocks
            if stock == 'all_trades':
                slippage_summary = []
                for stock in trade_blotter_filtered['Instrument'].unique().tolist():
                    data = data_fetching_and_preprocessing.slippage_pie_chart(trade_blotter_filtered, stock, start_date, end_date, benchmark)
                    data['stock'] = stock
                    slippage_summary.append(data)
            # else, return data for the requested stock
            else:
                slippage_summary = data_fetching_and_preprocessing.slippage_pie_chart(trade_blotter_filtered, stock, start_date, end_date, benchmark)
                slippage_summary['stock'] = stock
                
            slippage_summary = convert_nan_to_null(slippage_summary)
            
            return JsonResponse({'slippage_pie_chart': slippage_summary})
        
        elif(chart_type == 'slippage_over_time'):
            # Aggregate the data if stock is 'all_trades'
            aggregate = True if stock == 'all_trades' else False
            trade_blotter_filtered_line = trade_blotter.copy()
            
            show_open = True if show_open.lower() == 'true' else False
            show_close = True if show_close.lower() == 'true' else False
            show_twap = True if show_twap.lower() == 'true' else False
            show_vwap = True if show_vwap.lower() == 'true' else False
            show_hwoe = True if show_hwoe.lower() == 'true' else False
            
            slippage_over_time = data_fetching_and_preprocessing.plot_excess_returns(trade_blotter_filtered_line, stock, show_open=show_open, show_close=show_close, show_twap=show_twap, show_vwap=show_vwap, show_hwoe=show_hwoe, start_date=start_date, end_date=end_date, hwoe_adjustment_factor=scaling_factor_report, aggregate=aggregate)
            slippage_over_time = convert_nan_to_null(slippage_over_time)
            
            return JsonResponse({'slippage_over_time': slippage_over_time})
        
        elif(chart_type == 'slippage_bar'):
            slippage_bar = data_fetching_and_preprocessing.calculate_slippage_sums_plaid(trade_blotter_filtered, trade_option, hwoe_adjustment_factor=scaling_factor_report)
            slippage_bar = convert_nan_to_null(slippage_bar)
            
            return JsonResponse({'slippage_bar_data': slippage_bar})
        
        elif(chart_type == 'candle_stick'):
            candlestick_trade_options = data_fetching_and_preprocessing.candle_stick_trade_option(trade_blotter_filtered)
            # If all trades are requested, return data for all stocks using the first trade option found for each stock
            if stock == 'all_trades':
                candlestick_chart = []
                for stock in trade_blotter_filtered['Instrument'].unique().tolist():
                    valid_stock_idx = next((i for i, trade_option in enumerate(candlestick_trade_options) if stock in trade_option), -1)
                    if valid_stock_idx == -1:
                        return JsonResponse({"error": f"Stock {stock} not found in any trade option, found stocks are {candlestick_trade_options}"})
                    data = data_fetching_and_preprocessing.setup_slippage_analysis(trade_blotter_filtered, data_dict, candlestick_trade_options[valid_stock_idx])
                    data['stock'] = stock
                    candlestick_chart.append(data)
            # else, return data for the requested stock using the first trade option found for that stock
            else:
                valid_stock_idx = next((i for i, trade_option in enumerate(candlestick_trade_options) if stock in trade_option), -1)
                if valid_stock_idx == -1:
                    return JsonResponse({"error": f"Stock {stock} not found in any trade option, found stocks are {candlestick_trade_options}"})
                candlestick_chart = data_fetching_and_preprocessing.setup_slippage_analysis(trade_blotter_filtered, data_dict, candlestick_trade_options[valid_stock_idx])
                candlestick_chart['stock'] = stock
            
            candlestick_chart = convert_nan_to_null(candlestick_chart)
            
            return JsonResponse({'candlestick_chart': candlestick_chart})
        
        else:
            return JsonResponse({"error": f"Invalid chart type {chart_type}, valid chart types are ['slippage_pie_chart', 'slippage_over_time', 'slippage_bar', 'candle_stick']"})

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)
    except Exception as e:
        logger.error(f"Error fetching files: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
    
def fetch_latest_file_from_s3(user_email):
    s3 = boto3.client('s3',
                      aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                      region_name=settings.AWS_REGION)
    
    user_folder = user_folder = f"hoodwinked/plaid/{user_email}"
    
  
    response = s3.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET, Prefix=f"{user_folder}/")
    if 'Contents' not in response:
        raise FileNotFoundError(f"No files found for user {user_email}")
    
    files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
    
    latest_file_key = files[0]['Key']
    
    obj = s3.get_object(Bucket=settings.AWS_STORAGE_BUCKET, Key=latest_file_key)
    file_content = obj['Body'].read().decode('utf-8')
    
    df = pd.read_csv(StringIO(file_content))
    
    return df


def fetch_file_from_s3(file_id, site=None, siteType=None):
    if site is None:
        upload = UploadHoodWinked.objects.get(id=file_id)
    else:
        upload = UploadBlockhouse.objects.get(id=file_id)
    s3 = boto3.client('s3',
                      aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                      region_name=settings.AWS_REGION)
    user_folder = str(upload.user_email)  # or use request.user.username
    if site is None:
        s3_file_path = f"hoodwinked/app/{user_folder}/{upload.file_name}"
    else:
        if siteType == 'demo':
            s3_file_path = f"Blockhouse/demo/{user_folder}/{upload.file_name}"
        else:
            s3_file_path = f"Blockhouse/app/{user_folder}/{upload.file_name}"
    obj = s3.get_object(Bucket=settings.AWS_STORAGE_BUCKET, Key=s3_file_path)
    file_content = obj['Body'].read().decode('utf-8')
    df = pd.read_csv(StringIO(file_content))
    return df

def fetch_file_from_blockhouse_s3(file_id):
    upload = UploadBlockhouse.objects.get(id=file_id)
    s3 = boto3.client('s3',
                      aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                      region_name=settings.AWS_REGION)
    user_folder = str(upload.user_email)  # or use request.user.username
    s3_file_path = f"Blockhouse/app/{user_folder}/{upload.file_name}"
    obj = s3.get_object(Bucket=settings.AWS_STORAGE_BUCKET, Key=s3_file_path)
    file_content = obj['Body'].read().decode('utf-8')
    df = pd.read_csv(StringIO(file_content))
    return df
    

def preprocess_data(df, platform):
    trade_blotter = data_fetching_and_preprocessing.preprocess_by_platform(df, platform)
    trade_blotter = reportCalculation.preprocess_data(trade_blotter)
    tickers = trade_blotter['Instrument'].unique()
    data_dict, available_tickers = data_fetching_and_preprocessing.fetch_market_data(tickers)
    trade_blotter = trade_blotter[trade_blotter['Instrument'].isin(available_tickers)]
    trade_blotter = data_fetching_and_preprocessing.preprocess_data(trade_blotter, data_dict)
    return trade_blotter, tickers, data_dict

def preprocess_data_merged(df, platform):
    trade_blotter = data_fetching_and_preprocessing.preprocess_by_platform(df, platform)
    tickers = trade_blotter['Instrument'].unique()
    trade_blotter, data_dict = data_fetching_and_preprocessing.preprocess_data_merged(trade_blotter)
    return trade_blotter, tickers, data_dict

#This code will remove rows where the instrument appears only once or where the activity date corresponding to the instrument appears only once.
def filter_tickers_for_line_charts(trade_blotter):

    instrument_unique_dates = trade_blotter.groupby('Instrument')['Activity Date'].nunique()
    instruments_to_keep = instrument_unique_dates[instrument_unique_dates > 1].index
    filtered_df = trade_blotter[trade_blotter['Instrument'].isin(instruments_to_keep)]

    return filtered_df

def convert_nan_to_null(data):
    """_summary_
    Convert NaN values to None in a JSON-serializable data structure
    
    Args:
      data (dict): The data structure to convert
      
    Returns:
      dict: The data structure with NaN values replaced by None
    """
    data = convert_timestamps(data)
    json_str = json.dumps(data)
    cleaned_json_str = re.sub(r'\bNaN\b', 'null', json_str)
    return json.loads(cleaned_json_str)

def convert_timestamps(obj):
    """_summary_
    Convert pandas Timestamp objects to ISO 8601 strings in a JSON-serializable data structure

    Args:
      obj (dict): The data structure to convert

    Returns:
      dict: The data structure with Timestamp objects converted to ISO 8601 strings
    """
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: convert_timestamps(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_timestamps(i) for i in obj]
    return obj
  
@csrf_exempt
# @permission_classes([IsAuthenticated])
def hoodwinked_get_initial_metrics(request):
    try:
        user_email = get_user_email_from_token(request)
        
        uploads = UploadHoodWinked.objects.filter(user_email=user_email).values()
        
        if not uploads:
            return JsonResponse({'last_trade_value': None, 'metric2': None, 'metric3': None})
            #return JsonResponse({'error': 'No files found'}, status=404)
        
        latest_file = list(uploads)[-1]  
        file_id = latest_file.get('id')
        platform = latest_file.get('platform')
        
        
        cache_key = f"{platform}_{file_id}"
        df = cache.get(key=cache_key)
        trade_blotter = cache.get(key=f"{platform}_{file_id}_trade_blotter")
        scaling_factor_report = cache.get(key=f"{platform}_{file_id}_scaling_factor")
        #print(df)
        if df is None or trade_blotter is None or scaling_factor_report is None: 
            print('Not in Cache')
            df= fetch_file_from_s3(file_id)
            cache.set(key=cache_key, value=df, timeout=60*15)
            trade_blotter, tickers, data_dict = preprocess_data_merged(df, platform)
            cache.set(key=f"{platform}_{file_id}_trade_blotter", value=trade_blotter, timeout=60*15)
            trade_blotter_filtered = trade_blotter.copy()
            cache.set(key=f"{platform}_{file_id}_tickers", value=tickers, timeout=60*15)
            cache.set(key=f"{platform}_{file_id}_data_dict", value=data_dict, timeout=60*15)
            scaling_factor_report = reportCalculation.calculate_potential_savings(trade_blotter)['scaling_factor']
            cache.set(key=f"{platform}_{file_id}_scaling_factor", value=scaling_factor_report, timeout=60*15)
            
            ##Set cache for report calculation
            #reportCalculation.main(df, platform)
        else:
            print('In Cache')
            df = cache.get(key=cache_key)
            trade_blotter = cache.get(key=f"{platform}_{file_id}_trade_blotter")
            tickers = cache.get(key=f"{platform}_{file_id}_tickers")
            data_dict = cache.get(key=f"{platform}_{file_id}_data_dict")
            scaling_factor_report = cache.get(key=f"{platform}_{file_id}_scaling_factor")
            trade_blotter_filtered = trade_blotter.copy()
            
        # Calculate the value of the last trade
        trade_blotter_sorted = trade_blotter.sort_values(by='Activity Date', ascending=False)
        last_trade = trade_blotter_sorted.iloc[0]
        last_trade_value = last_trade['Price'] * last_trade['Quantity']
        
        
        # Get the most recent trade
        last_trade = trade_blotter_sorted.iloc[0]
        # Format the trade options
        trade_option = f"{last_trade.name}: {last_trade['Instrument']} {last_trade['Trans Code']} {last_trade['Quantity']} @ ${last_trade['Price']} on {last_trade['Activity Date']}"
        stock = last_trade['Instrument']
        slippage_bar = data_fetching_and_preprocessing.calculate_slippage_sums(trade_blotter_filtered, trade_option,hwoe_adjustment_factor=scaling_factor_report)
        metric2 = slippage_bar['HWOE']
        
        start_date = trade_blotter_filtered['Activity Date'].min()
        end_date = trade_blotter_filtered['Activity Date'].max()
        trade_blotter_filtered_line = trade_blotter.copy()
        slippage_over_time = data_fetching_and_preprocessing.plot_excess_returns(trade_blotter_filtered_line, stock, show_open=True, show_close=True, show_twap=True, show_vwap=True, show_hwoe=True, start_date=start_date, end_date=end_date,hwoe_adjustment_factor=scaling_factor_report,aggregate=True)
        metric3 = slippage_over_time['HWOE'][-1]['HWOE_Excess_Returns']

        
        return JsonResponse({'last_trade_value': last_trade_value, 'metric2': metric2, 'metric3': metric3})

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)
    except Exception as e:
        logger.error(f"Error fetching files: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
    
import requests 
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def process_pipeline_for_ticker(request):
    try:
        get_user_email_from_token(request)  # Verify token
        
        ticker = request.query_params.get('ticker')
        inventory = request.query_params.get('inventory')
        timeframe = request.query_params.get('timeframe')
        
        # Step 0: Validate the ticker using Polygon.io API
        polygon_url = f'https://api.polygon.io/v3/reference/tickers/{ticker}?'
        api_key = settings.POLYGON_API_KEY
        params = {
            'apiKey': api_key
        }

        try:
            polygon_response = requests.get(polygon_url, params=params)
            if polygon_response.status_code == 404:
                return JsonResponse({'error': 'Invalid ticker.'}, status=400)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching ticker data from Polygon.io: {e}")
            return JsonResponse({'error': 'Failed to validate ticker.'}, status=500)

        try:
            # fastapi_url = f"https://fastapi.blockhouse.app/run-pipeline/{ticker}&{inventory}&{timeframe}"
            # response = requests.get(fastapi_url)

            # if response.status_code == 200:
            #     results = response.json()
            #     # Further processing of results if needed
            #     print(f"Pipeline results for {ticker}: {results}")
            #     return JsonResponse(results)
            # else:
            #     response.raise_for_status()
            payload = {
                "ticker": ticker,
                "action": "sell",
                "inventory": int(inventory),
                "timeframe": int(timeframe)
            }
            results = get_inference_response(payload)
            print(f"Pipeline results for {ticker}: {results}")
            return JsonResponse({
                'ticker': ticker,
                'inventory': inventory,
                'results': results
            })
            # return JsonResponse(results, safe=False)

        except requests.exceptions.RequestException as e:
            # Log the error for further analysis
            print(f"Error fetching pipeline results from FastAPI: {e}")
            return JsonResponse({'error': f"Failed to fetch or process pipeline results for {ticker}."}, status=400)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)
        
        
        
        
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def process_pipeline_for_ticker_buy(request):
    try:
        get_user_email_from_token(request)  # Verify token
        
        ticker = request.query_params.get('ticker')
        inventory = request.query_params.get('inventory')
        timeframe = request.query_params.get('timeframe')
        
        # Step 0: Validate the ticker using Polygon.io API
        polygon_url = f'https://api.polygon.io/v3/reference/tickers/{ticker}?'
        api_key = settings.POLYGON_API_KEY
        params = {
            'apiKey': api_key
        }

        try:
            polygon_response = requests.get(polygon_url, params=params)
            if polygon_response.status_code == 404:
                return JsonResponse({'error': 'Invalid ticker.'}, status=400)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching ticker data from Polygon.io: {e}")
            return JsonResponse({'error': 'Failed to validate ticker.'}, status=500)

        try:
            # fastapi_url = f"https://fastapi.blockhouse.app/run-pipeline-buy/{ticker}&{inventory}&{timeframe}"
            # response = requests.get(fastapi_url)

            # if response.status_code == 200:
            #     results = response.json()
            #     # Further processing of results if needed
            #     print(f"Pipeline results for {ticker}: {results}")
            #     return JsonResponse(results)
            # else:
            #     response.raise_for_status()
            payload = {
                "ticker": ticker,
                "action": "buy",
                "inventory": int(inventory),
                "timeframe": int(timeframe)
            }
            results = get_inference_response(payload)
            print(f"Pipeline results for {ticker}: {results}")
            return JsonResponse({
                'ticker': ticker,
                'inventory': inventory,
                'results': results
            })
            # return JsonResponse(results, safe=False)

        except requests.exceptions.RequestException as e:
            # Log the error for further analysis
            print(f"Error fetching pipeline results from FastAPI: {e}")
            return JsonResponse({'error': f"Failed to fetch or process pipeline results for {ticker}."}, status=400)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)
        
        
def get_inference_response(payload):
    try:
        request_body = json.dumps(payload)
        # Create a low-level client representing Amazon SageMaker Runtime
        sagemaker_runtime = boto3.client(
            "sagemaker-runtime", 
            region_name=settings.AWS_REGION, 
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        # Make the prediction
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName='MainPackage-website-endpoint', 
            Body=request_body, 
            ContentType='application/json',
            # InferenceComponentName='adjusted-vwap-3-new12-inference-component'
        )
        # Decodes the response body and converts it into a JSON object:
        response_body = response['Body'].read().decode('utf-8')
        response_json = json.loads(response_body)
        return response_json
    except Exception as e:
        print(f"Error in get_inference_response: {str(e)}")
        # return None
        return JsonResponse({'error': f"Error in get_inference_response: {str(e)}"}, status=400)

@csrf_exempt
@api_view(['POST'])
# @permission_classes([IsAuthenticated])
def plaid_data_to_csv(request):
    try:
        user_email = get_user_email_from_token(request)
        
        # Extract json_data and user_email from the request body
        json_data = request.data.get('json_data')
        user_email = request.data.get('user_email')


        if not json_data or not user_email:
            return JsonResponse({'error': 'json_data and user_email are required.'}, status=400)

        if not isinstance(json_data, list) or len(json_data) == 0:
            return JsonResponse({'error': 'json_data must be a non-empty list.'}, status=400)

        # Generate CSV data
        output = StringIO()
        csv_writer = csv.writer(output)
        csv_writer.writerow(json_data[0].keys())
        for item in json_data:
            csv_writer.writerow(item.values())

        # Define user folder and file name
        user_folder = f"hoodwinked/plaid/{user_email}"
        timestamp = datetime.now().strftime('%Y%m%d')
        s3_file_name = f"PLAID_transactions-{timestamp}.csv"
        
        s3_file_path = f"{user_folder}/{s3_file_name}"

        # Upload CSV to S3
        s3 = boto3.client('s3',
                          aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                          region_name=settings.AWS_REGION)
        
        try:
            s3.put_object(Bucket=settings.AWS_STORAGE_BUCKET, Key=s3_file_path, Body=output.getvalue())
        except Exception as e:
            return JsonResponse({'error': f'Failed to upload CSV to S3: {str(e)}'}, status=500)

        return JsonResponse({'message': 'CSV file created and uploaded to S3 successfully.'})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=401)
