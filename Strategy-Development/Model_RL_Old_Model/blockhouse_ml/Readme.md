# About
This folder contains all the scripts for ML model inferencing and development -- Website Implementation
All the scripts are modules and can be imported for your use case.
It follows a modular approach with emphasis on re-usability. These data fetching scripts as well as foreacasting scripts can be re-used again and again.

## Structure:
1. Equities: This contains separate modules for Buy, Sell and Utils.
Buy - scripts for buy side model
Sell - scripts for sell side model
Utils - generic scripts for data manipulation

2. Options: This is a work in progress and all future Options implementations will go in here.
It has Utils module which has the environment for the model to run on as well as data handling modules

## Run Model
### For Equity Trading
*  **Sell**
```
from blockhouse_ml.ml_prod import run_equities_inference
results = run_equities_inference('AAPL',inventory=1000, action='sell')
```
* **Note** : Wherever this function is called, add SellEquityModels, SellEquityMicroModels, and SellEquityData in that directory.

* **Buy**
```
from blockhouse_ml.ml_prod import run_equities_inference
results = run_equities_inference('AAPL',inventory=1000, action='buy')
```
* **Note** : Wherever this function is called, add BuyEquityModels, BuyEquityMicroModels, and BuyEquityData in that directory.
* Output is a list of trades
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
