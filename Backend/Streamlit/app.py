import base64
import time

import streamlit as st
import pandas as pd

from utils import data_preprocessing, report_calculation, report_generation

def main():
    st.title("Blockhouse Streamlit")
    platform_options = ["Select a platform", "Charles Schwab", "Robinhood", "Webull", "Plaid"]
    selected_platform = st.selectbox("Select the trading platform", platform_options)

    realtime = st.toggle('Use realtime endpoint (default = async)')

    if selected_platform != "Select a platform":
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.write("Original Data:")
            st.write(df)

            # Preprocess the data, then get the report on that data
            trade_blotter = data_preprocessing.preprocess_by_platform(df, selected_platform)

            # Get the inference on the trade data either using the realtime or (by default) async endpoints
            if realtime:
                # Get the realtime inference
                inference = data_preprocessing.get_realtime_inference(trade_blotter)
            else:
                # Reqeust an async inference
                output_file = data_preprocessing.request_async_inference(trade_blotter)
                # Wait for the async model to return an inference
                while True:
                    inference = data_preprocessing.get_async_inference(output_file)
                    if inference is not None:
                        break
                    time.sleep(2)
      
            trade_blotter, data_dict, error_message = data_preprocessing.preprocess_data_merged(trade_blotter, inference)
            if error_message:
                st.error(error_message)
            report_data = report_calculation.generate_report_data(trade_blotter)

            # Create tabs
            tab1, tab2, tab3 = st.tabs(["Report", "Graphs", "Onboarding Data"])
            
            with tab1:
                st.subheader("Report")
                document_base64 = report_generation.generate_report(report_data)
                base64_pdf = base64.b64encode(document_base64).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)

            with tab2:
                st.subheader("Graphs")

                if error_message:
                    st.error(error_message)
                else:
                    st.subheader("Bar Graph - Average Slippage % vs. Strategy")
                    hoodwinked_analysis(trade_blotter, data_dict)

            with tab3:
                st.subheader("Onboarding Data")
                
                if error_message:
                    st.error(error_message)
                else:
                    st.subheader("Trading Overview")
                    st.write(report_calculation.generate_trading_overview(trade_blotter))
                    
                    st.subheader("Trades with Most Slippage")
                    st.write(report_calculation.calculate_trades_slippage(trade_blotter))
                    
                    st.subheader("Potential Savings")
                    st.write(report_calculation.calculate_potential_savings(trade_blotter))

def hoodwinked_analysis(trade_blotter, data_dict):
    """
    Analyze data and generate various charts in Streamlit.

    Args:
    df (pd.DataFrame): The input DataFrame containing trade data.

    Returns:
    None: Displays charts directly in the Streamlit app.
    """
    st.title("Data Analysis")
    trade_blotter_filtered = trade_blotter.copy()
    tickers = trade_blotter_filtered['Symbol'].unique()

    scaling_factor_report = report_calculation.calculate_potential_savings(trade_blotter)['scaling_factor']

    st.write(f"Number of stocks: {len(tickers)}")
    st.write(f"Date range: {trade_blotter['Date'].min()} to {trade_blotter['Date'].max()}")

    st.subheader("Excess Returns Over Time")
    stock = trade_blotter_filtered['Symbol'].unique().tolist()[0]
    start_date = trade_blotter_filtered['Date'].min()
    end_date = trade_blotter_filtered['Date'].max()

    xs_returns_data = report_calculation.plot_excess_returns(
        trade_blotter_filtered, 
        stock=stock,
        show_open=True, 
        show_close=True, 
        show_twap=True, 
        show_vwap=True, 
        show_hwoe=True,
        start_date=start_date,
        end_date=end_date,
        hwoe_adjustment_factor=scaling_factor_report,
        aggregate=True
    )
    xs_returns_chart = report_calculation.xs_returns_line(xs_returns_data)
    st.plotly_chart(xs_returns_chart)

    st.subheader("Average Slippage % vs Strategy")
    st.plotly_chart(report_calculation.avg_slippage_bar(trade_blotter))

    st.subheader("Slippage Sums by Benchmark")
    slippage_bar = report_calculation.calculate_slippage_sums(trade_blotter, hwoe_adjustment_factor=scaling_factor_report)

    if isinstance(slippage_bar, dict):
        slippage_sums_chart = report_calculation.slippage_sum_bar(slippage_bar)
    elif isinstance(slippage_bar, pd.DataFrame):
        slippage_sums_chart = report_calculation.slippage_sum_bar(slippage_bar.to_dict())
    else:
        st.error("Unexpected data format for slippage sums. Unable to plot bar chart.")
    st.plotly_chart(slippage_sums_chart)

    st.subheader("Candlestick Chart")
    selected_stock = st.selectbox("Select a stock for the candlestick chart", options=tickers)
    
    candlestick_data = report_calculation.setup_slippage_analysis(trade_blotter_filtered, data_dict, selected_stock)
    
    plot_data = candlestick_data.get('plot_data', {})
    trade_price = candlestick_data.get('trade_price', 0)
    benchmark_prices = candlestick_data.get('Benchmark_Prices', {})
    
    selected_benchmarks = st.multiselect(
        "Select benchmarks to display",
        options=list(benchmark_prices.keys()),
        default=list(benchmark_prices.keys())
    )

    candlestick_chart = report_calculation.candlestick(plot_data, trade_price, benchmark_prices, selected_benchmarks)
    st.plotly_chart(candlestick_chart)

if __name__ == "__main__":
    main()