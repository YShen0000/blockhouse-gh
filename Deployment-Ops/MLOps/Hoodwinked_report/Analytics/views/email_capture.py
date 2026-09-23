from django.http import JsonResponse
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt

import json
import requests
import os

HUBSPOT_APP_TOKEN = os.getenv('HUBSPOT_APP_TOKEN')



def send_to_hubspot(email):

    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {HUBSPOT_APP_TOKEN}"
    }
    payload = json.dumps({
        "properties": {
            "email": email,
        }
    })
    try:
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 201:
            print("Contact created successfully in HubSpot.")
        else:
            print(f"Failed to create contact in HubSpot. Status Code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

# Call the function after capturing the email


@api_view(["POST"])
@csrf_exempt
def email_capture(request):
    print("email_capture")
    try:
        email = request.POST.get('email')
        print(f"Received email: {email}")
        if not email:
            return JsonResponse({'error': 'Email is required'}, status=400)
        send_to_hubspot(email)
        return JsonResponse({'message': 'Email received successfully'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
