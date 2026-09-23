import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from openai import OpenAI

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_messages(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    try:
        thread_id = data.get('threadId')
        run_id = data.get('runId')

        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run_id)

        run_status = run.status

        if run_status == "completed":
            api_messages = client.beta.threads.messages.list(
                thread_id=thread_id, order="asc")

            messages = [{
                'message': msg.content[0].text.value,
                'sender': msg.role,
            } for msg in api_messages]

            return JsonResponse({"status": "completed", 'messages': messages})
        else:
            return JsonResponse({"status": run_status})
    except Exception as e:
        return JsonResponse({'error': e}, status=400)