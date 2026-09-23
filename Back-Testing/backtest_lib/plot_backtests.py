import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
def streamlit_metrics_plot(filename="sell_comparison_trading_data.csv", is_sell=True, is_equity=True):
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
        plt.title(f"Performance Metrics for {trade_type} {model_type} of {subset['shares'].iloc[0]} of {subset['ticker'].iloc[0]} on {subset['date'].iloc[0]}")
        plt.xlabel('Strategy')
        plt.ylabel('Total Value')
        plt.xticks(adjusted_indices + (bar_width * (num_metrics - 1) / 2), model_names)  # Set model names as x-tick labels
        plt.legend(title="Metrics")

        # Streamlit: Display the plot in the app
        st.pyplot(plt)  # This will render the plot directly in Streamlit

        plt.close()  # Close the plot to free memory
def plot_market_impact_against_shares():
    df_metrics = pd.read_csv('metrics_data.csv')
    plt.figure(figsize=(10, 6))
    plt.scatter(df_metrics['shares'], df_metrics['model_market_impact'], label='Model Market Impact', color='blue')
    plt.scatter(df_metrics['shares'], df_metrics['twap_market_impact'], label='TWAP Market Impact', color='green')
    plt.scatter(df_metrics['shares'], df_metrics['vwap_market_impact'], label='VWAP Market Impact', color='red')
    plt.xlabel('Shares')
    plt.ylabel('Market Impact')
    plt.legend()
    plt.show()
def plot_single_backtest(backtest_results, ticker, inventory, date, is_sell):
    metrics = ['Slippage', 'Market Impact', 'Spread Cost', 'Opportunity Cost vs Close', 'Opportunity Cost vs Open']
    model_names = backtest_results.index
    values = backtest_results[metrics].values.T

    plt.figure(figsize=(14, 8))
    bar_width = 0.2
    indices = np.arange(len(model_names))

    for i, metric in enumerate(metrics):
        bars = plt.bar(indices + i * bar_width, values[i], width=bar_width, label=metric)
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, yval, f'{yval:.2e}', ha='center', va='bottom', fontsize=8)

    plt.title(f"Performance Metrics for {'Sell' if is_sell else 'Buy'} of {inventory} {ticker} on {date}")
    plt.xlabel('Strategy')
    plt.ylabel('Total Value')
    plt.xticks(indices + bar_width * 1.5, model_names)
    plt.legend(title="Metrics")
    plt.tight_layout()
    plt.savefig(f'backtest_{ticker}_{date}_{"sell" if is_sell else "buy"}.png')
    plt.close()
def plot_slippage_dist():
    df_slippage = pd.read_csv('metrics_data.csv')

    # Convert 'timestamp' back to datetime format
    df_slippage['timestamp'] = pd.to_datetime(df_slippage['timestamp'])

    # Plot the data
    plt.figure(figsize=(10, 6))
    plt.plot(df_slippage['timestamp'], df_slippage['model_slippage'], label='ModelSlippage', color='blue')
    plt.plot(df_slippage['timestamp'], df_slippage['twap_slippage'], label='TWAP Slippage', color='green')
    plt.plot(df_slippage['timestamp'], df_slippage['vwap_slippage'], label='VWAP Slippage', color='red')
    # Adding labels and title
    plt.xlabel('Timestamp')
    plt.ylabel('Slippage')
    plt.title('Slippage Over Time')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()
    plt.show()
def plot_slippage_by_interval():
    import pandas as pd
    import matplotlib.pyplot as plt

    # Load the CSV file into a DataFrame
    df_slippage = pd.read_csv('metrics_data.csv')

    # Convert 'timestamp' back to datetime format
    df_slippage['timestamp'] = pd.to_datetime(df_slippage['timestamp'])

    
    # Define the intervals to plot
    intervals = {
        '5 Minutes': '5T',
        '10 Minutes': '10T',
        '15 Minutes': '15T',
        '30 Minutes': '30T',
        '1 Hour': '1H',
        '2 Hours': '2H',
        '4 Hours': '4H'
    }
    
    # Set up subplots (3 rows, 3 columns)
    fig, axs = plt.subplots(3, 3, figsize=(15, 10), constrained_layout=True)
    axs = axs.flatten()  # Flatten the array of subplots for easy iteration
    
    for i, (interval_name, interval_code) in enumerate(intervals.items()):
        # Resample the data based on the selected interval
        df_slippage_binned = df_slippage.resample(interval_code, on='timestamp').mean().reset_index()

        # Plot in each subplot
        axs[i].plot(df_slippage_binned['timestamp'], df_slippage_binned['model_slippage'], label="Model Slippage", color='blue')
        axs[i].plot(df_slippage_binned['timestamp'], df_slippage_binned['twap_slippage'], label='TWAP Slippage', color='green')
        axs[i].plot(df_slippage_binned['timestamp'], df_slippage_binned['vwap_slippage'], label='VWAP Slippage', color='red')
        axs[i].set_title(f'Slippage ({interval_name})')
        axs[i].set_xlabel('Timestamp')
        axs[i].set_ylabel('Avg Slippage')
        axs[i].tick_params(axis='x', rotation=45)
        axs[i].grid(True)
        axs[i].legend(loc='best')

    # Hide any extra subplots (if there are any)
    for j in range(i + 1, len(axs)):
        axs[j].axis('off')

    # Show the full figure with subplots
    plt.show()


def plot_metrics(filename="sell_comparison_trading_data.csv", is_sell=True, is_equity=True):
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
        plt.title(f"Performance Metrics for {trade_type} {model_type} of {subset['shares'].iloc[0]} of {subset['ticker'].iloc[0]} on {subset['date'].iloc[0]}")
        plt.xlabel('Strategy')
        plt.ylabel('Total Value')
        plt.xticks(adjusted_indices + (bar_width * (num_metrics - 1) / 2), model_names)  # Set model names as x-tick labels
        plt.legend(title="Metrics")
        plt.show()  # To display the plot
        plt.savefig(f'bar_plot_{i+1}_{i+3}.png')  # To save the plot as a PNG file
        plt.close()