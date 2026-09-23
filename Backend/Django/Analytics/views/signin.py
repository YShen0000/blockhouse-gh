from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken
from Analytics.models import User
from django.conf import settings
import jwt
import hashlib
import random
import string
from pymongo import MongoClient

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

# Convert bytes to Base62 string
def base62_encode(num):
    base62 = []
    while num:
        num, rem = divmod(num, 62)
        base62.append(BASE62[rem])
    return ''.join(reversed(base62))

# Generate a unique referral code
def generate_referral_code(user_id: str, length: int = 10):
    unique_input = user_id + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    hash_object = hashlib.sha256(unique_input.encode())
    hash_int = int.from_bytes(hash_object.digest(), 'big')
    referral_code = base62_encode(hash_int)[:length]
    return referral_code

@csrf_exempt
def signin(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Basic validation
        if not email or not password:
            return JsonResponse({'error': 'Missing email or password'}, status=400)

        try:
            # Retrieve user by email
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)

        # Authenticate user
        user = authenticate(username=user.username, password=password)

        if user is not None:
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return JsonResponse({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def get_referral_link(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return JsonResponse({'error': 'Authorization header missing'}, status=401)

    # Connect to the MongoDB database
    client = MongoClient(str(settings.MONGODB_CONNECTION_STRING))
    hoodwinkedTrades_db = client['HoodwinkedTrades']
   
    user_schema = hoodwinkedTrades_db['users']
    
    # get user_id from the email
    user_referrer = user_schema.find_one({'email': email})
    
    if user_referrer:
        user_referrer_id = str(user_referrer['_id'])
    else:
        return JsonResponse({'error': 'User not found'}, status=404)
        
    
    referral_schema = hoodwinkedTrades_db['Referral']
    # Check if the user_id exists in the database
    user_referrer_data = referral_schema.find_one({'user_id': user_referrer_id})

    if user_referrer_data:
        referral_code = user_referrer_data['referral_code']
    else:
        # Generate a new referral code
        referral_code = generate_referral_code(user_referrer_id)
        
        # Ensure uniqueness by checking the database
        while referral_schema.find_one({'referral_code': referral_code}):
            referral_code = generate_referral_code(user_referrer_id)
        
        referral_schema.insert_one({'user_id': user_referrer_id, 'user_email': email,'referral_code': referral_code, 'referral_score': 0, 'referral_clicks': 0,'reward': 0})

    return JsonResponse({'referral_code': referral_code})

def calculate_rewards(request):
    if request.method == 'GET':
        # Get the user's email and referral code from the request parameters
        email = request.GET.get('email')
        ref_code = request.GET.get('ref_code')
        if not email or not ref_code:
            return JsonResponse({'error': 'Missing fields'}, status=400)
        try:
            # Connect to MongoDB
            client = MongoClient(str(settings.MONGODB_CONNECTION_STRING))
            db = client['HoodwinkedTrades']
            # Access the necessary collections
            collection_referral = db['Referral']
            collection_referral_status = db['Referral Status']
            # Find the user by referral code
            document = collection_referral.find_one({'referral_code': ref_code})
            if document:
                user_id = document.get('user_id')
                # Calculate the number of referrals
                referral_count = collection_referral_status.count_documents({'user_id1': user_id})
                # Calculate the reward based on the number of referrals
                reward = calculate_reward(referral_count)
                # Update the reward field for the user in the referral collection
                collection_referral.update_one(
                    {'user_id': user_id},
                    {'$set': {'reward': reward}}
                )
                return JsonResponse({'message': 'Reward updated successfully', 'reward': reward}, status=200)
            else:
                return JsonResponse({'error': 'Referral code not found'}, status=400)
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
