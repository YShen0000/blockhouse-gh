import boto3
from io import StringIO
import logging
import json
import pandas as pd

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from Analytics.models import Uploads, UploadBlockhouse, Trade
from datetime import datetime, timedelta
from Analytics.Engine.DataProcessing import DataCleaning
from Analytics.utils.timestamp_converter import convert_to_datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_file(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    files = request.FILES.getlist('files')  # Get multiple files

    if not files:
        return JsonResponse({'error': 'No files provided'}, status=400)

    s3 = boto3.client('s3',
                      aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                      region_name=settings.AWS_REGION)

    responses = []

    for file in files:
        try:
            user_folder = str(request.user.id)  # or use request.user.username
            s3_file_path = f"{user_folder}/{file.name}"

            s3.upload_fileobj(file, settings.AWS_STORAGE_BUCKET, s3_file_path)

            # obj = s3.get_object(
            #     Bucket=settings.AWS_STORAGE_BUCKET, Key=s3_file_path)
            # file_content = obj['Body'].read().decode('utf-8')

            # df = pd.read_csv(StringIO(file_content))

            # df = DataCleaning.clean_data(df)

            upload_record = Uploads.objects.create(
                user=request.user,
                file_name=file.name,
                file_size=file.size,
                file_path=f"https://analyticsv1.s3.amazonaws.com/{s3_file_path}"
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



@api_view(["POST"])
# @permission_classes([IsAuthenticated])
def blockhouse_upload_file(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    user_email = request.POST.get("user_email")
    account_type = request.POST.get("account_type")
    platform = request.POST.get("platform")

    # print("user_email: ", user_email)
    # print("account_type: ", account_type)

    files = request.FILES.getlist("files")  # Get multiple files

    if not files:
        return JsonResponse({"error": "No files provided"}, status=400)

    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

    responses = []

    for file in files:
        try:
            print("Inside the try block and now uploading....")
            # Determine the S3 folder based on user type (demo or regular Blockhouse user)
            if account_type == "demo":
                user_folder = f"Blockhouse/demo/{user_email}"
            elif account_type == "retail" or account_type == "pro" or account_type == "institutional":
                user_folder = f"Blockhouse/app/{user_email}"

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            s3_file_name = f"{timestamp}_{file.name}"
            s3_file_path = f"{user_folder}/{s3_file_name}"

            s3.upload_fileobj(file, settings.AWS_STORAGE_BUCKET, s3_file_path)

            upload_record = UploadBlockhouse.objects.create(
                user_email=user_email,
                account_type=account_type,
                file_name=s3_file_name,
                file_size=file.size,
                file_path=f"https://analyticsv1.s3.amazonaws.com/{s3_file_path}",
                platform=platform
            )

            responses.append({"message": f"File {file.name} uploaded successfully"})
        except Exception as e:
            logger.error(
                f"Error uploading file {file.name} to S3: {str(e)}", exc_info=True
            )
            responses.append({"error": str(e), "file": file.name})

    return JsonResponse({"responses": responses})