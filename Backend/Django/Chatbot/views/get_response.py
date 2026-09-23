from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from Chatbot.Functions import (
    analyze_similar_trades,
    trade_vs_similar_securities,
    execution_compliance,
    execution_quality_by_asset_class,
    execution_quality_by_volume,
    slippage_by_venue,
    notional_value_analysis,
)

from Chatbot.Functions.charts.execution_price_chart import execution_price_chart

conversations = {
    "compliance": [
        [
            "Analyze Trader X's 10Y Apple bond trades against similar securities on TRACE over the last week. Please give the results in terms of spread to treasury (STT)",
            """We've analyzed TRACE records and found 3 securities with similar risk and liquidity profiles to measure your trades against.

1. Microsoft 5.2% 10Y (01-Jun-2039)
2. Alphabet 1.1% 10Y (15-Aug-2030)
3. Meta 3.9% 8Y (15-Aug-2032)

Using the 10Y treasury prices as a benchmark, we calculate the average spread to treasury for all security trades each day to evaluate the effectiveness of your execution strategies. Here's a summary of the findings:
""",
            """Here's the updated table with values in basis points:""",
            analyze_similar_trades,
            """The table shows a consistent downward trend in the spread to Treasury (STT) for all securities, including your Apple bond trades. Over the week, your average spread to Treasury decreased from 120 bips to 90 bips, indicating an improving position relative to the 2Y Treasury prices. Similarly, Microsoft, Alphabet, and Meta securities also show a decreasing trend in their spreads to Treasury. This trend could suggest a general market movement towards a more favorable view of these tech companies' bonds or a decrease in perceived risk compared to Treasury securities.
""",
        ],
        [
            "Could you plot a line chart showing the spread to treasury (STT) between our trader's trades and similar market securities for the last week?",
            """Here's the line chart showing the comparison of the average spread to Treasury for your trades and similar market securities (Microsoft, Alphabet, and Meta) over the last week. The chart illustrates the downward trend for all, indicating an improvement in their positions relative to the 2Y Treasury prices.
""",
            trade_vs_similar_securities,
        ],
        [
            "Is Trader X filling best execution requirements? What percentage of the trades do not meet these requirements?",
            """Based on the trades I have analyzed for Trader X over the last 1 year, trader X is filling their best execution requirements for 89% of their trades. Here are a few instances where they are not meeting this requirement:
""",
            execution_compliance,
        ],
        [
            "Are there any trends in these trades that we can use to improve our performance??",
            """Upon conducting further analysis, it appears that these trades are all large bloc trades performed with a singular counterparty, Citibank. In the future, we recommend that Trader X split these trades into smaller blocs of ~$25 million in notional and distribute these transactions among your existing electronic venues, Bloomberg, MarketAxess, and Tradeweb. Would you like to backtest and simulate the performance of this strategy to understand impact on execution quality?
""",
        ],
        [
            "Yes, please do",
            """Please reach out to the Blockhouse team to see how we can implement this tool for your use cases, thank you for viewing our demo conversation!
""",
        ],
    ],
    "portfolio_manager": [
        [
            "My team has started trading on four electronic venues to buy corporate bonds: Bloomberg, Tradeweb, Trumid, and MarketAxess. Can you compare the quality of executions I am getting on these platforms over the last 1 year? Please give me the results grouped by asset class and venue.",
            """Certainly, lets break down the weighted average slippage per trade on each of these exchanges by asset class as well as trade size. The reference price for slippage is calculated using Bayesian inference on similar securities as well as taking into account the market liquidity (days since last trade, days since issuance, etc.) for the specific CUSIPs traded. The weighted average component of the slippage per trade is takes into account slippage values scaled by total notional amount of the trade. Slippage values are calculated in basis points (0.01%).
""",
            execution_quality_by_asset_class,
            execution_quality_by_volume,
        ],
        [
            "How do you recommend I trade on these electronic platforms in the future to improve my executions?",
            """There are three areas in which we can provide recommendations to improve your performance:

1. Comparing aggregate slippage by each trading protocol on each venue to determine the most cost effective protocol (by venue)
2. Comparing the transaction costs of similar / comparable trading protocols across venues to determine which determine which venue is the cheapest
3. Optimizing order size and timing on each venue individually, determine how to improve trading performance on all traded venues individually

Which type of analysis should we proceed to conduct?
""",
        ],
        [
            "Please compare the slippage I'm incurring on RFQ trades across all of my electronic venues",
            """Certainly, first we analyze the weighted average slippage for all RFQ trades on each venue and provide a breakdown of the percentage of total trading volume on each venue by the RFQ protocol.
""",
            slippage_by_venue,
            """Based on this analysis, we recommend that you reduce your notional RFQ trades on Bloomberg and Tradweb and increase your notional RFQ trades on Trumid and Marketaxess. Would you like to backtest these results in a simulated environment to determine specific percentages of notional amounts to decrease / increase in order to optimize RFQ slippage?
""",
        ],
        [
            "Yes, please do",
            """Please reach out to the Blockhouse team to see how we can implement this tool for your use cases, thank you for viewing our demo conversation!
""",
        ],
    ],
    "trader_bonds": [
        [
            "Yesterday I executed a portfolio trade on some investment grade JPM bonds. Did I get a good deal?",
            """I see, let's conduct a thorough analysis of your portfolio trade and measure the entire execution on a bond-by-bond basis. Yesterday, you traded the following bonds at 13:30:00 EST
""",
            notional_value_analysis,
            """The aggregate price you received for the portfolio trade was $26.21 million. The weighted average price per security was $97.88. Based on our estimates of previous trades, market volatility, and the liquidity of each individual securities at the time of the trade, you paid an average of 8.7% higher than the market price on a per bond basis.""",
        ],
        [
            "Can you show me a bar chart comparing my executed prices to estimated market prices of each of the securities side by side",
            """Sure, here is the side by side bar chart showing the estimated execution prices per bond as a side by side bar graph, with a trend line displaying the weighted average security trade price as a reference.
""",
            execution_price_chart,
        ],
        [
            "How do I improve my slippage on my portfolio trades?",
            """Based on analysis of your trade, there are two factors you can manipulate to improve your performance: timing and size. We noticed that you conducted the trade at 13:30:00 EST on Monday, which is in the afternoon. In the future, we recommend conducting the trade between the hours of 9:30:00 - 12:30:00 EST on Mondays or Fridays to get the maximum liquidity. We also recommend breaking down your trade into two blocs of less than $10 million notional within 30 minutes of each other to to reduce the price impact of your trade. Would you like to backtest these results in a simulated environment to analyze the execution improvement of this strategy?
""",
        ],
        [
            "Yes, please do",
            """Please reach out to the Blockhouse team to see how we can implement this tool for your use cases, thank you for viewing our demo conversation!""",
        ],
    ],
    "trader_crypto": [
        [
            "I did some BTC momentum trading yesterday using RSI as my entry and exit signals. I bought when RSI fell below 30 on Uniswap, and sold when RSI was above 70. How profitable was I on my trades?",
            """Analyzing your BTC trades yesterday, we break down your aggregate PnL as follows:

- Total Profit: $43,323.21 (10% returns)
- Network Fees: $230.31 — the cost of transaction on the blockchain level
- AMM Slippage: $5,671.19 — the slippage caused by AMM pricing structure
- Opportunity Costs:  $390.34 — BTC staking rewards for the same period of time
- Total PnL: $37031.37 (8.55% returns)

The sharpe and sortino ratio of your strategies were 1.55 and 0.99 respectively. Since BTC increased by 4.95% yesterday, your trading alpha was 3.6%.""",
        ], [
            "How can I improve the performance of my strategy in the future?",
            """There are three areas that you can explore to improve your future performance:

- Exploring transaction costs on different exchanges to determine cheapest venue
- Optimizing entry and exit signals on your RSI based trading strategy
- Modifying existing strategy to include different indicators and features

Which type of analysis should we proceed to conduct?"""
        ], [
            "I would like to explore some different indicators and stop losses to change my trading style with the same strategy",
            """Certainly, an alternative indicator that serves as a strong entry signal for momentum trading is a combination of the Moving Average Convergence Divergence (MACD) indicator and the Relative Strength Index (RSI). For example, you can enter a trade when the MACD line (the difference between the 12-day and 26-day exponential moving averages) crosses above the signal line (9-day EMA of the MACD line). This crossover indicates that momentum might be shifting upwards, potentially signaling a buying opportunity. If the RSI index simultaneously moves to your desired threshold, then you make a BUY or SELL. Would you like to backtest to find the optimal levels to set your MACD and RSI entry and exit signals?"""
        ], [
            "Yes, please do",
            """Please reach out to the Blockhouse team to see how we can implement this tool for your use cases, thank you for viewing our demo conversation!""",
        ],
    ],
}


@csrf_exempt
@api_view(["POST"])
def get_response(request):
    print(request.data)
    # user_question = request.data.get("message", "").strip()
    category = request.data.get("category", "").strip()
    question_index = request.data.get("question_index", 0)
    is_question = request.data.get("is_question", False)
    file_id = request.data.get("file_id", "")
    if is_question == True:
        response_text = conversations[category][question_index][0]
        sender = "user"
        return JsonResponse(
            {
                "data": [{"data": response_text, "sender": sender, "type": "text"}],
                "question_count": len(conversations[category]),
            }
        )

    else:
        responses = conversations[category][question_index][1:]

        response_data = []
        for text in responses:
            if isinstance(text, str):
                response_data.append(
                    {"data": text, "sender": "assistant", "type": "text"}
                )
            if callable(text):
                response_data.append(text(file_id))
        return JsonResponse(
            {"data": response_data, "question_count": len(conversations[category])}
        )
