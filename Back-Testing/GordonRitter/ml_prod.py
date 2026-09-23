import numpy as np
import pandas as pd
from datetime import datetime
import pytz

from GordonRitter.utils.pipeline import OptimalBetSizeInference

# Create the Inference class object
obj = OptimalBetSizeInference(data_dir='Data')

# Get the bet size prediction results
# Pipeline steps:
# 1. Get the data for 2 days in the past for the given end time.
# 2. Predict the data for the next day upto the given timeframe.
# 3. Pick the 20 top least volatile points.
# 4. Predict the bet sizes to trade the given inventory over the given points.
rs = obj.run_pipeline(
    ticker='AAPL',
    end_timestamp=datetime.now(pytz.UTC).strftime('%Y-%m-%d'),
    timeframe=390,
    inventory=10000,
    bet_sz_model_dir='GordonRitter/Models/bet_sizing_v1')
