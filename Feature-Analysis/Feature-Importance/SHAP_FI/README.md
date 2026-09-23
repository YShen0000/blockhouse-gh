# Feature Importance Framework of SHAP

- This repository provides a framework to calculate and visualize feature importance in a reinforcement learning environment using SHAP (SHapley Additive exPlanations). 
- The framework is designed to work with a deterministic model, focusing on short-term feature impacts on the model's actions.
- The feature importance result image also listed those states generated in the environment in addition to the features. These states are unnamed, so please ignore them.

## How to use it

- You need to pass following parameters into **feature_importance_shap**
- **Parameters**:
     - `env`: The custom environment class.
     - `model`: The trained model used for predictions.
     - `steps`: The recommended step is 500. Large steps might take a long time to run the code.
     - `feature_names`: List of features' names for which importance is to be calculated.

- **Example**:
     - `env` = TradingEnvironment,
     - `model` = model,
     - `steps` = 500,
     - `feature_list` = ['bid_price_1','bid_size_1','high','low','open','volume','volatility']

## Test Setup
1. **Define Environment and Model**: Instantiate an environment (`env`) and load or train a model (`model`) compatible with the framework.
2. **Generate States and Calculate SHAP Values**: Use the `feature_importance_shap` function to generate states, calculate SHAP values, and visualize feature importance.
3. **Plot SHAP Values**: SHAP values for each feature are plotted against sample indices, allowing users to assess each feature’s importance.

### Example Usage

```python
# Import required libraries
import numpy as np
import pandas as pd
import torch
import shap

# Initialize environment and model
env = ...  # Define your environment instance
model = ...  # Load or train your model

# Define the number of steps and feature names
steps = 500 # With the increase of steps, the running time will surge.
feature_names = ['bid_price_1', 'bid_size_1', 'high', 'low', 'open', 'volume', 'volatility']

# Calculate and visualize feature importance
shap_df = feature_importance_shap(env, model, steps, feature_names)
print(shap_df)
```
### Result
<img width="768" alt="Screenshot 2024-11-07 at 8 23 39 PM" src="https://github.com/user-attachments/assets/a446a376-2205-421c-9a32-24c5523889bc">

## Framework Details

### Main Functions

1. **generate_states(env, model, steps)**

   This function generates states from a reinforcement learning environment by stepping through it for a specified number of steps.

   - **Parameters**:
     - `env`: The environment instance used to generate states.
     - `model`: A trained reinforcement learning model.
     - `steps`: Number of steps for state generation.

   - **Returns**:
     - `states`: Array of generated states.
     - `len_of_state`: Length of each state vector.

   - **Note**: The environment is reset if an episode ends before reaching the desired number of steps.

2. **get_actions(model, state)**

   Fetches actions for a given state using the model.

   - **Parameters**:
     - `model`: A trained reinforcement learning model.
     - `state`: A single state or batch of states for action prediction.

   - **Returns**:
     - `action`: Predicted action(s) by the model.

3. **feature_importance_shap(env, model, steps, feature_names)**

   This function calculates and visualizes SHAP values to determine feature importance for the model’s actions.

   - **Parameters**:
     - `env`: The environment instance.
     - `model`: A trained reinforcement learning model.
     - `steps`: Number of steps for generating states.
     - `feature_names`: List of feature names for SHAP visualization.

   - **Returns**:
     - A `pandas.DataFrame` containing SHAP values for each feature.

   - **Notes**:
     - SHAP values focus on the short-term effect of features on actions and may not reflect long-term impacts on rewards.
     - If extra states are generated during the process, they may appear in the plots without labels. They should be ignored.

### Additional Notes
- **Reducing Computation Time**: Method `shap.sample(data, K)` for random sampling or `shap.kmeans(data, K)` for cluster-based summarization could reduce running time, but destroy the time series relationships.
- **Interpretation of SHAP Values**: SHAP values represent each feature’s contribution to the model's actions. Higher absolute SHAP values indicate a greater impact. The features in the plot is in a decreasing order.

## Considerations
- **Model Compatibility**: The framework assumes a deterministic model where actions are predictable based on states.
- **Feature Names Length**: Ensure that the `feature_names` list length matches the number of features in `states`.
- **SHAP Limitations**: SHAP values in this framework reflect only the short-term impact on actions and do not account for potential long-term rewards.

---

This README provides instructions on using the framework to evaluate feature importance in a reinforcement learning context using SHAP values.
