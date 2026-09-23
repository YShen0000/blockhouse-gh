# Stock Data Analysis and Feature Extraction 
This project provides several advanced financial analysis features for analyzing stock data fetched from Yahoo Finance. The available features include detection of structural breaks, trade classification, Fibonacci retracement levels, and other key financial metrics.

## Features
### 1. Fetch Stock Data
> Function: fetch_data() \
> Description: Fetches historical stock data from Yahoo Finance using the provided ticker symbol and date range. It computes the log of adjusted closing prices and calculates daily log returns.

### 2. CUSUM Detection
> Function: apply_cusum()\
> Description: Applies the CUSUM (Cumulative Sum) algorithm to detect structural breaks in stock price returns. This method flags significant changes in the log returns based on a specified threshold.
### 3. Structural Break Detection
> Function: detect_breakpoints() \
> Description: Detects structural breaks in stock prices using the ruptures library. The PELT algorithm identifies points in the log stock price time series where significant breaks occur.
### 4. Rolling SADF (Supremum Augmented Dickey-Fuller)
> Function: rolling_sadf() \
> Description: Calculates the SADF statistic on a rolling window. The SADF test helps in detecting explosive behaviors or bubbles in time series data.
### 5. Lorentzian Classifier
> Function: apply_lorentzian_classifier() \
> Description: Classifies stock price movements using Lorentzian distance and nearest neighbors. It predicts the next price direction based on the nearest historical patterns.
### 6. Fibonacci Retracement and Extensions
> Function: apply_fibonacci_alpha_factors() \
> Description: Calculates Fibonacci retracement levels and extensions based on historical highs and lows. These levels help in identifying potential support and resistance levels.
### 7. Corwin-Schultz Spread Estimator
> Function: corwin_schultz() \
> Description: Estimates the bid-ask spread using the Corwin-Schultz model. This model uses daily high and low prices to measure liquidity and trading costs.
### 8. Volume-Synchronized Probability of Informed Trading (VPIN)
> Function: compute_vpin() & plot_vpin() \
> Description: Computes and plots the VPIN metric, which measures the probability of informed trading based on trade volume imbalance. It helps assess market liquidity and the likelihood of informed trading.
### 9. Trade Classification
> Function: classify_trades() \
> Description: Classifies trades as buy or sell based on price changes relative to the mid-price (calculated from the adjusted close). It assigns a trade sign (+1 for buy, -1 for sell) to each trade.
### 10. Volume Bars
> Function: get_volume_bars() \
> Description: Groups stock data into volume-based bars, which provide a better representation of market activity. Each volume bar aggregates data until a set volume threshold is reached, allowing for a more consistent comparison of periods with varying trading volumes.
### 11. Rolling_volatility_20 days
> Function: calculate_rolling_volatility() \
> This feature calculates the rolling volatility over a 20-day window using the top five bid and ask prices. It provides a measure of price fluctuation over time, which is essential for assessing market uncertainty and potential trading opportunities. Volatility is calculated as the standard deviation of the mid-price (average of best bid and ask) within the rolling window.

### 12. Big_event_indicator
> Function: big_event_indicator() \
> A binary feature that indicates whether a significant market event (like an economic announcement or central bank decision) has occurred within a specified time window. The feature is derived from external datasets tracking major events and used to adjust trading strategies around high-impact periods.
