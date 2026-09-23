import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Fetch NVIDIA high-frequency minute data
ticker = "NVDA"
data = yf.download(ticker, period="1d", interval="1m")

# Prepare the data
data.reset_index(inplace=True)
data["Datetime"] = pd.to_datetime(data["Datetime"])
data.set_index("Datetime", inplace=True)
minute_close_prices = data["Close"]
minute_volume = data["Volume"]

# Simulate some trades
np.random.seed(42)
trade_signals = pd.DataFrame({
    "timestamp": minute_close_prices.index[::10],  # Every 10th minute
    "trade_size": np.random.choice([-100, 100, 200, -200], size=len(minute_close_prices[::10]))
})

# Define a market impact model
def market_impact(order_size, adv, gamma=0.4, eta=0.001, decay_factor=0.05, liquidity_factor=0.1):
    """
    A complex market impact model with non-linear impacts, time decay, and liquidity adjustment.
    """
    # Permanent impact scales quadratically with trade size
    permanent_impact = gamma * (abs(order_size) / adv) ** 2

    # Temporary impact with a time decay factor
    temporary_impact = eta * np.sign(order_size) * (1 - np.exp(-decay_factor * abs(order_size)))

    # Liquidity adjustment based on order size and ADV
    liquidity_adjustment = liquidity_factor * (abs(order_size) / adv)

    return permanent_impact, temporary_impact, liquidity_adjustment

# Simulate market impact
def simulate_market_impact(price_data, trade_signals, volume_data, impact_model):
    # Calculate Average Daily Volume (ADV)
    adv = volume_data.resample('D').sum().mean()
    impacted_prices = price_data.copy()
    transaction_cost = 0

    for _, trade in trade_signals.iterrows():
        timestamp = trade["timestamp"]
        order_size = trade["trade_size"]
        
        if timestamp not in impacted_prices.index:
            continue
        
        permanent_impact, temporary_impact, liquidity_adjustment = impact_model(order_size, adv)
        
        # Adjust current price (temporary impact with liquidity adjustment)
        impacted_prices.loc[timestamp] *= (1 + temporary_impact + liquidity_adjustment)
        
        # Adjust future prices (permanent impact)
        future_timestamps = impacted_prices.index[impacted_prices.index >= timestamp]
        impacted_prices.loc[future_timestamps] *= (1 + permanent_impact)

        transaction_cost += order_size * (impacted_prices.loc[timestamp]-price_data.loc[timestamp])
    
    return impacted_prices, transaction_cost

# Visualize results
models = {
    "Market Impact": market_impact
}

fig, ax = plt.subplots(figsize=(14, 7))

for model_name, impact_model in models.items():
    impacted_prices, transaction_cost = simulate_market_impact(data['Close'], trade_signals, data['Volume'], impact_model)
    ax.plot(data['Close'], label="Original Prices", alpha=0.7)
    ax.plot(impacted_prices, label=model_name, alpha=0.7)

ax.set_title("Market Impact Simulation with Complex Model")
ax.set_ylabel("Price")
ax.legend()

plt.xlabel("Time")
plt.tight_layout()
plt.show()

# Plot a single bar for total transaction cost
print("Total Transaction Cost is:", round(transaction_cost,2))
plt.figure(figsize=(8, 6))
plt.bar(["Total Transaction Cost"], [transaction_cost], color='blue', alpha=0.7, width=0.2)
plt.title("Total Transaction Cost")
plt.ylabel("Transaction Cost")
plt.tight_layout()
plt.show()

# Simulated observed price impacts for parameter estimation
def simulate_observed_impacts(price_data, trade_signals, adv):
    observed_impacts = []
    for _, trade in trade_signals.iterrows():
        timestamp = trade["timestamp"]
        order_size = trade["trade_size"]

        if timestamp not in price_data.index:
            continue
        
        # Observed price change (next price relative to the current)
        current_price = price_data.loc[timestamp]
        next_timestamp = price_data.index[price_data.index > timestamp].min()
        if next_timestamp is not None:
            next_price = price_data.loc[next_timestamp]
            observed_change = (next_price - current_price) / current_price
            observed_impacts.append((order_size, observed_change))
    return np.array(observed_impacts)

# Function to fit
def fit_market_impact(order_size, gamma, eta, decay_factor, liquidity_factor, adv):
    permanent_impact = gamma * (np.abs(order_size) / adv) ** 2
    temporary_impact = eta * np.sign(order_size) * (1 - np.exp(-decay_factor * np.abs(order_size)))
    liquidity_adjustment = liquidity_factor * (np.abs(order_size) / adv)
    return permanent_impact + temporary_impact + liquidity_adjustment

# Observed impacts (generated from trades)
adv = minute_volume.resample('D').sum().mean()  # Average daily volume
observed_impacts = simulate_observed_impacts(minute_close_prices, trade_signals, adv)

# Extract order sizes and observed price changes
order_sizes = observed_impacts[:, 0]
observed_changes = observed_impacts[:, 1]

# Fit the model to observed data
initial_guess = [0.4, 0.04, 0.05, 0.1]
params, covariance = curve_fit(
    lambda x, gamma, eta, decay_factor, liquidity_factor: fit_market_impact(x, gamma, eta, decay_factor, liquidity_factor, adv),
    order_sizes,
    observed_changes,
    p0=initial_guess
)

# Extract the fitted parameters
gamma_estimated, eta_estimated, decay_factor_estimated, liquidity_factor_estimated = params

print("Estimated Parameters:")
print(f"Gamma: {gamma_estimated}")
print(f"Eta: {eta_estimated}")
print(f"Decay Factor: {decay_factor_estimated}")
print(f"Liquidity Factor: {liquidity_factor_estimated}")