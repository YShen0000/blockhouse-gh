import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
import matplotlib.pyplot as plt
import seaborn as sns

# Load the metrics data
metrics_data = pd.read_csv('metrics_data.csv')

# Load the data with indicators
data_with_indicators = pd.read_csv('data_with_indicators.csv')

# Convert to datetime
metrics_data['timestamp'] = pd.to_datetime(metrics_data['timestamp'], errors='coerce')
data_with_indicators['datetime'] = pd.to_datetime(data_with_indicators['datetime'], errors='coerce')

# Merge metrics with the data
merged_data = data_with_indicators.join(metrics_data, how='inner')


def analyze_trading_feature_importance(merged_data):
    """
    Analyze feature importance based on actual trading performance metrics
    """
    features = data_with_indicators.select_dtypes(include=[np.number])  # Select only numeric columns


    # Initialize dictionary to store importance results for each metric
    importance_results = {}

    # Analyze importance for each performance metric
    metrics = {
        'model_slippage': merged_data['model_slippage'],
        'model_market_impact': merged_data['model_market_impact'],
        'model_spread_cost': merged_data['model_spread_cost'],
        "final_signal": merged_data["final_signal"]
    }

    for metric_name, metric_values in metrics.items():
        # Remove any NaN values
        mask = ~(features.isna().any(axis=1) | metric_values.isna())
        X = features[mask]
        y = metric_values[mask]

        # Use Ridge regression for continuous targets
        model = Ridge(alpha=1.0)
        model.fit(X, y)

        # Calculate feature importance (absolute coefficients)
        importance = pd.DataFrame({
            'feature': X.columns,
            'importance': np.abs(model.coef_)
        }).sort_values('importance', ascending=False)

        importance_results[metric_name] = importance
        # Save feature importance to CSV
        importance.to_csv(f'adjusted_Vwap)feature_importance_{metric_name}.csv', index=False)

        # Plot feature importance
        plt.figure(figsize=(10, 6))
        sns.barplot(x='importance', y='feature', data=importance)
        plt.title(f'Adjusted_Vwap_Feature Importance for {metric_name.upper()}')
        plt.tight_layout()
        plt.savefig(f'Adjusted_Vwap_feature_importance_{metric_name}.png')
        plt.close()

    return importance_results

# Perform the analysis
importance_analysis = analyze_trading_feature_importance(merged_data)
print(type(importance_analysis))
# Print results
for metric, importance in importance_analysis.items():
    print(f"\n{metric.upper()}:")
    print(importance)


# Calculate and plot correlation matrix for all numeric columns
numeric_data = data_with_indicators .select_dtypes(include=[np.number])  # Select only numeric columns
correlation_matrix = numeric_data.corr()
correlation_matrix.to_csv('adjusted_Vwap_feature_correlation_matrix.csv')

plt.figure(figsize=(12, 10))
sns.heatmap(correlation_matrix, annot=True, fmt=".2f", cmap='coolwarm', center=0)
    
plt.figure(figsize=(12, 10))
sns.heatmap(correlation_matrix, annot=True, fmt=".2f", cmap='coolwarm', center=0)
plt.title('adjusted_Vwap_Feature Correlation Matrix')
plt.tight_layout()
plt.savefig('adjusted_Vwap_feature_correlation_matrix.png')
plt.close()

    # Print the correlation matrix
print("\nFeature Correlation Matrix:")
print(correlation_matrix)