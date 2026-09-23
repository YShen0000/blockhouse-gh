from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

@csrf_exempt
@api_view(["POST"])
def init_chat(request):
    sample_conversations = [
        # Compliance
        [
            # Convo 1
            [
                [
                    "Compliance: Analyze Trader X's 10Y Apple bond trades against similar securities on TRACE over the last week. Please give the results in terms of spread to treasury (STT)",
                    """
                    We've analyzed TRACE records and found 3 securities with similar risk and liquidity profiles to measure your trades against.

                        1. Microsoft 5.2% 10Y (01-Jun-2039)
                        2. Alphabet 1.1% 10Y (15-Aug-2030)
                        3. Meta 3.9% 8Y (15-Aug-2032)

                        Using the 10Y treasury prices as a benchmark, we calculate the average spread to treasury for all security trades each day to evaluate the effectiveness of your execution strategies. Here's a summary of the findings:
                    """
                ]
            ]
        ],
        # Portfolio Manager
        [
            # Convo 1
            [
                [
                    "Portfolio Manager: My team has started trading on four electronic venues to buy corporate bonds: Bloomberg, Tradeweb, Trumid, and MarketAxess. Can you compare the quality of executions I am getting on these platforms over the last 1 year? Please give me the results grouped by asset class and venue."

                ],
                [
                    "How do you recommend I trade on these electronic platforms in the future to improve my executions?"
                ],
                [
                    "Please compare the slippage I'm incurring on RFQ trades across all of my electronic venues"
                ],
                ["Yes, please do"],
            ]
        ],
        # Trader
        [
            # Convo 1
            [
                [
                    "Trader: Yesterday I executed a portfolio trade on some investment grade JPM bonds. Did I get a good deal?"
                ],
                [
                    "Can you show me a bar chart comparing my executed prices to estimated market prices of each of the securities side by side?"
                ],
                ["How do I improve my slippage on my portfolio trades?"],
                ["Yes, please do"],
            ]
        ],
    ]
    response_obj = {}
    first_questions = [
        convo[0][0] for category in sample_conversations for convo in category
    ]
    response_obj["responses"] = first_questions
    return JsonResponse({"data": response_obj})



