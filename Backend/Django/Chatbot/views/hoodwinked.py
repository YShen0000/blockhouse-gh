import boto3
from io import StringIO
import logging
import json
import pandas as pd
import numpy as np

from io import StringIO, BytesIO
import base64


from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from Analytics.models import Uploads, Trade, UploadHoodWinked
from Analytics.Engine.DataProcessing import DataCleaning
from Analytics.utils.timestamp_converter import convert_to_datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

from datetime import datetime, timedelta
from Analytics.utils import reportCalculation, testreports
from Analytics.utils import data_fetching_and_preprocessing



@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def hoodwinked_dynamic_chatbot(request):
    try:
        file_id = request.query_params.get('file_id')
        
        upload = UploadHoodWinked.objects.get(id=file_id)

        s3 = boto3.client('s3',
                            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                            region_name=settings.AWS_REGION)

        # s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET,
        #                     Key=upload.file_name)

        user_folder = str(upload.user_email)  # or use request.user.username
        s3_file_path = f"{user_folder}/{upload.file_name}"
        platform = upload.platform

        obj = s3.get_object(
                Bucket=settings.AWS_STORAGE_BUCKET, Key=s3_file_path)
        
        file_content = obj['Body'].read().decode('utf-8')

        df = pd.read_csv(StringIO(file_content))

        # Report Calculation
        report_calculation = reportCalculation.main(df, platform,file_id)

        # Generate Report
        # document_base64 = testreports.generate_report(report_calculation);
        # # return JsonResponse({'document': document_base64, 'message': 'Report generation successful'})
        # return document_base64

        # Convert numpy arrays, DataFrames, and BytesIO to JSON serializable types
        def convert_to_serializable(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, pd.DataFrame):
                return obj.to_dict(orient='records')
            elif isinstance(obj, BytesIO):
                return base64.b64encode(obj.getvalue()).decode('utf-8')
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(i) for i in obj]
            else:
                return obj
            
        report_calculation_converted = convert_to_serializable(report_calculation)


        return JsonResponse({'report_calculation': report_calculation_converted})

    except Exception as e:
        # logger.error(f"Error fetching files: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
    
