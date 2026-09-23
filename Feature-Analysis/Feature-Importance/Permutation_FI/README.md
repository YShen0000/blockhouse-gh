# Feature Importance Framework using Permutation Method

- This repository provides a framework to calculate feature importance in a reinforcement learning environment using a permutation-based method. 
- The permutation method helps determine the significance of each feature by shuffling it and observing the resulting change in rewards.

## How to use it

- You need to pass following parameters into **feature_importance_permutation**
- **Parameters**:
     - `env_class`: The custom environment class.
     - `trained_model`: The trained model used for predictions.
     - `data`: Data for out-of-sample testing.
     - `feature_list`: List of features' names for which importance is to be calculated.
     - `env_para`: Dictionary of all environment parameters except data.
- **Example**:
     - `env_class` = TradingEnvironment,
     - `trained_model` = model,
     - `data` = data_test,
     - `feature_list` = ['bid_price_1','bid_size_1','high','low','open','volume','volatility'],
     - `env_para` = {
                "reset_count": 20,
                "initial_inventory": 10000,
                "state_columns": ['bid_price_1','bid_size_1','high','low','open','volume','volatility']
       }

### Test Setup
1. **Define Environment and Model**: Create an environment (`env`) and initialize a trained model (`model`).
2. **Generate Feature Importance Scores**: Use `feature_importance_permutation` to calculate feature importance by shuffling each feature and measuring its impact on rewards.
3. **Interpret Results**: The function returns a dictionary with feature names as keys and their importance scores as values.

## Example Usage

```python
# Import required libraries
import pandas as pd
import numpy as np
import torch

# Initialize environment and model
env = ...  # Define your environment instance
model = ...  # Load or train your model

# Define parameters for testing
data = pd.read_csv('data.csv')  # Example data
feature_list = ['feature1', 'feature2', 'feature3']  # List of features
env_params = {'param1': value1, 'param2': value2}  # Environment parameters

# Calculate feature importance using permutation
importance_scores = feature_importance_permutation(
  env_class = TradingEnvironment,
  trained_model = model,
  data = data,
  feature_list = feature_list,
  env_para = env_params
)
print(importance_scores)
```

## Framework Details

### Main Functions

1. **create_environment(env_class, data_input, env_para)**

   This function automatically creates an instance of an environment with the specified parameters.

   - **Parameters**:
     - `env_class`: The class of the environment to be instantiated.
     - `data_input`: Input data for the environment.
     - `env_para`: Dictionary containing parameters for the environment.

   - **Returns**:
     - An instance of the specified environment.

2. **shuffle_feature(feature, env_class, data_input, env_para)**

   Shuffles a specific feature within the data to assess its importance by nullifying its effect.

   - **Parameters**:
     - `feature`: Name of the feature to be shuffled.
     - `env_class`: The environment class.
     - `data_input`: Input data for the environment.
     - `env_para`: Dictionary containing parameters for the environment.

   - **Returns**:
     - An environment instance with the specified feature shuffled.

   - **Note**: To avoid disrupting potential time series relationships in the data, the feature data is split in half and the two halves are swapped.

3. **calculate_final_reward(model, env, steps)**

   Calculates the cumulative reward over a specified number of steps.

   - **Parameters**:
     - `model`: The trained model.
     - `env`: The environment instance.
     - `steps`: Number of steps for which rewards are calculated.

   - **Returns**:
     - The cumulative reward over the specified steps.

4. **feature_importance_permutation(env_class, trained_model, data, feature_list, env_para)**

   Calculates feature importance by shuffling each feature individually and observing the reduction in cumulative rewards.

   - **Parameters**:
     - `env_class`: The environment class.
     - `trained_model`: The trained model used for predictions.
     - `data`: Data for out-of-sample testing, containing features and additional data for reward calculation.
     - `feature_list`: List of features for which importance is to be calculated.
     - `env_para`: Dictionary of environment parameters.

   - **Returns**:
     - A dictionary of feature importance values based on the reduction in rewards.

   - **Notes**:
     - `data` is filled using forward and backward filling to handle any missing values.
     - The importance of each feature is measured by the percentage reduction in rewards after shuffling.

### Additional Notes
- **Interpretation of Results**: A higher percentage reduction in rewards indicates that the feature is more important.
- **Data Handling**: Ensure that `data` does not contain missing values, as these can affect the feature importance calculations.

## Considerations
- **Effect on Time Series Data**: This framework shuffles feature values, which may disrupt time series relationships. Be cautious when using this on data where temporal ordering is important.
- **Model Requirements**: The framework assumes a deterministic model that outputs predictable actions based on input states.
- **Evaluation Metrics**: The percentage reduction in rewards is used to quantify feature importance, focusing on short-term impacts.

---

This README provides instructions on using the framework to evaluate feature importance in a reinforcement learning environment with a permutation-based approach.
