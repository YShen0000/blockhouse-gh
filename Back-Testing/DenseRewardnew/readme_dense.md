# Optimal Trade Execution using Reinforcement Learning

This project implements a reinforcement learning (RL) based approach for optimal trade execution in financial markets. The system learns to execute large orders while minimizing market impact and transaction costs.

## Overview

The system uses a reinforcement learning agent to determine optimal trading strategies by learning from market microstructure data and order book information. The main components include:

- Trade execution environment (`TradingEnvironmentMacroV3`)
- Reinforcement learning model training and inference
- Market impact and transaction cost analysis
- TWAP (Time-Weighted Average Price) benchmark comparison

## Requirements

- Python 3.7+
- PyTorch
- Gym
- Pandas
- NumPy
- Scikit-learn
- numba

## Installation

```bash
pip install -r requirements.txt
```

## Data Structure

The system requires the following data:
- Market data with OHLCV (Open, High, Low, Close, Volume)
- Technical indicators (RSI, MACD, etc.)
- Order book data (5 levels)
- Market microstructure metrics
- Forecast data for various time horizons

## Usage

### 1. Data Preparation

```python
# Prepare and process the data
processed_data = get_data(data_dir, ticker, start_time, end_time)
train_data = processed_data[:int(len(processed_data) * 0.8)]
test_data = processed_data[int(len(processed_data) * 0.8):]
```

### 2. Model Training

```python
# Initialize the trader model
macro_trader = MacroTraderModel(MODEL_DIR)

# Train the model
model, env = macro_trader.train(
    train_data, 
    train_data_raw, 
    processed_train_data,
    preferred_timeframe=390,
    market_cap=market_cap,
    scenario=scenario,
    training_params=training_params,
    training_config=training_config
)
```

### 3. Testing and Evaluation

```python
# Test the model
rewards, tenv, model, infos = macro_trader.test_benchmark(
    test_data, 
    test_data_raw, 
    processed_test_data,
    preferred_timeframe=390,
    market_cap=market_cap,
    scenario=scenario
)

# Get trading results
trading_results = pd.DataFrame(tenv.trades)
```

## Configuration

### Training Parameters

```python
training_params = {
    'callback': None,
    'total_timesteps': 45000
}

training_config = {
    'learning_rate': 0.000001,
    'n_steps': 1024,
    'batch_size': 64,
    'gamma': 0.965901,
    'clip_range': 0.03,
    'n_epochs': 8,
    'ent_coef': 0.3,
    'use_sde': True,
    'verbose': 1
}
```

### Scenario Types

The system supports different trading scenarios based on order size:
- large
- medium-large
- medium
- small-medium
- small

## Environment State Space

The trading environment includes various market features:
- Price data (OHLCV)
- Technical indicators (RSI, MACD, Bollinger Bands, etc.)
- Market microstructure metrics
- Order book data
- Forecasted values
- Inventory information
- Time remaining

## Performance Metrics

The system tracks several performance metrics:
- Implementation Shortfall (IS)
- Slippage
- Transaction costs
- TWAP benchmark comparison
- Market impact
- Opportunity cost

## Results Analysis

Results can be analyzed through:
```python
# Get trading results
results_df = pd.DataFrame(tenv.trades)

# Key metrics
slippage = results_df['IS'].sum()
transaction_costs = results_df['transaction_cost'].sum()
```

## Benchmarking

The system includes TWAP (Time-Weighted Average Price) benchmark comparison:
```python
# Run TWAP benchmark
twap_results = macro_trader.test_benchmark_twap(
    test_data, 
    test_data_raw, 
    processed_test_data,
    preferred_timeframe=timeframe,
    market_cap=market_cap,
    scenario=scenario
)
```

## Data Handling

The system implements a robust data pipeline for processing market data using the Databento API:

### Market Data Acquisition

```python
from data_handler_v2 import fetch_data, process_data

# Fetch market data
data_path = fetch_data(
    ticker="AAPL",
    start_date="2023-07-01",
    end_date="2023-10-31",
    data_dir="data"
)
```

### Data Pipeline Features

#### 1. Raw Data Collection
- Connects to NASDAQ ITCH data through Databento Historical API
- Captures market microstructure during trading hours (13:30-20:00 UTC)
- Filters for valid bid/ask quotes with non-zero sizes
- Removes cancelled orders (action != 'C')

#### 2. Data Aggregation
```python
def aggregate_to_minute(df):
    df['minute'] = df['timestamp'].dt.floor('min')
    # Aggregates to minute-level with top 5 price levels
    # Returns DataFrame with columns:
    # - timestamp
    # - bid_price_1 through bid_price_5
    # - bid_size_1 through bid_size_5
```

Key Features:
- Minute-level aggregation of tick data
- Maintains top 5 price levels for market depth
- Handles duplicate price levels
- Preserves timestamp information

#### 3. Data Processing
```python
processed_data = process_data(
    data=raw_data,
    name="AAPL",
    cols=["bid_size", "bid_price", "ask_price", "ask_size"],
    train=True
)
```

Processing Steps:
- Standardization of numerical features using sklearn's StandardScaler
- Persistent storage of scalers for consistent processing
- Addition of processed columns with prefix "processed_"

### Data Structure

The system works with the following data structure:

```python
# Raw tick data columns
tick_columns = [
    'timestamp',      # Nanosecond precision
    'bid_price',      # Best bid price
    'ask_price',      # Best ask price
    'bid_size',       # Best bid size
    'ask_size'        # Best ask size
]

# Aggregated minute data columns
minute_columns = [
    'timestamp',      # Minute timestamp
    'bid_price_1',    # Highest bid price
    'bid_price_2',    # Second highest bid price
    'bid_price_3',    # Third highest bid price
    'bid_price_4',    # Fourth highest bid price
    'bid_price_5',    # Fifth highest bid price
    'bid_size_1',     # Size at highest bid
    'bid_size_2',     # Size at second highest bid
    'bid_size_3',     # Size at third highest bid
    'bid_size_4',     # Size at fourth highest bid
    'bid_size_5'      # Size at fifth highest bid
]
```

### Usage Example

```python
# Full pipeline example
ticker = "AAPL"
start_date = "2023-07-01"
end_date = "2023-10-31"

# 1. Fetch raw data
data_path = fetch_data(
    ticker=ticker,
    start_date=start_date,
    end_date=end_date,
    data_dir="data"
)

# 2. Load and process data
raw_data = pd.read_csv(data_path)
processed_data = process_data(
    data=raw_data,
    name=ticker,
    cols=["bid_size", "bid_price", "ask_price", "ask_size"],
    train=True
)
```

[Reward System section and rest of the README remain the same]
## Reward System

The system implements a sophisticated multi-component reward function through the `TradingRewards` class:

### Reward Components

1. **TWAP Deviation (reward_1)**
   ```python
   reward = -abs(action - twap) / (0.4 * twap)
   ```
   Penalizes deviation from TWAP benchmark

2. **Implementation Shortfall Improvement (reward_2)**
   ```python
   if is_action > is_twap and action > twap:
       return 1
   return 0
   ```
   Rewards actions that improve implementation shortfall

3. **Market Impact Assessment (reward_3)**
   - Evaluates trading impact across different market conditions
   - Considers average implementation shortfall in various scenarios
   - Scales reward based on market impact assessment

4. **Optimal Execution Point (reward_4)**
   - Identifies and rewards optimal execution points
   - Considers implementation shortfall function derivatives
   - Provides additional rewards for optimal timing

5. **Conservative Execution (reward_5)**
   - Rewards conservative execution strategies
   - Considers minimum execution thresholds
   - Includes safety margins for execution prices

6. **Dynamic Market Response (reward_6)**
   - Evaluates market response to executions
   - Considers historical implementation shortfall trends
   - Adapts rewards based on market conditions

7. **Final Step Penalty (reward_7)**
   ```python
   reward = -40 * abs(action - twap) / twap
   ```
   Ensures completion of execution within constraints

### Reward Configuration

```python
rewards = TradingRewards()
total_reward = rewards.calculate_reward(
    action=executed_price,
    twap=twap_price,
    is_action=implementation_shortfall,
    is_twap=twap_shortfall,
    avg_plus_set=positive_impact_avg,
    avg_minus_set=negative_impact_avg,
    avg_normal_set=normal_impact_avg,
    is_func=shortfall_function,
    is_t=current_shortfall,
    is_t_minus_1=previous_shortfall,
    is_1=initial_shortfall,
    is_final_step=is_last_execution
)
```

[Rest of the README remains the same]
