from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
import json

import Chatbot.Functions as functions


@csrf_exempt
@api_view(['POST'])
def test(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    file_id = data.get('file_id')
    # message = data.get('message', '')
    function_name = data.get('function_name')

    start_date = data.get('start_date', None)
    end_date = data.get('end_date', None)

    if not file_id:
        return JsonResponse({'error': 'No file ID provided'}, status=400)

    # if not message:
    #     return JsonResponse({'error': 'No message provided'}, status=400)

    if not function_name:
        return JsonResponse({'error': 'No function provided'}, status=400)

    if function_name == 'calculate_tca_metrics':
        try:
            response = functions.calculate_tca_metrics(
                file_id, start_date, end_date)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    elif function_name == 'analyze_trades_vwap':
        try:
            response = functions.analyze_trades_vwap(
                file_id, start_date, end_date)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    elif function_name == 'trade_vs_trace':
        try:
            response = functions.trade_vs_trace(file_id, start_date, end_date)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    elif function_name == 'liquidity_over_time':
        try:
            response = functions.liquidity_over_time(
                file_id, start_date, end_date)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    elif function_name == 'trade_size_vs_execution_performance':
        try:
            response = functions.trade_size_vs_execution_performance(
                file_id, start_date, end_date)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    elif function_name == 'post_trade_analytics':
        try:
            response = functions.post_trade_analytics(
                file_id, start_date, end_date)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    elif function_name == 'risk_adjusted_performance_metrics':
        try:
            response = functions.risk_adjusted_performance_metrics(
                file_id, start_date, end_date)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid function provided'}, status=400)

    return JsonResponse({"data": response})
