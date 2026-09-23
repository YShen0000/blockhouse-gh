Model overview:
The model is present at 'Blockhouse-ML/GordonRitter/Models/bet_sizing_v1:
The bet sizing model predicts the proportion of the
inventory to be traded. It takes the following features
as an input:
1. Bid_price_1,
2. Bid_size_1,
3. Open,
4. Volume,
5. Daily_volume,
6. Volatility,
7. Fraction of evaluated optimal trade points to the total points (20),
8. Fraction of inventory remaining out of the given inventory.

It gives out the volume to be traded for a particular point.

Inferring the model:
The model inference is demonstrated in inference.ipynb
It runs a single function, run_pipeline, which runs 3 steps:
1. Fetches the data.
2. Predict optimal points for the next day for the given timeframe. 
3. Predict the optimal bet sizes for the given optimal points.

The function takes 5 arguments:
1. ticker
2. end_timestamp
3. timeframe
4. inventory
5. model_dir=
and returns a list of DataFrames.

The current setting returns a single DataFrame with two columns
timestamp and volume.