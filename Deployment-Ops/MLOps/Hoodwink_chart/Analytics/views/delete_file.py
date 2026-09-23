import boto3
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from Analytics.models import Uploads, Trade, UploadHoodWinked

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes


logger = logging.getLogger(__name__)


@csrf_exempt
def delete_file(request):
    if request.method == 'POST':

        try:
            data = json.loads(request.body)
            file_id = data.get('file_id')

            if not file_id:
                return JsonResponse({'error': 'No file ID provided'}, status=400)

            # upload = Uploads.objects.get(id=file_id)
            upload = UploadHoodWinked.objects.get(id=file_id) # that should be Uploads for demo but figure out it later

            # Trade.objects.filter(file=upload).delete()

            s3 = boto3.client('s3',
                              aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                              region_name=settings.AWS_REGION)

            s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET,
                             Key=upload.file_name)

            upload.delete()

            return JsonResponse({'message': 'File deleted successfully'})

        except Exception as e:
            logger.error(
                f"Error deleting file from S3: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)