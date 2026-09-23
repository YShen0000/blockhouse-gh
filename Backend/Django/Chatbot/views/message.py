from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from enum import Enum
import json
from rest_framework.decorators import api_view, permission_classes
import logging
from Chatbot.Functions.utils.default_start_end_dates import default_start_end_dates
from Chatbot.Pinecone.PineconeDriver import PineconeDriver
import Chatbot.Functions as functions
from Chatbot.OpenAI import parse_query, format_query

# Set up logging
logger = logging.getLogger("django")

driver = PineconeDriver(settings.PINECONE_API_KEY,
                        settings.PINECONE_INDEX_NAME, settings.PINECONE_ENVIRONMENT)


class FunctionName(Enum):
    # EXECUTION_QUALITY_ANALYSIS = "execution_quality_analysis"
    # COUNTERPARTY_PERFORMANCE = "counterparty_performance"
    # TRANSACTION_COST_ANALYSIS = "transaction_cost_analysis"
    # VOLUME_WEIGHTED_AVERAGE_PRICE = "volume_weighted_average_price"
    # LIQUIDITY_PROFILE_OVER_TIME = "liquidity_profile_over_time"
    # TRADE_SIZE_OPTIMIZATION = "trade_size_optimization"
    # POST_TRADE_ANALYSIS_BY_ASSET_CLASS = "post_trade_analysis_by_asset_class"
    # DURATION_ANALYSIS = "duration_analysis"
    # RISK_ADJUSTED_METRICS = "risk_adjusted_metrics"
    ANALYZE_SIMILAR_TRADES = "analyze_similar_trades"
    ANALYZE_TRADES_VWAP = "analyze_trades_vwap"
    CALCULATE_TCA_METRICS = "calculate_tca_metrics"
    LIQUIDITY_OVER_TIME = "liquidity_over_time"
    POST_TRADE_ANALYTICS = "post_trade_analytics"
    RISK_ADJUSTED_PERFORMANCE_METRICS = "risk_adjusted_performance_metrics"
    TRADE_SIZE_VS_EXECUTION_PERFORMANCE = "trade_size_vs_execution_performance"
    TRADE_VS_TRACE = "trade_vs_trace"
    CALCULATE_SLIPPAGE = "calculate_slippage"
    COUNTERPARTY_PERFORMANCE = "counterparty_performance"

    # Charts
    TRADE_VS_SIMILAR_SECURITIES = "trade_vs_similar_securities"
    POST_TRADE_BY_CLASS = "post_trade_by_class"
    TRADE_PRICES_VS_VWAP = "trade_prices_vs_vwap"
    PRICE_IMPACT_TRADE_COMPLETENESS = "price_impact_trade_completeness"
    BID_ASK_SPREAD = "bid_ask_spread"
    TCA_METRICS_CHART = "tca_metrics_chart"
    TRADE_VS_TRACE_CHART = "trade_vs_trace_chart"
    CALCULATE_SLIPPAGE_CHART = "calculate_slippage_chart"


@csrf_exempt
@api_view(['POST'])
def message(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON error: {e}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    file_id = data.get('file_id')
    message = data.get('message', '')

    if not file_id:
        logger.warning("No file ID provided in request")
        return JsonResponse({'error': 'No file ID provided'}, status=400)

    if not message:
        logger.warning("No message provided in request")
        return JsonResponse({'error': 'No message provided'}, status=400)
    logger.info(f"Received message: {message}")

    try:
        # TODO redo filter and intent parsing, remove date hardcode
        # Parse the query
        # parsed_query, start_date, end_date = parse_query(message)

        # if not parsed_query:
        #     logger.info("Failed to parse query")
        #     return JsonResponse({'error': "Failed to parse query"}, status=400)

        vector_match = driver.query(message, top_k=1)

        score = vector_match.matches[0].score
        logger.info(f"Message: {message}, Score: {score}")
        if score < 0.3:
            logger.info("Low score for vector match, returning default response")
            response = format_query(message, "")
            response_obj = [{
                "type": "text",
                "data": response,
                "sender": "assistant"
            }]

            return JsonResponse({"data": response_obj})

        response = None
        response_type = "text"
        fallback_message = "I'm sorry, I don't understand that. Please try again."

        try:
            # Convert string to FunctionName enum
            function_enum = FunctionName(vector_match.matches[0].id)
        except ValueError as e:
            logger.error(f"ValueError in converting string to FunctionName enum: {e}")
            response_obj = [{
                "type": "text",
                "message": response if response else fallback_message,
                "sender": "assistant"
            }]
            return JsonResponse({'data': response_obj})

        # Function execution based on enum
        function_map = {
            FunctionName.ANALYZE_SIMILAR_TRADES: functions.analyze_similar_trades,
            FunctionName.ANALYZE_TRADES_VWAP: functions.analyze_trades_vwap,
            FunctionName.CALCULATE_TCA_METRICS: functions.calculate_tca_metrics,
            FunctionName.LIQUIDITY_OVER_TIME: functions.liquidity_over_time,
            FunctionName.POST_TRADE_ANALYTICS: functions.post_trade_analytics,
            FunctionName.RISK_ADJUSTED_PERFORMANCE_METRICS: functions.risk_adjusted_performance_metrics,
            FunctionName.TRADE_SIZE_VS_EXECUTION_PERFORMANCE: functions.trade_size_vs_execution_performance,
            FunctionName.TRADE_VS_TRACE: functions.trade_vs_trace,
            FunctionName.CALCULATE_SLIPPAGE: functions.calculate_slippage,
            FunctionName.COUNTERPARTY_PERFORMANCE: functions.counterparty_performance,
            FunctionName.TRADE_VS_SIMILAR_SECURITIES: functions.trade_vs_similar_securities,
            FunctionName.POST_TRADE_BY_CLASS: functions.post_trade_by_class,
            FunctionName.TRADE_PRICES_VS_VWAP: functions.trade_prices_vs_vwap,
            FunctionName.PRICE_IMPACT_TRADE_COMPLETENESS: functions.price_impact_trade_completeness,
            FunctionName.BID_ASK_SPREAD: functions.bid_ask_spread,
            FunctionName.TCA_METRICS_CHART: functions.tca_metrics_chart,
            FunctionName.TRADE_VS_TRACE_CHART: functions.trade_vs_trace_chart,
            FunctionName.CALCULATE_SLIPPAGE_CHART: functions.calculate_slippage_chart,
        }
        response_function = function_map.get(function_enum)
        if response_function:
            start_date, end_date = default_start_end_dates()
            logger.info(f"Executing function: {function_enum} with file_id: {file_id}, start_date: {start_date}, end_date: {end_date}")
            response = response_function(file_id, start_date, end_date)
        else:
            response = None
        if not response:
            logger.info("No matching function found for the query")
            return JsonResponse({'error': 'No matching query found'}, status=400)

        response_message = format_query(message, response)

        message = {
            "type": response_type,
            "data": response_message,
            "sender": "assistant"
        }

        response_obj = [response, message]
        logger.info(f"Response: {response_obj}")
        return JsonResponse({"data": response_obj})

    except Exception as e:
        logger.exception(f"Unhandled exception in message view: {e}")
        errorMessage = [{
            "type": "text",
            "data": "I didn't quite catch that, do you mind typing it again?",
            "sender": "assistant"
        }]
        return JsonResponse({"data": errorMessage})
