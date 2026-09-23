
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import json
import logging

from openai import OpenAI

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_chat_message(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    try:
        assistant_id = data.get('assistantId')
        thread_id = data.get('threadId')
        message = data.get('message')

        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user", content=message
        )

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
        )

        return JsonResponse({"run_id": run.id, "status": "in_progress"}, status=201)
    except Exception as e:
        return JsonResponse({'error': e}, status=400)