# Move each function into its own files and modify the arguments with variables like timestamps, cusips, etc!!

def execution_quality_analysis(message):
    '''
    query: Please analyze historical execution data to measure the quality of past trades in terms of slippage, price deviation, and trade completeness
    '''

    message = """The analysis of the historical execution data yielded the following measures for each trading day:

1. **Average Slippage**: The average difference between the trade price and the average daily price.
2. **Price Deviation**: The standard deviation of trade prices for each day.
3. **Trade Completeness**: The proportion of trades that were fully filled.

Here are the results for the first few trading days:

| Trade Date | Average Slippage | Price Deviation | Trade Completeness |
|------------|------------------|-----------------|--------------------|
| 2024-01-02 | ≈ 0              | 24.61           | 100%               |
| 2024-01-03 | ≈ 0              | 12.79           | 100%               |
| 2024-01-04 | ≈ 0              | 17.18           | 100%               |
| 2024-01-05 | ≈ 0              | 25.11           | 100%               |
| 2024-01-06 | ≈ 0              | 18.19           | 100%               |

The average slippage is close to zero for these days, indicating minimal deviation from the average daily price. The price deviation varies each day, reflecting the variability in trade prices. Trade completeness is 100%, indicating all trades were fully filled on these days.
"""

    return message


def counterparty_performance(message):

    message = """
The analysis of historical performance with different counterparties, focusing on price negotiation, execution speed, and reliability, yields the following results:


### Counterparty Performance Analysis
| Counterparty | Average Execution Time | Reliability (%) | Favorable Price Negotiation Rate (%) |
|--------------|------------------------|-----------------|--------------------------------------|
| Ban            | 12.95                  | 91.15           | 0.0                                  |
| Benjie       | 14.31                  | 88.59           | 0.0                                  |
| Bit                | 9.94                   | 93.26           | 0.0                                  |

- **Average Execution Time**: Represents the mean time taken to execute trades with each counterparty. 'Bit' has the lowest average execution time of 9.94.

- **Reliability**: Calculated as the percentage of trades that were fully executed ('Yes' in the 'Complete' field). 'Bit' leads in this category with 93.26% reliability.

- **Favorable Price Negotiation Rate**:  Shows the percentage of trades executed at a price more favorable than the market price. Surprisingly, all counterparties show a 0.0% rate, suggesting no trades were executed at a price better than the market price. This might need further investigation or could be due to the way trades are recorded or negotiated.

This analysis provides insights into the performance characteristics of each counterparty. Depending on the priority (speed, reliability, price), you can evaluate which counterparty aligns best with your trading objectives. If you need further analysis or specific queries, feel free to ask.

"""
    return message


# Todo: Implement the hardcoded message from ChatGPT
def transaction_cost_analysis(message):

    message = """
The analysis of transaction costs yields the following results:


### Transaction Cost Analysis

| Transaction Type | Cost (%) |
|------------------|----------|
| Market Price     | 0.0      |
| Limit Price      | 0.0      |


The transaction costs are 0% for all transactions.

This analysis provides insights into the costs associated with each transaction type.

"""

    return message

# Todo: Implement the hardcoded message from ChatGPT


def volume_weighted_average_price(message):

    message = """
The analysis of volume-weighted average price yields the following results:

***Insert results here***

"""
    return message

# Todo: Implement the hardcoded message from ChatGPT


def liquidity_profile_over_time(message):

    message = """

The analysis of liquidity profile over time yields the following results:

***Insert liquidity profile here***

"""
    return message


def trade_size_optimization(message):

    message = """
The impact of different trade sizes on execution performance is summarized as follows:



| Trade Size Range        | Slippage | Price Deviation | Trade Completeness |
|-------------------------|----------|-----------------|--------------------|
| 501,205 - 782,450       | 0.0606   | 0.0062%         | 84.10%             |
| 782,451 - 847,017       | 0.0295   | 0.0030%         | 89.22%             |
| 847,017 - 895,197       | 0.0204   | 0.0021%         | 94.05%             |
| 895,198 - 1,050,484     | 0.0150   | 0.0016%         | 95.42%             |
These results suggest that as the trade size increases, the slippage and price deviation tend to decrease, and trade completeness tends to increase

"""
    return message


# Todo: Implement the hardcoded message from ChatGPT
def post_trade_analysis_by_asset_class(message):

    message = """
The analysis of post-trade analysis by asset class yields the following results:

***Insert post trade analysis by asset class here***

"""
    return message


# Todo: Implement the hardcoded message from ChatGPT
def duration_analysis(message):

    message = """

The analysis of duration yields the following results:

***Insert duration analysis here***
"""
    return message


# Todo: Implement the hardcoded message from ChatGPT
def risk_adjusted_metrics(message):

    message = """

The analysis of risk adjusted metrics yields the following results:

***Insert risk adjusted metrics here
"""
    return message
