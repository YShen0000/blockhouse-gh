# About
This folder contains all the existing RL models created. 

## Requirements
* Need the anconda environment to run the code

## Installation
```
git clone https://github.com/Blockhouse-Repo/Blockhouse-ML.git -b prod
cd Blockhouse-ML
pip install -e .
conda install -c conda-forge ta-lib -y
```
---
## run prod
### For Equity Trading
*  **Sell**
```
from blockhouse_ml.ml_prod import run_equities_sell_inference
results = run_equities_sell_inference('AAPL',inventory=1000)
```
* **note** : wherever this function is called, add SellEquityModels, SellEquityMicroModels, and SellEquityData in that directory.

* **Buy**
```
from blockhouse_ml.ml_prod import run_equities_buy_inference
results = run_equities_buy_inference('AAPL',inventory=1000)
```
* **note** : wherever this function is called, add BuyEquityModels, BuyEquityMicroModels, and BuyEquityData in that directory.
* output is a list of trades
```
sample results : 
[{'step': 1,
  'timestamp': Timestamp('2024-08-23 09:30:00'),
  'order_type': 'Market',
  'volume': 3457,
  'limit_price': 224.88512245579287},
 {'step': 2,
  'timestamp': Timestamp('2024-08-23 10:19:00'),
  'order_type': 'Market',
  'volume': 2355,
  'limit_price': 224.48486758886006},]
```
## Building and Running Docker 
```
docker build -t blockhouse_ml:v1 .
docker run -it blockhouse_ml:v1 /bin/bash
```