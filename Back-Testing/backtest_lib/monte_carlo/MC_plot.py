import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

def streamlit_metrics_plot(filename="monte_carlo_metrics.csv", is_sell=True, is_equity=True, is_monte_carlo=True):
    # Load the CSV data into a DataFrame
    df = pd.read_csv(filename)

    # Extract the relevant columns (metrics)
    metrics = ['slippage', 'market_impact', 'spread_cost', 'opportunity_cost_vs_close', 'opportunity_cost_vs_open']

    # Loop through every 3 rows and plot each one
    for i in range(0, len(df), 3):
        # Select the current set of 3 rows
        subset = df.iloc[i:i+3]
        
        # Ensure there are exactly 3 rows for this plot
        if len(subset) < 3:
            break

        # Prepare data for plotting
        model_names = subset['trader_model']
        values = subset[metrics].values.T  # Transpose to get metrics as columns

        # Define the position of the bars
        num_metrics = len(metrics)
        bar_width = 0.35  # Set bar width
        indices = np.arange(len(model_names))  # X locations for each model
        
        # Increase the multiplier to add more space between bar groups
        total_width = bar_width * num_metrics  # Total width of the bar group for each model
        spacing_multiplier = 0.5  # Significantly increase the spacing
        adjusted_indices = indices * (1 + total_width * spacing_multiplier)  # Adjust indices for more space
        
        # Increase figure size to accommodate wider bars
        plt.figure(figsize=(14, 8))  # Increased the figure size

        # Plot bars for each metric inside each model
        for j, metric in enumerate(metrics):
            bars = plt.bar(adjusted_indices + j * bar_width, values[j], width=bar_width, label=metric)
            
            # Add the numeric values on top of each bar
            for bar in bars:
                yval = bar.get_height()  # Get the height of the bar (which is the value)
                plt.text(
                    bar.get_x() + bar.get_width()/2, yval + 0.01,  # Positioning text
                    f'{yval:.2e}',  # Formatting the text in scientific notation
                    ha='center', va='bottom', fontsize=10  # Horizontal/Vertical alignment
                )

        # Customize the plot
        trade_type = "Equities" if is_equity else "Options"
        model_type = "Sell" if is_sell else "Buy"
        mc_type = "Monte Carlo Simulated " if is_monte_carlo else ""
        plt.title(f"{mc_type}Performance Metrics for {trade_type} {model_type} of {subset['shares'].iloc[0]} of {subset['ticker'].iloc[0]} on {subset['date'].iloc[0]}")
        plt.xlabel('Strategy')
        plt.ylabel('Total Value')
        plt.xticks(adjusted_indices + (bar_width * (num_metrics - 1) / 2), model_names)  # Set model names as x-tick labels
        plt.legend(title="Metrics")

        # Streamlit: Display the plot in the app
        st.pyplot(plt)  # This will render the plot directly in Streamlit

        plt.close()  # Close the plot to free memory
        
def plot_metrics(filename="monte_carlo_metrics.csv", is_sell=True, is_equity=True, is_monte_carlo=True):
    # Load the CSV data into a DataFrame
    df = pd.read_csv(filename)

    # Extract the relevant columns (metrics)
    metrics = ['slippage', 'market_impact', 'spread_cost', 'opportunity_cost_vs_close', 'opportunity_cost_vs_open']

    # Loop through every 3 rows and plot each one 
    for i in range(0, len(df), 3):
        # Select the current set of 3 rows
        subset = df.iloc[i:i+3]
        
        # Ensure there are exactly 3 rows for this plot
        if len(subset) < 3:
            break

        # Prepare data for plotting
        model_names = subset['trader_model']
        values = subset[metrics].values.T  # Transpose to get metrics as columns

        # Define the position of the bars
        num_metrics = len(metrics)
        bar_width = 0.35  # Set bar width
        indices = np.arange(len(model_names))  # X locations for each model
        
        # Increase the multiplier to add more space between bar groups
        total_width = bar_width * num_metrics  # Total width of the bar group for each model
        spacing_multiplier = 0.5  # Significantly increase the spacing
        adjusted_indices = indices * (1 + total_width * spacing_multiplier)  # Adjust indices for more space
        
        # Increase figure size to accommodate wider bars
        plt.figure(figsize=(14, 8))  # Increased the figure size

        # Plot bars for each metric inside each model
        for j, metric in enumerate(metrics):
            bars = plt.bar(adjusted_indices + j * bar_width, values[j], width=bar_width, label=metric)
            
            # Add the numeric values on top of each bar
            for bar in bars:
                yval = bar.get_height()  # Get the height of the bar (which is the value)
                plt.text(
                    bar.get_x() + bar.get_width()/2, yval + 0.01,  # Positioning text
                    f'{yval:.2e}',  # Formatting the text in scientific notation
                    ha='center', va='bottom', fontsize=10  # Horizontal/Vertical alignment
                )

        # Customize the plot
        trade_type = "Equities" if is_equity else "Options"
        model_type = "Sell" if is_sell else "Buy"
        mc_type = "Monte Carlo Simulated " if is_monte_carlo else ""
        plt.title(f"{mc_type}Performance Metrics for {trade_type} {model_type} of {subset['shares'].iloc[0]} of {subset['ticker'].iloc[0]} on {subset['date'].iloc[0]}")
        plt.xlabel('Strategy')
        plt.ylabel('Total Value')
        plt.xticks(adjusted_indices + (bar_width * (num_metrics - 1) / 2), model_names)  # Set model names as x-tick labels
        plt.legend(title="Metrics")
        plt.show()  # To display the plot
        plt.savefig(f'monte_carlo_bar_plot_{i+1}_{i+3}.png')  # To save the plot as a PNG file
        plt.close()

# def plot_monte_carlo_paths(simulated_paths, original_path, ticker, day_of_backtest):
#     fig, ax = plt.subplots(figsize=(12, 6))
    
#     # Plot simulated paths
#     for path in simulated_paths:
#         ax.plot(path, color='gray', alpha=0.1)
    
#     # Plot original path
#     ax.plot(original_path, color='blue', linewidth=2, label='Original Path')
    
#     ax.set_title(f"Monte Carlo Simulated Paths for {ticker} on {day_of_backtest}")
#     ax.set_xlabel('Time (minutes)')
#     ax.set_ylabel('Price')
#     ax.legend()
    
#     # Display the plot in Streamlit
#     st.pyplot(fig)
    
#     # Close the figure to free up memory
#     plt.close(fig)