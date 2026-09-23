from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from Analytics.models import User
from rest_framework.decorators import api_view
from pymongo import MongoClient
from django.conf import settings
from datetime import datetime
import jwt

@csrf_exempt
def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Basic validations
        if not username or not email or not password:
            return JsonResponse({'error': 'Missing fields'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists'}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email already exists'}, status=400)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        return JsonResponse({'message': 'User created successfully'}, status=201)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def update_referral(request):  # API for score / Referral Status DB
    if request.method == 'GET':
        # Get the email and ref_code from the query parameters
        user2_email = request.GET.get('email')
        ref_code = request.GET.get('ref_code')

        if not user2_email or not ref_code:
            return JsonResponse({'error': 'Missing fields'}, status=400)

        try:
            # Connect to MongoDB
            client = MongoClient(str(settings.MONGODB_CONNECTION_STRING))
            hoodwinkedTrades_db = client['HoodwinkedTrades']
            user_schema = hoodwinkedTrades_db['users']

            # Get user_id from the email
            user2 = user_schema.find_one({'email': user2_email})
            
            if user2:
                user2_id = str(user2['_id'])
            else:
                return JsonResponse({'error': 'User not found'}, status=404)
            
            # Update the referral status and increment score
            update_result = add_status_increment_score(user2_id, ref_code, user2_email)
            
            if update_result:
                return JsonResponse({'message': 'Referral updated successfully'}, status=200)
            else:
                return JsonResponse({'error': 'Update failed'}, status=400)
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


def add_status_increment_score(user2_id, ref_code, user2_email): #Add the referral (IF there is one) to the Referral Status DB
    client = MongoClient(str(settings.MONGODB_CONNECTION_STRING))
    hoodwinkedTrades_db = client['HoodwinkedTrades']

    
    referralStatus_schema = hoodwinkedTrades_db['Referral Status']

    #finding the user via referral code
    referral_schema = hoodwinkedTrades_db['Referral']
    user1_document = referral_schema.find_one({'referral_code': ref_code})
    if user1_document:
        user_referrer_id = user1_document.get('user_id')
        user_referrer_email = user1_document.get('user_email')
        

    if user1_document:  # Updating Score
        updated_values = referral_schema.find_one_and_update(
            {'user_id': user_referrer_id},
            {
                '$inc': {'referral_score': 1, 'referral_clicks': 1}
            },
            return_document=True
        )

        # Calculate reward based on the updated referral_score
        reward = calculate_reward(updated_values['referral_score'])

        # Updating reward in the database
        referral_schema.update_one(
            {'user_id': user_referrer_id},
            {
                '$set': {'reward': reward}
            }
        )

        # Implementing into status DB
        referralStatus_schema.insert_one({
            'user_id1': user_referrer_id,
            'user_id2': user2_id,
            'user1_email': user_referrer_email,
            'user2_email': user2_email,
            'date_time_of_signup' : datetime.now(),
            'timestamp': datetime.now(),
            'referral_score': updated_values['referral_score'],
            'referral_clicks': updated_values['referral_clicks'],
            'reward': reward
        })
        return True
    else:
        return False

    
    
def update_referral_clicks(request): 
    if request.method == 'GET':

        ref_code = request.GET.get('ref_code')

        if not ref_code:
            return JsonResponse({'error': 'Missing fields'}, status=400)

        try:
            # Connect to MongoDB
            client = MongoClient(str(settings.MONGODB_CONNECTION_STRING))
            hoodwinkedTrades_db = client['HoodwinkedTrades']
            
            
            referralStatus_schema = hoodwinkedTrades_db['Referral Status']
            referral_schema = hoodwinkedTrades_db['Referral']
            user1_document = referral_schema.find_one({'referral_code': ref_code})
            if user1_document:
                user_referrer_id = user1_document.get('user_id')
                user_referrer_email = user1_document.get('user_email')
            else:
                return JsonResponse({'error': 'User not found'}, status=404)
            
            if user1_document: # Updating Clicks
                referral_schema.update_one(
                    {'referral_code': ref_code},
                    {'$inc': {'referral_clicks': 1}}
                )
                
                referralStatus_schema.insert_one({
                    'user_id1': user_referrer_id,
                    'user1_email': user_referrer_email,
                    'timestamp': datetime.now(),
                    'referral_clicks': user1_document.get('referral_clicks'),
                    'referral_score': user1_document.get('referral_score'),
                    'reward': user1_document.get('reward'),
                    
                })
                return JsonResponse({'message': 'Clicks updated successfully'}, status=200)
            else:
                return JsonResponse({'error': 'Update failed'}, status=400)
                
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


def calculate_reward(score):
    if score >= 5000:
        return 50000
    elif score >= 1000:
        return 25000
    elif score >= 500:
        return 2500
    elif score >= 100:
        return 500
    elif score >= 50:
        return 250
    elif score >= 10:
        return 50
    else:
        return 0
