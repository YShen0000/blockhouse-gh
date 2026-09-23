## Details about the current model

### Training
* use `training_tuning.ipynb` for training the model

### Testing
* use `testing.ipynb` for testing the model

### Backtesting
* use `backtesting.ipynb` for backtesting the model

### Production Testing
* use `production_testing.ipynb` for production testing the model

## Where to store Model?
* Store the model in backtest_lib/Model/{model.pt}

## How to infer?

* `Action = sell`
```
from inference import EquityInference

data_dir = 'Data' # where the data is stored
model_dir = 'Model' # where the models are stored
logging_dir = 'Logs' # where the logs are stored (optional)

# Initialize the inference object
inference = EquityInference(data_dir, model_dir, logging_dir, action="sell")

# Run inference for the given ticker, start date, end date, timeframe, inventory
inference.run_inference(ticker, start_date, end_date, timeframe, inventory)
```

* `Action = buy`
```
from inference import EquityInference

data_dir = 'Data' # where the data is stored
model_dir = 'Model' # where the models are stored
logging_dir = 'Logs' # where the logs are stored (optional)

# Initialize the inference object
inference = EquityInference(data_dir, model_dir, logging_dir, action="buy")

# Run inference for the given ticker, start date, end date, timeframe, inventory
inference.run_inference(ticker, start_date, end_date, timeframe, inventory)
```

## Installing Dependencies
```
pip install -r requirements.txt
```
