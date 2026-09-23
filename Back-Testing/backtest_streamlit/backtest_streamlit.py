import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from backtest_lib.backtest import run_backtest
from backtest_lib.monte_carlo.MC_backtest import run_monte_carlo_backtest
from backtest_lib.backtest import run_hw_trade_list
from backtest_lib.backtest import save_backtest_data
from backtest_lib.backtest import run_blockhouse_list   
import os
import subprocess
import hashlib
import time
def plot_market_impact_against_shares():
    df_metrics = pd.read_csv('metrics_data.csv')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(df_metrics['shares'], df_metrics['model_market_impact'], label='Model Market Impact', color='blue')
    ax.scatter(df_metrics['shares'], df_metrics['twap_market_impact'], label='TWAP Market Impact', color='green')
    ax.scatter(df_metrics['shares'], df_metrics['vwap_market_impact'], label='VWAP Market Impact', color='red')
    ax.set_xlabel('Shares')
    ax.set_ylabel('Market Impact')
    ax.legend()
    return fig
# Define the backtest function
def run_selected_backtest(ticker, inventory, day_of_backtest, is_sell):
    # Call the backtest function with provided parameters
    run_backtest(ticker, inventory, day_of_backtest, True, is_sell, True, True)
    st.success(f"Backtest completed for {ticker} on {day_of_backtest} (Sell: {is_sell})")

# Streamlit UI for input
st.sidebar.header("Backtest Configuration")

# Input fields to configure the backtest
ticker = st.sidebar.text_input("Ticker", "AAPL")
inventory = st.sidebar.number_input("Inventory", min_value=1, max_value=9999999, value=100)
day_of_backtest = st.sidebar.text_input("Backtest Day (YYYY-MM-DD)", "2024-09-09")
is_sell = st.sidebar.selectbox("Buy/Sell", ["Buy", "Sell"]) == "Sell"

# Monte Carlo simulation options
st.sidebar.header("Monte Carlo Simulation")
run_monte_carlo = st.sidebar.checkbox("Run Monte Carlo Simulation")
num_simulations = st.sidebar.number_input("Number of Simulations", min_value=1, max_value=9999999, value=20, step=1, disabled=not run_monte_carlo)

# Allow file upload (ML_prod.py, inference.py, data_handler.py, env.py, model.py)
st.sidebar.header("Upload Required Files")
ml_prod_file = st.sidebar.file_uploader("Upload ML_prod.py", type="py")
inference_file = st.sidebar.file_uploader("Upload inference.py", type="py")
data_handler_file = st.sidebar.file_uploader("Upload data_handler.py", type="py")
env_file = st.sidebar.file_uploader("Upload env.py", type="py")
model_file = st.sidebar.file_uploader("Upload model.py", type="py")
requirements_file = st.sidebar.file_uploader("Upload requirements.txt", type="txt")


# Handling the file upload process
def save_uploaded_file(uploaded_file, destination_folder):
    if uploaded_file is not None:
        try:
            # Ensure the destination directory exists
            if not os.path.exists(destination_folder):
                os.makedirs(destination_folder)
            # Save the uploaded file to the destination
            with open(os.path.join(destination_folder, uploaded_file.name), "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Show success message and then remove it after a few seconds
            success_message = st.empty()  # Create an empty placeholder
            success_message.success(f"Successfully uploaded {uploaded_file.name}")
            time.sleep(0.2)  # Wait for 3 seconds
            success_message.empty()  # Clear the success message

        except Exception as e:
            st.error(f"Error uploading {uploaded_file.name}: {e}")

# Save uploaded files to the 'uploaded_files' directory
destination_folder = "test_model"
hash_file_path = "test_model/requirements_hash.txt"
save_uploaded_file(ml_prod_file, destination_folder)
save_uploaded_file(inference_file, destination_folder)
save_uploaded_file(data_handler_file, destination_folder)
save_uploaded_file(env_file, destination_folder)
save_uploaded_file(model_file, destination_folder)
save_uploaded_file(requirements_file, destination_folder)

models_folder = "Models"
# Allow uploading of model files (e.g., .pt files for PyTorch models)
st.sidebar.header("Upload Model Files")
model_file_upload = st.sidebar.file_uploader("Upload Model (.pt)", type=["pt"])

# Save the uploaded model file to the "Models" directory
if model_file_upload is not None:
    save_uploaded_file(model_file_upload, models_folder)

# Function to install dependencies from the uploaded requirements.txt file
def install_requirements(requirements_path):
    try:
        result = subprocess.run(
            ["pip", "install", "-r", requirements_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode == 0:
            st.success("Installation of dependencies completed successfully!")
        else:
            st.error(f"Error installing dependencies: {result.stderr}")
    except Exception as e:
        st.error(f"An error occurred during installation: {e}")

# Function to calculate the hash of a file
def calculate_file_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        buffer = f.read()
        hasher.update(buffer)
    return hasher.hexdigest()
# Function to plot slippage for multiple intervals
def plot_multiple_intervals_slippage():
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
        axs[i].grid(True)  # Add grid to each subplot
        axs[i].legend(loc='best')

    # Hide any extra subplots (if there are any)
    for j in range(len(intervals), len(axs)):
        axs[j].axis('off')

    # Return the full figure to Streamlit
    return fig
def plot_slippage_dist():
    # Load the CSV file into a DataFrame
    df_slippage = pd.read_csv('metrics_data.csv')

    # Convert 'timestamp' back to datetime format
    df_slippage['timestamp'] = pd.to_datetime(df_slippage['timestamp'])

    # Plot the data
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df_slippage['timestamp'], df_slippage['model_slippage'], label='Model Slippage', color='blue')
    ax.plot(df_slippage['timestamp'], df_slippage['twap_slippage'], label='TWAP Slippage', color='green')
    ax.plot(df_slippage['timestamp'], df_slippage['vwap_slippage'], label='VWAP Slippage', color='red')

    # Adding labels and title
    ax.set_xlabel('Timestamp')
    ax.set_ylabel('Slippage')
    ax.set_title('Slippage Over Time')
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True)
    ax.legend()

    # Display the plot in Streamlit
    st.pyplot(fig)
def plot_market_impact_against_shares():
    df_metrics = pd.read_csv('metrics_data.csv')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(df_metrics['shares'], df_metrics['model_market_impact'], label='Model Market Impact', color='blue')
    ax.scatter(df_metrics['shares'], df_metrics['twap_market_impact'], label='TWAP Market Impact', color='green')
    ax.scatter(df_metrics['shares'], df_metrics['vwap_market_impact'], label='VWAP Market Impact', color='red')
    ax.set_xlabel('Shares')
    ax.set_ylabel('Market Impact')
    ax.legend()
    return fig
# Check if the hash of the requirements.txt file has changed
def has_requirements_changed(requirements_path):
    # Calculate current file hash
    current_hash = calculate_file_hash(requirements_path)
    
    # Check if hash file exists
    if os.path.exists(hash_file_path):
        # Read the saved hash
        with open(hash_file_path, "r") as f:
            saved_hash = f.read().strip()
        
        # Compare the current hash with the saved hash
        if current_hash == saved_hash:
            return False  # Requirements haven't changed
        else:
            # Update the saved hash with the current hash
            with open(hash_file_path, "w") as f:
                f.write(current_hash)
            return True  # Requirements have changed
    else:
        # If no hash file exists, create one and consider requirements changed
        with open(hash_file_path, "w") as f:
            f.write(current_hash)
        return True
# Handle requirements.txt installation with hash check
if requirements_file is not None:
    save_uploaded_file(requirements_file, destination_folder)
    requirements_path = os.path.join(destination_folder, requirements_file.name)
    
    # Check if the requirements file has changed
    if has_requirements_changed(requirements_path):
        with st.spinner("Installing dependencies..."):
            install_requirements(requirements_path)
    else:
        st.success("Requirements have not changed. Skipping installation.")

# Run the backtest when the button is pressed
if st.sidebar.button("Run Backtest"):
    with st.spinner("Running backtest..."):
        model_trades, model_metrics, twap_metrics, vwap_metrics = run_backtest(ticker, inventory, day_of_backtest, True, is_sell, True, True)
        st.write("Backtest Results:")
            
        # Create a DataFrame for the backtest results
        backtest_results = pd.DataFrame({
                'Slippage': [model_metrics[0], twap_metrics[0], vwap_metrics[0]],
                'Market Impact': [model_metrics[1], twap_metrics[1], vwap_metrics[1]],
                'Spread Cost': [model_metrics[2], twap_metrics[2], vwap_metrics[2]],
                "opportunity cost vs close": [model_metrics[4], twap_metrics[4], vwap_metrics[4]],
                "opportunity cost vs open": [model_metrics[5], twap_metrics[5], vwap_metrics[5]]
            }, index=['Model', 'TWAP', 'VWAP'])

        # Display the backtest results using st.dataframe
        st.dataframe(backtest_results)
            
        # Optionally, display model trades if needed
        st.write("Model Trades:")
        st.dataframe(model_trades)

        # Load the CSV file into a DataFrame
        df_slippage = pd.read_csv('metrics_data.csv')

        # Convert 'timestamp' back to datetime format
        df_slippage['timestamp'] = pd.to_datetime(df_slippage['timestamp'])
        # Streamlit app setup
        st.title("Slippage Distribution Over Time")

        # Call the function to plot and display the chart in Streamlit
        plot_slippage_dist()
        # Streamlit app setup
        st.title("Slippage Plotting for Multiple Intervals")

        # Generate and display the plot with subplots for each interval
        fig = plot_multiple_intervals_slippage()

        # Display the plot in Streamlit
        st.pyplot(fig)
        # Add the new market impact plot
        st.title("Market Impact Against Shares")
        market_impact_fig = plot_market_impact_against_shares()
        st.pyplot(market_impact_fig)
        if run_monte_carlo:
            st.spinner("Running Monte Carlo Simulation...")
            mc_results = run_monte_carlo_backtest(ticker, inventory, day_of_backtest, num_simulations, is_sell, record_data=True, plotter=True)
            st.write("Monte Carlo Simulation Results:")
            st.dataframe(mc_results)
        st.success(f"Backtest completed for {inventory} shares of {ticker} on {day_of_backtest} (Sell: {is_sell})")