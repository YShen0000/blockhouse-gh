import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import pandas as pd
import numpy as np

def main():
    firm_name = "Merit Financial Advisors"
    st.set_page_config(page_title=firm_name, initial_sidebar_state="collapsed")
    st.title(firm_name + " Equity Report")
    ret_firm_list = st.button("Return to Firms List")
    try:
        summary_report = pd.read_csv("Summary_Report.csv")
    except Exception as e:
        st.error("ERROR: Missing Summary_Report.csv")

    firm_row = summary_report[summary_report['FileName'] == firm_name]
    
    if firm_row.empty:
        st.error(f"ERROR: No data found for WBI Investments")
    else:
        # Outputting data just cuz convenient
        st.write("## Data:")
        st.write(firm_row)
        graph_and_analysis_data = firm_view(firm_name, firm_row)

        # Analysis section for the firm. Uses the up to date stock tickers, and change in shares for each stock
        st.write("## Analysis:")
        st.write(graph_and_analysis_data["analysis_text"])

        # Slippage Bar Chart
        st.write("## Cost Comparison: Blockhouse vs. Industry Standards")
        st.write("### Slippage Bar Chart")
        # Create the select for All, Open, or Close
        bar_option = st.selectbox(label="Slippage Shown (All, Open, or Close)", options=("All", "Open", "Close"), label_visibility="collapsed")
        # Display selected option
        st.write(f"Selected: {bar_option}")
        # if open
        if bar_option == "Open":
            bar_columns = ["Slip Name", "Data"]
            bar_data = [
                [graph_and_analysis_data["bar_chart_html"]["openClose_bars"][0], graph_and_analysis_data["bar_chart_html"]["open_values"][0]],
                [graph_and_analysis_data["bar_chart_html"]["openClose_bars"][1], graph_and_analysis_data["bar_chart_html"]["open_values"][1]],
                [graph_and_analysis_data["bar_chart_html"]["openClose_bars"][2], graph_and_analysis_data["bar_chart_html"]["open_values"][2]]
            ]
        # if close
        elif bar_option == "Close":
            bar_columns = ["Slip Name", "Data"]
            bar_data = [
                [graph_and_analysis_data["bar_chart_html"]["openClose_bars"][0], graph_and_analysis_data["bar_chart_html"]["close_values"][0]],
                [graph_and_analysis_data["bar_chart_html"]["openClose_bars"][1], graph_and_analysis_data["bar_chart_html"]["close_values"][1]],
                [graph_and_analysis_data["bar_chart_html"]["openClose_bars"][2], graph_and_analysis_data["bar_chart_html"]["close_values"][2]]
            ]
        # if all or not one of our options
        else:
            bar_columns = ["Slip Name", "Data"]
            bar_data = [
                [graph_and_analysis_data["bar_chart_html"]["all_bars"][0], graph_and_analysis_data["bar_chart_html"]["all_values"][0]],
                [graph_and_analysis_data["bar_chart_html"]["all_bars"][1], graph_and_analysis_data["bar_chart_html"]["all_values"][1]],
                [graph_and_analysis_data["bar_chart_html"]["all_bars"][2], graph_and_analysis_data["bar_chart_html"]["all_values"][2]],
                [graph_and_analysis_data["bar_chart_html"]["all_bars"][3], graph_and_analysis_data["bar_chart_html"]["all_values"][3]],
                [graph_and_analysis_data["bar_chart_html"]["all_bars"][4], graph_and_analysis_data["bar_chart_html"]["all_values"][4]],
                [graph_and_analysis_data["bar_chart_html"]["all_bars"][5], graph_and_analysis_data["bar_chart_html"]["all_values"][5]],
            ]
        # form the chart data based on the option selected
        chart_data = pd.DataFrame(data=bar_data, columns=bar_columns)
        st.write(chart_data)
        # create the bar graph
        st.bar_chart(chart_data, x="Slip Name", y_label="Type of Slippage (Refer to Legend)", x_label="Average Slippage In Dollars Per Average Share", horizontal=True, stack=False)

        # Cost Efficiency: Savings Achieved with Blockhouse
        st.write("## Cost Efficiency: Savings Achieved with Blockhouse")
        st.write("### Stacked Savings Bar Chart")
        # Create the select for All, Open, or Close
        stock_names = graph_and_analysis_data["stacked_bar_chart_html"]["stock_names"]
        st_bar_option = st.selectbox(label="Stock Displayed", options=("All", stock_names[0], stock_names[1], stock_names[2], stock_names[3]), label_visibility="collapsed")
        # Display selected option
        st.write(f"Selected: {st_bar_option}")
        # if stock1
        if st_bar_option == stock_names[0]:
            st_bar_columns = ["Savings Name", stock_names[0]]
            st_bar_data = [
                ["Savings vs TWAP", graph_and_analysis_data["stacked_bar_chart_html"]["stock1_savings"][0]],
                ["Savings vs VWAP", graph_and_analysis_data["stacked_bar_chart_html"]["stock1_savings"][1]],
            ]
        # if stock2
        elif st_bar_option == stock_names[1]:
            st_bar_columns = ["Savings Name", stock_names[1]]
            st_bar_data = [
                ["Savings vs TWAP", graph_and_analysis_data["stacked_bar_chart_html"]["stock2_savings"][0]],
                ["Savings vs VWAP", graph_and_analysis_data["stacked_bar_chart_html"]["stock2_savings"][1]],
            ]
        # if stock3
        elif st_bar_option == stock_names[2]:
            st_bar_columns = ["Savings Name", stock_names[2]]
            st_bar_data = [
                ["Savings vs TWAP", graph_and_analysis_data["stacked_bar_chart_html"]["stock3_savings"][0]],
                ["Savings vs VWAP", graph_and_analysis_data["stacked_bar_chart_html"]["stock3_savings"][1]],
            ]
        # if stock4
        elif st_bar_option == stock_names[3]:
            st_bar_columns = ["Savings Name", stock_names[3]]
            st_bar_data = [
                ["Savings vs TWAP", graph_and_analysis_data["stacked_bar_chart_html"]["stock4_savings"][0]],
                ["Savings vs VWAP", graph_and_analysis_data["stacked_bar_chart_html"]["stock4_savings"][1]],
            ]
        # if all or not one of our options
        else:
            st_bar_columns = ["Savings Name"] + stock_names
            st_bar_data =   [
                ["Savings vs TWAP", graph_and_analysis_data["stacked_bar_chart_html"]["stock1_savings"][0], graph_and_analysis_data["stacked_bar_chart_html"]["stock2_savings"][0], graph_and_analysis_data["stacked_bar_chart_html"]["stock3_savings"][0], graph_and_analysis_data["stacked_bar_chart_html"]["stock4_savings"][0]],
                ["Savings vs VWAP", graph_and_analysis_data["stacked_bar_chart_html"]["stock1_savings"][1], graph_and_analysis_data["stacked_bar_chart_html"]["stock2_savings"][1], graph_and_analysis_data["stacked_bar_chart_html"]["stock3_savings"][1], graph_and_analysis_data["stacked_bar_chart_html"]["stock4_savings"][1]],
                ]
        # form the chart data based on the option selected
        chart_data = pd.DataFrame(data=st_bar_data, columns=st_bar_columns)
        st.write(chart_data)
        # create the bar graph
        st.bar_chart(chart_data, x="Savings Name", y_label="Type of Slippage (Refer to Legend)", x_label="Average Slippage In Dollars Per Average Share", stack=True)

        # Weekly Savings: A Snapshot of Consistency
        st.write("## Weekly Savings: A Snapshot of Consistency")
        st.write("### Table Data")
        # Create the select for All, Open, or Close
        tb_bar_option = st.selectbox(label="Stock Displayed", options=("Open", "Close", "TWAP", "VWAP"), label_visibility="collapsed")
        # Display selected option
        st.write(f"Selected: {tb_bar_option}")
        table_dict = graph_and_analysis_data["table_html"]
        stock_vals = table_dict["StockData"]
        shares_vals = table_dict["SharesData"]
        open_vals = table_dict["OpenData"]
        close_vals = table_dict["CloseData"]
        twap_vals = table_dict["TWAPValData"]
        vwap_vals = table_dict["VWAPValData"]
        lstm_vals = table_dict["LSTMValData"]
        savings_vs_open_vals = table_dict["SavingsVsOpenData"]
        savings_vs_close_vals = table_dict["SavingsVsCloseData"]
        savings_vs_twap_vals = table_dict["SavingsVsTWAPData"]
        savings_vs_vwap_vals = table_dict["SavingsVsVWAPData"]
        avg_savings_vs_twap = table_dict["AvgSavingsVsTWAP"]
        avg_savings_vs_vwap = table_dict["AvgSavingsVsVWAP"]
        # if close
        if tb_bar_option == "Close":
            tb_bar_columns = ["Securities", "Open", "Close", "TWAP", "VWAP", "Bhouse", "Shares Traded", "Savings vs Close"]
            tb_bar_data = [
                [stock_vals[0], open_vals[0], close_vals[0], twap_vals[0], vwap_vals[0], lstm_vals[0], shares_vals[0], savings_vs_close_vals[0]],
                [stock_vals[1], open_vals[1], close_vals[1], twap_vals[1], vwap_vals[0], lstm_vals[1], shares_vals[1], savings_vs_close_vals[1]],
                [stock_vals[2], open_vals[2], close_vals[2], twap_vals[2], vwap_vals[0], lstm_vals[2], shares_vals[2], savings_vs_close_vals[2]],
                [stock_vals[3], open_vals[3], close_vals[3], twap_vals[3], vwap_vals[0], lstm_vals[3], shares_vals[3], savings_vs_close_vals[3]],
            ]
        # if twap
        elif tb_bar_option == "TWAP":
            tb_bar_columns = ["Securities", "Open", "Close", "TWAP", "VWAP", "Bhouse", "Shares Traded", "Savings vs TWAP"]
            tb_bar_data = [
                [stock_vals[0], open_vals[0], close_vals[0], twap_vals[0], vwap_vals[0], lstm_vals[0], shares_vals[0], savings_vs_twap_vals[0]],
                [stock_vals[1], open_vals[1], close_vals[1], twap_vals[1], vwap_vals[0], lstm_vals[1], shares_vals[1], savings_vs_twap_vals[1]],
                [stock_vals[2], open_vals[2], close_vals[2], twap_vals[2], vwap_vals[0], lstm_vals[2], shares_vals[2], savings_vs_twap_vals[2]],
                [stock_vals[3], open_vals[3], close_vals[3], twap_vals[3], vwap_vals[0], lstm_vals[3], shares_vals[3], savings_vs_twap_vals[3]],
            ]
        # if vwap
        elif tb_bar_option == "VWAP":
            tb_bar_columns = ["Securities", "Open", "Close", "TWAP", "VWAP", "Bhouse", "Shares Traded", "Savings vs VWAP"]
            tb_bar_data = [
                [stock_vals[0], open_vals[0], close_vals[0], twap_vals[0], vwap_vals[0], lstm_vals[0], shares_vals[0], savings_vs_vwap_vals[0]],
                [stock_vals[1], open_vals[1], close_vals[1], twap_vals[1], vwap_vals[0], lstm_vals[1], shares_vals[1], savings_vs_vwap_vals[1]],
                [stock_vals[2], open_vals[2], close_vals[2], twap_vals[2], vwap_vals[0], lstm_vals[2], shares_vals[2], savings_vs_vwap_vals[2]],
                [stock_vals[3], open_vals[3], close_vals[3], twap_vals[3], vwap_vals[0], lstm_vals[3], shares_vals[3], savings_vs_vwap_vals[3]],
            ]
        # if open or not one of our options
        else:
            tb_bar_columns = ["Securities", "Open", "Close", "TWAP", "VWAP", "Bhouse", "Shares Traded", "Savings vs Open"]
            tb_bar_data = [
                [stock_vals[0], open_vals[0], close_vals[0], twap_vals[0], vwap_vals[0], lstm_vals[0], shares_vals[0], savings_vs_open_vals[0]],
                [stock_vals[1], open_vals[1], close_vals[1], twap_vals[1], vwap_vals[0], lstm_vals[1], shares_vals[1], savings_vs_open_vals[1]],
                [stock_vals[2], open_vals[2], close_vals[2], twap_vals[2], vwap_vals[0], lstm_vals[2], shares_vals[2], savings_vs_open_vals[2]],
                [stock_vals[3], open_vals[3], close_vals[3], twap_vals[3], vwap_vals[0], lstm_vals[3], shares_vals[3], savings_vs_open_vals[3]],
            ]
        # form the chart data based on the option selected
        chart_data = pd.DataFrame(data=tb_bar_data, columns=tb_bar_columns)
        # create the table
        st.write(chart_data)




    if ret_firm_list:
        switch_page("Firm List")

def create_graphs(data):
    # Custom color palette
    colors = ['#7962E7', '#A1EAFB', '#3DBEF6']
    all_bars = ['TWAP Slippage (Open)', 'TWAP Slippage (Close)', 'VWAP Slippage (Open)', 'VWAP Slippage (Close)', 'LSTM Slippage (Open)', 'LSTM Slippage (Close)']
    openClose_bars = ['TWAP Slippage', 'VWAP Slippage', 'LSTM Slippage']
    
    num_stocks = 3

    # Average Open: (Sum of Open price of all stocks) / number of stocks
    average_open = data['AvgOpen']

    # Average Close: (Sum of Close price of all stocks) / number of stocks
    average_close = data['AvgClose']
    
    # Average shares: (Total number of shares for three stocks) / number of stocks
    average_shares = data['Shares'] / num_stocks
    
    # Each Value follows the following format:
    #   
    #   (Average Strategy Value - Average Open/Close Value) * Average? Shares
    all_values = [
        ( data['AvgTWAPVal'] - average_open ) * average_shares,
        ( data['AvgTWAPVal'] - average_close ) * average_shares,
        ( data['AvgVWAPVal'] - average_open ) * average_shares,
        ( data['AvgVWAPVal'] - average_close ) * average_shares,
        ( data['AvgLSTMVal'] - average_open ) * average_shares,
        ( data['AvgLSTMVal'] - average_close ) * average_shares,
    ]

    open_values = [
        ( data['AvgTWAPVal'] - average_open ) * average_shares,
        ( data['AvgVWAPVal'] - average_open ) * average_shares,
        ( data['AvgLSTMVal'] - average_open ) * average_shares,
    ]

    close_values = [
        ( data['AvgTWAPVal'] - average_close ) * average_shares, 
        ( data['AvgVWAPVal'] - average_close ) * average_shares, 
        ( data['AvgLSTMVal'] - average_close ) * average_shares,
    ]

    bar_chart_dict = {'all_bars':all_bars, 'all_values':all_values, 'openClose_bars':openClose_bars, 'open_values':open_values, 'close_values':close_values}

    # Stacked Bar Chart: Dollars Saved for Each Stock
    categories = ['Savings vs TWAP', 'Savings vs VWAP']
    stock1_savings = [data['SavingsVsTWAP1'], data['SavingsVsVWAP1']]
    stock2_savings = [data['SavingsVsTWAP2'], data['SavingsVsVWAP2']]
    stock3_savings = [data['SavingsVsTWAP3'], data['SavingsVsVWAP3']]
    stock4_savings = [data['SavingsVsTWAP4'], data['SavingsVsVWAP4']]
    
    stacked_bar_chart_dict = {
        'categories': categories,
        'stock_names': [data['Stock1'], data['Stock2'], data['Stock3'], data['Stock4']],
        'stock1_savings': stock1_savings,
        'stock2_savings': stock2_savings,
        'stock3_savings': stock3_savings,
        'stock4_savings': stock4_savings,
    }

    # Table: Weekly Savings: A Snapshot of Consistency
    table_dict = {'StockData': [data['Stock1'], data['Stock2'], data['Stock3'], data['Stock4']],
                  'SharesData': [int(data['Shares1']), int(data['Shares2']), int(data['Shares3']), int(data['Shares4'])],
                  'OpenData': [data['Open1'], data['Open2'], data['Open3'], data['Open4']], 
                  'CloseData': [data['Close1'], data['Close2'], data['Close3'], data['Close4']],
                  'TWAPValData': [data['TWAPVal1'], data['TWAPVal2'], data['TWAPVal3'], data['TWAPVal4']],
                  'VWAPValData': [data['VWAPVal1'], data['VWAPVal2'], data['VWAPVal3'], data['VWAPVal4']],
                  'LSTMValData': [data['LSTMVal1'], data['LSTMVal2'], data['LSTMVal3'], data['LSTMVal4']],
                  'SavingsVsOpenData': [data['SavingsVsOpen1'], data['SavingsVsOpen2'], data['SavingsVsOpen3'], data['SavingsVsOpen4']],
                  'SavingsVsCloseData': [data['SavingsVsClose1'], data['SavingsVsClose2'], data['SavingsVsClose3'], data['SavingsVsClose4']],
                  'SavingsVsTWAPData': [data['SavingsVsTWAP1'], data['SavingsVsTWAP2'], data['SavingsVsTWAP3'], data['SavingsVsTWAP4']],
                  'SavingsVsVWAPData': [data['SavingsVsVWAP1'], data['SavingsVsVWAP2'], data['SavingsVsVWAP3'], data['SavingsVsVWAP4']],
                  'AvgSavingsVsTWAP': data['AvgSavingsVsTWAP'], 'AvgSavingsVsVWAP': data['AvgSavingsVsVWAP']}

    # Line Chart: Weekly Savings (Placeholder)
    weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5']  # Placeholder weeks
    savings = [1000, 1500, 1200, 1700, 2000]  # Placeholder savings
    line_chart_dict = {'weeks':weeks, 'savings':savings}
    
    return bar_chart_dict, stacked_bar_chart_dict, table_dict, line_chart_dict

def firm_view(name, data):
    firm_name = name
    firm_data = data

    bar_chart_html, stacked_bar_chart_html, table_html, line_chart_html = create_graphs(firm_data.iloc[0])

    # Get the top 3 stocks for this firm
    top_stocks = [firm_data.iloc[0]['Stock1'], firm_data.iloc[0]['Stock2'], firm_data.iloc[0]['Stock3'], firm_data.iloc[0]['Stock4']]
    top_stocks_change_shares = [firm_data.iloc[0]['Change1'], firm_data.iloc[0]['Change2'], firm_data.iloc[0]['Change3'], firm_data.iloc[0]['Change4']]

    # Calculate average shares traded per week
    total_shares = firm_data.iloc[0]['Shares']
    traded_per_week = total_shares / 13
    quarterly_savings = (firm_data.iloc[0]['AvgSavingsVsTWAP'] + firm_data.iloc[0]['AvgSavingsVsVWAP']) * 13

    analysis_text = (
        f"At Blockhouse, we understand that portfolio rebalancing can be costly, especially during volatile periods. "
        f"Our machine learning models deliver real-time insights to optimize trades, minimize costs, and maximize returns. "
        f"According to your 13-F filings, the stocks with the largest net increase in holdings were "
        f"**{top_stocks[0]}(+{top_stocks_change_shares[0]})** and **{top_stocks[1]}(+{top_stocks_change_shares[1]})**, and the stocks with the largest net decrease in holdings were "
        f"**{top_stocks[2]}({top_stocks_change_shares[2]})** and **{top_stocks[3]}({top_stocks_change_shares[3]})**."
        f"Based on your total reported shares of {total_shares:,}, we estimate an average of {traded_per_week:,.0f} "
        f"shares traded per week. We've analyzed these positions to identify cost-saving opportunities, "
        f"focusing on slippage, market impact, bid-ask spread, and commissions."
    )
    
    return {
        'firm_name': firm_name,
        'bar_chart_html': bar_chart_html,
        'stacked_bar_chart_html': stacked_bar_chart_html,
        'table_html': table_html,
        'line_chart_html': line_chart_html,
        'analysis_text': analysis_text,
        'firm_data': firm_data.to_dict(orient='records')[0],
        'traded_per_week': traded_per_week,
        'quarterly_savings': quarterly_savings,
    }

if __name__ == "__main__":
    main()