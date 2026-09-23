import logging

from django.http import JsonResponse

from Analytics.models import Uploads, UploadBlockhouse

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes


logger = logging.getLogger(__name__)

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def files_list(request):
    try:
        user_email = request.query_params.get('user_email')
        account_type = request.query_params.get("account_type")
        print("user_email: ", user_email)
        print("Account Type: ", account_type)
        
        if account_type == "demo":
            uploads = UploadBlockhouse.objects.filter(user_email=user_email, account_type=account_type).values()
            return JsonResponse({'uploads': list(uploads), 'account_type': 'demo'})
        else:
            uploads = UploadBlockhouse.objects.filter(user_email=user_email).values()
            return JsonResponse({'uploads': list(uploads), 'account_type': 'app'})

    except Exception as e:
        logger.error(f"Error fetching files: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)