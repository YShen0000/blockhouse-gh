# Deployment Branch

This folder contains all the code and deployment scripts for the various endpoints created, including:
- **Blockhouse Report**
- **Hoodwinked Report**
- **Hoodwinked Charts**
- **Blockhouse Calculator**
- **Website**

## Requirements
* You will need the Anaconda environment to run the code and manage dependencies.

## Installation
To set up the environment and install necessary packages:

```bash
git clone https://github.com/Blockhouse-Repo/Blockhouse-ML.git -b deployment
cd Blockhouse-ML
pip install -e .
conda install -c conda-forge ta-lib -y
```
## Running the Endpoints
### 1. **ML-Pipeline(Website)**
This is the core trading report endpoint that allows you to run both buy and sell inferences.
####Endpoint for this:
```python
Endpoint name : endpoint-real-time-inference2424-new
Model Name : model-real-time-inference24-new-inference-component
```
For more details and deployment steps, refer to the [ML-Pipeline deployment_utils folder](./deployment_utils/).



### 2. **Blockhouse Report**
This is the core trading report endpoint that allows you to run both buy and sell inferences.
####Endpoint for this:
```python

Endpoint name : endpoint-real-time-inference-report3333 
Model Name : model-real-time-inference-report333
```
For more details and deployment steps, refer to the [ML-Pipeline deployment_utils folder](./Blockhouse_report/).


### 3. **Hoodwinked Charts**
This is the core trading Charts endpoint that allows you to run both buy and sell inferences.
####Endpoint for this:
```python
Endpoint name : endpoint-real-time-inference24-HW-R 
Model Name : model-real-time-inference24-HW-R-inference-component
```
For more details and deployment steps, refer to the [ML-Pipeline deployment_utils folder](./Hoodwink_chart/).

### 4. **Hoodwinked Report**
This is the core trading report endpoint that allows you to run both buy and sell inferences.
####Endpoint for this:
```python
Endpoint name : endpoint-real-time-inference24-HW-R 
Model Name : model-real-time-inference24-HW-R-inference-component
```
For more details and deployment steps, refer to the [ML-Pipeline deployment_utils folder](./Hoodwinked_report/).


### 5. **Hoodwinked Calculator**
This is the core trading report endpoint that allows you to run both buy and sell inferences.
####Endpoint for this:
```python
Yet to be Deployed.
```

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

## Deploying to Production

Steps to deploy to production, click [here](deployment_utils/production_readme.md)
