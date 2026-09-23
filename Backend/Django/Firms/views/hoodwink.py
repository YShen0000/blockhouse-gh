from django.http import HttpResponse
from django.shortcuts import redirect, render
from rest_framework.decorators import api_view
import pandas as pd
import plotly.graph_objs as go
from django.http import JsonResponse
import os
from .tasks import scrape_companies, merge_csvs, gather_all_data_post_scrape, merge_summary_report_csvs
from celery import chord, chain
import logging
# Load the CSV file
file_path = os.path.join(os.path.dirname(__file__), 'Summary_Report.csv')
df = pd.read_csv(file_path)
logger = logging.getLogger('django')


# Calculates savings vs ____ (Open, Close, TWAP, VWAP) scaled up with relation to number of shares
# Input:    num_stocks (the total number of stocks we are analysing), 
#           prices (an array with num_stocks Average prices (average of open, close, high and low for a stock))
#           all_open (an array with num_stocks Open values),
#           all_close (an array with num_stocks Close values),
#           all_twap (an array with num_stocks calculated TWAP values),
#           all_vwap (an array with num_stocks calculated VWAP values),
#           all_shares (an array with num_stocks number of shares for each stock), 
#
# Output:   savings_vs_open (an array of length num_stocks with savings versus the Open prices for each stock),
#           savings_vs_close (an array of length num_stocks with savings versus the Close prices for each stock),
#           savings_vs_twap (an array of length num_stocks with savings versus the TWAP prices for each stock),
#           savings_vs_vwap (an array of length num_stocks with savings versus the VWAP prices for each stock),
def calculate_savings_vs(num_stocks, buy_prices, sell_prices, all_open, all_close, all_twap, all_vwap, all_change_shares):
    savings_vs_open_buy = []
    savings_vs_close_buy = []
    savings_vs_twap_buy = []
    savings_vs_vwap_buy = []
    savings_vs_open_sell = []
    savings_vs_close_sell = []
    savings_vs_twap_sell = []
    savings_vs_vwap_sell = []
    twap_savings_vs_open = []
    twap_savings_vs_close = []
    vwap_savings_vs_open = []
    vwap_savings_vs_close = []
    # To calculate savings scaled up with relation to shares:
    #       Model Price (Models Prediction for the stock)
    #       ______ (can be either Open, Close, TWAP or VWAP value for each individual stock)
    #       Number of Shares (number of shares for a specific stock)
    #
    #       Savings vs _____ = (_______ - Model Price) * Number of Shares
    for i in range(num_stocks):
        savings_vs_open_buy.append((all_open[i] - buy_prices[i]) * abs(all_change_shares[i]))
        savings_vs_close_buy.append((all_close[i] - buy_prices[i]) * abs(all_change_shares[i]))
        savings_vs_twap_buy.append((all_twap[i] - buy_prices[i]) * abs(all_change_shares[i]))
        savings_vs_vwap_buy.append((all_vwap[i] - buy_prices[i]) * abs(all_change_shares[i]))

    for i in range(num_stocks):
        savings_vs_open_sell.append((sell_prices[i] - all_open[i]) * abs(all_change_shares[i]))
        savings_vs_close_sell.append((sell_prices[i] - all_close[i]) * abs(all_change_shares[i]))
        savings_vs_twap_sell.append((sell_prices[i] - all_twap[i]) * abs(all_change_shares[i]))
        savings_vs_vwap_sell.append((sell_prices[i] - all_vwap[i]) * abs(all_change_shares[i]))

    for i in range(num_stocks):
        twap_savings_vs_open.append((all_open[i] - all_twap[i]) * abs(all_change_shares[i]))
        twap_savings_vs_close.append((all_close[i] - all_twap[i]) * abs(all_change_shares[i]))
        vwap_savings_vs_open.append((all_open[i] - all_vwap[i]) * abs(all_change_shares[i]))
        vwap_savings_vs_close.append((all_close[i] - all_vwap[i]) * abs(all_change_shares[i]))


    return savings_vs_open_buy, savings_vs_close_buy, savings_vs_twap_buy, savings_vs_vwap_buy, savings_vs_open_sell, savings_vs_close_sell, savings_vs_twap_sell, savings_vs_vwap_sell, twap_savings_vs_open, twap_savings_vs_close, vwap_savings_vs_open, vwap_savings_vs_close

# Generates the graph/table data for the site
# Input:    data (a DataFrame representation of the Summary_Report.csv) 
#
# Output:   bar_chart_dict          (the dictionary/json representation of the graph data),
#           stacked_bar_chart_dict  (the dictionary representation of the stacked bar graph data),
#           table_dict              (the dictionary representation of the table data)
#           line_chart_dict         (the dictionary representation of the line chart - STILL WORK IN PROGRESS)
def create_graphs(data):
    # Custom color palette
    colors = ['#7962E7', '#A1EAFB', '#3DBEF6']
    # Bar titles for Open and Close both
    openClose_bars = ['TWAP Slippage', 'VWAP Slippage', 'BHM Slippage']
    
    num_stocks = 4

    # Average Open: (Sum of Open price of all stocks) / number of stocks
    average_open = data['AvgOpen']

    # Average Close: (Sum of Close price of all stocks) / number of stocks
    average_close = data['AvgClose']
    
    # Average Change in Shares (all positive): (Total number of shares for three stocks) / number of stocks
    average_shares = (abs(data['Change1']) + abs(data['Change2']) + abs(data['Change3']) + abs(data['Change4'])) / num_stocks
    
    # Each Value follows the following format:
    #   
    #   (Average Open/Close Value - Average Strategy Value) * Average Change in Shares
    #   For the Last one:
    #       (Average Open/Close Value - Average BHM Buy Value) * Average Change in Shares + (Average BHM Sell Value - Average Open/Close Value) * Average Change in Shares
    slip_twap_open = ( average_open - data['AvgTWAPVal'] ) * average_shares
    slip_twap_close = ( average_close - data['AvgTWAPVal'] ) * average_shares
    slip_vwap_open = ( average_open - data['AvgVWAPVal'] ) * average_shares
    slip_vwap_close = ( average_close - data['AvgVWAPVal'] ) * average_shares
    slip_lstm_open = ( average_open - data['AvgBHBuy'] ) * average_shares + ( data['AvgBHSell'] - average_open ) * average_shares
    slip_lstm_close = ( average_close - data['AvgBHBuy'] ) * average_shares + ( data['AvgBHSell'] - average_close ) * average_shares

    # Calculated Slippage Open values for TWAP, VWAP, and BHM
    open_values = [
        slip_twap_open,
        slip_vwap_open,
        slip_lstm_open,
    ]
    # Calculated Slippage Close values for TWAP, VWAP, and BHM
    close_values = [
        slip_twap_close,
        slip_vwap_close,
        slip_lstm_close,
    ]

    # Creates the bar chart dict to return (same as json)
    bar_chart_dict = {'openClose_bars':openClose_bars, 'open_values':open_values, 'close_values':close_values}

    # Stacked Bar Chart: Dollars Saved for Each Stock
    # Calculate Savings:
    savings_vs_open_buy, savings_vs_close_buy, savings_vs_twap_buy, savings_vs_vwap_buy, savings_vs_open_sell, savings_vs_close_sell, savings_vs_twap_sell, savings_vs_vwap_sell, twap_savings_vs_open, twap_savings_vs_close, vwap_savings_vs_open, vwap_savings_vs_close = calculate_savings_vs(
        num_stocks, 
        buy_prices=[data['BHBuy1'], data['BHBuy2'], data['BHBuy3'], data['BHBuy4']], 
        sell_prices=[data['BHSell1'], data['BHSell2'], data['BHSell3'], data['BHSell4']], 
        all_open=[data['Open1'], data['Open2'], data['Open3'], data['Open4']], 
        all_close=[data['Close1'], data['Close2'], data['Close3'], data['Close4']], 
        all_twap=[data['TWAPVal1'], data['TWAPVal2'], data['TWAPVal3'], data['TWAPVal4']], 
        all_vwap=[data['VWAPVal1'], data['VWAPVal2'], data['VWAPVal3'], data['VWAPVal4']], 
        all_change_shares=[data['Change1'], data['Change2'], data['Change3'], data['Change4']]
    )
    # Graph categories
    categories = ['Savings vs TWAP', 'Savings vs VWAP']
    # Get all savings values directly from Summary_Report.csv
    # Savings for Buy for stocks 1, 2, 3, and 4
    stock1_savings_buy = [savings_vs_twap_buy[0], savings_vs_vwap_buy[0]]
    stock2_savings_buy = [savings_vs_twap_buy[1], savings_vs_vwap_buy[1]]
    stock3_savings_buy = [savings_vs_twap_buy[2], savings_vs_vwap_buy[2]]
    stock4_savings_buy = [savings_vs_twap_buy[3], savings_vs_vwap_buy[3]]

    # Savings for Sell for stocks 1, 2, 3, and 4
    stock1_savings_sell = [savings_vs_twap_sell[0], savings_vs_vwap_sell[0]]
    stock2_savings_sell = [savings_vs_twap_sell[1], savings_vs_vwap_sell[1]]
    stock3_savings_sell = [savings_vs_twap_sell[2], savings_vs_vwap_sell[2]]
    stock4_savings_sell = [savings_vs_twap_sell[3], savings_vs_vwap_sell[3]]
    # Creates the stacked bar chart dict to return (same as json)
    stacked_bar_chart_dict = {
        'categories': categories,
        'stock_names': [data['Stock1'], data['Stock2'], data['Stock3'], data['Stock4']],
        'stock1_savings_buy': stock1_savings_buy,
        'stock2_savings_buy': stock2_savings_buy,
        'stock3_savings_buy': stock3_savings_buy,
        'stock4_savings_buy': stock4_savings_buy,
        'stock1_savings_sell': stock1_savings_sell,
        'stock2_savings_sell': stock2_savings_sell,
        'stock3_savings_sell': stock3_savings_sell,
        'stock4_savings_sell': stock4_savings_sell,
    }

    print("TWAP Savings vs Open")
    print(twap_savings_vs_open)
    print("TWAP Savings vs Close")
    print(twap_savings_vs_close)

    avg_savings_buy = ((sum(savings_vs_open_buy) / len(savings_vs_open_buy)) + (sum(savings_vs_close_buy) / len(savings_vs_close_buy))) / 2
    avg_savings_sell = ((sum(savings_vs_open_sell) / len(savings_vs_open_sell)) + (sum(savings_vs_close_sell) / len(savings_vs_close_sell))) / 2
    avg_twap_savings = ((sum(twap_savings_vs_open) / len(twap_savings_vs_open)) + (sum(twap_savings_vs_close) / len(twap_savings_vs_close))) / 2
    avg_vwap_savings = ((sum(vwap_savings_vs_open) / len(vwap_savings_vs_open)) + (sum(vwap_savings_vs_close) / len(vwap_savings_vs_close))) / 2

    stacked_bar_chart_savings_dict = {
        'savings_vs_twap_percent_buy': (avg_savings_buy - avg_twap_savings) / avg_twap_savings * 100,
        'savings_vs_vwap_percent_buy': (avg_savings_buy - avg_vwap_savings) / avg_vwap_savings * 100,
        'savings_vs_twap_percent_sell': (avg_savings_sell - avg_twap_savings) / avg_twap_savings * 100,
        'savings_vs_vwap_percent_sell': (avg_savings_sell - avg_vwap_savings) / avg_vwap_savings * 100,
    }

    # Table: Weekly Savings: A Snapshot of Consistency
    # Re-organizing data for table data
    table_dict = {
        # StockData: names of the four stocks in an array
        'StockData': [data['Stock1'], data['Stock2'], data['Stock3'], data['Stock4']],
        # SharesData: Change in shares data in an array for the four stocks
        'SharesData': [int(data['Change1']), int(data['Change2']), int(data['Change3']), int(data['Change4'])],
        # OpenData: Open values in an array for the four stocks
        'OpenData': [data['Open1'], data['Open2'], data['Open3'], data['Open4']], 
        # CloseData: Close values in an array for the four stocks
        'CloseData': [data['Close1'], data['Close2'], data['Close3'], data['Close4']],
        # TWAPValData: TWAP values in an array for the four stocks
        'TWAPValData': [data['TWAPVal1'], data['TWAPVal2'], data['TWAPVal3'], data['TWAPVal4']],
        # VWAPValData: VWAP values in an array for the four stocks
        'VWAPValData': [data['VWAPVal1'], data['VWAPVal2'], data['VWAPVal3'], data['VWAPVal4']],
        # BHBuyData: BHM Buy values in an array for the four stocks fetched from ML endpoint
        'BHBuyData': [data['BHBuy1'], data['BHBuy2'], data['BHBuy3'], data['BHBuy4']],
        # BHSellData: BHM Sell values in an array for the four stocks fetched from ML endpoint
        'BHSellData': [data['BHSell1'], data['BHSell2'], data['BHSell3'], data['BHSell4']],
        # SavingsVsOpenBuyData: Savings vs Open for Buy calculations for the four stocks in an array
        'SavingsVsOpenBuyData': savings_vs_open_buy,
        # SavingsVsOpenSellData: Savings vs Open for Sell calculations for the four stocks in an array
        'SavingsVsOpenSellData': savings_vs_open_sell,
        # SavingsVsCloseBuyData: Savings vs Close for Buy calculations for the four stocks in an array
        'SavingsVsCloseBuyData': savings_vs_close_buy,
        # SavingsVsCloseSellData: Savings vs Close for Sell calculations for the four stocks in an array
        'SavingsVsCloseSellData': savings_vs_close_sell,
        # SavingsVsTWAPBuyData: Savings vs TWAP for Buy calculations for the four stocks in an array
        'SavingsVsTWAPBuyData': savings_vs_twap_buy,
        # SavingsVsTWAPSellData: Savings vs TWAP for Sell calculations for the four stocks in an array
        'SavingsVsTWAPSellData': savings_vs_twap_sell,
        # SavingsVsVWAPBuyData: Savings vs VWAP for Buy calculations for the four stocks in an array
        'SavingsVsVWAPBuyData': savings_vs_vwap_buy,
        # SavingsVsVWAPSellData: Savings vs VWAP for Sell calculations for the four stocks in an array
        'SavingsVsVWAPSellData': savings_vs_vwap_sell,
        # AvgSavingsVsTWAPBuy and AvgSavingsVsTWAPSell: Average Savings vs TWAP for buy and sell
        'AvgSavingsVsTWAPBuy': sum(savings_vs_twap_buy) / len(savings_vs_twap_buy), 'AvgSavingsVsTWAPSell': sum(savings_vs_twap_sell) / len(savings_vs_twap_sell),
        # AvgSavingsVsVWAPBuy and AvgSavingsVsVWAPSell: Average Savings vs VWAP for buy and sell
        'AvgSavingsVsVWAPBuy': sum(savings_vs_vwap_buy) / len(savings_vs_vwap_buy), 'AvgSavingsVsVWAPSell': sum(savings_vs_vwap_sell) / len(savings_vs_vwap_sell)
    }

    # Line Chart: Weekly Savings (Placeholder)
    weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5']  # Placeholder weeks
    savings = [1000, 1500, 1200, 1700, 2000]  # Placeholder savings
    line_chart_dict = {'weeks':weeks, 'savings':savings}

    return bar_chart_dict, stacked_bar_chart_dict, stacked_bar_chart_savings_dict, table_dict, line_chart_dict

@api_view(['GET'])
def firm_view(request):
    # Gathers the request from the url to get the firm name
    firm_name = request.GET.get('firm_name', 'Unknown')
    # Gathers the firm data from the csv
    firm_data = df[df['FileName'] == firm_name]

    # If ther csv does not have data for this firm:
    if firm_data.empty:
        return HttpResponse("No data found for the specified firm.", status=404)

    # Calls the create_graphs function to form all the dictionaries/jsons for the graphs
    bar_chart_html, stacked_bar_chart_html, stacked_bar_chart_savings_dict, table_html, line_chart_html = create_graphs(firm_data.iloc[0])

    # Get the top 4 stocks for this firm (top two increase and decrease in shares)
    top_stocks = [firm_data.iloc[0]['Stock1'], firm_data.iloc[0]['Stock2'], firm_data.iloc[0]['Stock3'], firm_data.iloc[0]['Stock4']]
    
    # Calculate average shares traded per week
    total_shares = [abs(firm_data.iloc[0]['Change1']), abs(firm_data.iloc[0]['Change2']), abs(firm_data.iloc[0]['Change3']), abs(firm_data.iloc[0]['Change4'])]

    # Generates the analysis text for the firm based on its stock holdings and their change in holdings values
    analysis_text = (
        f"At Blockhouse, we understand that portfolio rebalancing can be costly, especially during volatile periods. "
        f"Our machine learning models deliver real-time insights to optimize trades, minimize costs, and maximize returns. "
        f"According to your 13-F filings, the stocks with the largest net increase in holdings were "
        f"**{top_stocks[0]} (+{total_shares[0]})** and **{top_stocks[1]} (+{total_shares[1]})**, and the stocks with the largest net decrease in holdings were "
        f"**{top_stocks[2]} (-{total_shares[2]})** and **{top_stocks[3]} (-{total_shares[3]})**."
        f"We’ve analyzed these position changes to identify cost-saving opportunities, focusing on slippage, market impact, "
        f"bid-ask spread, and commissions."
    )
    
    # Returns all of the outputs in json format
    return render(request, 'firm-report.html', {
        'firm_name': firm_name,
        'bar_chart_html': bar_chart_html,
        'stacked_bar_chart_html': stacked_bar_chart_html,
        'table_html': table_html,
        'line_chart_html': line_chart_html,
        'analysis_text': analysis_text,
        'firm_data': firm_data.to_dict(orient='records')[0],
        'stacked_bar_chart_savings_dict': stacked_bar_chart_savings_dict,
    })

def firm_graph_data(request):
    firm_name = request.GET.get('firm_name', 'Unknown')
    firm_data = df[df['FileName'] == firm_name]

    bar_chart_dict, stacked_bar_chart_dict, stacked_bar_chart_savings_dict, table_dict, line_chart_dict = create_graphs(firm_data.iloc[0])

    # Get the top 3 stocks for this firm
    top_stocks = [firm_data.iloc[0]['Stock1'], firm_data.iloc[0]['Stock2'], firm_data.iloc[0]['Stock3'], firm_data.iloc[0]['Stock4']]
    
    # Calculate average shares traded per week
    total_shares = [abs(firm_data.iloc[0]['Change1']), abs(firm_data.iloc[0]['Change2']), abs(firm_data.iloc[0]['Change3']), abs(firm_data.iloc[0]['Change4'])]

    analysis_text = (
        f"At Blockhouse, we understand that portfolio rebalancing can be costly, especially during volatile periods. "
        f"Our machine learning models deliver real-time insights to optimize trades, minimize costs, and maximize returns. "
        f"According to your 13-F filings, the stocks with the largest net increase in holdings were "
        f"**{top_stocks[0]} (+{total_shares[0]})** and **{top_stocks[1]} (+{total_shares[1]})**, and the stocks with the largest net decrease in holdings were "
        f"**{top_stocks[2]} (-{total_shares[2]})** and **{top_stocks[3]} (-{total_shares[3]})**."
        f"We’ve analyzed these position changes to identify cost-saving opportunities, focusing on slippage, market impact, "
        f"bid-ask spread, and commissions."
    )
    
    response_data = {
        'firm_name': firm_name,
        'bar_chart_html': bar_chart_dict,
        'stacked_bar_chart_html': stacked_bar_chart_dict,
        'line_chart_html': line_chart_dict,
        'table_html': table_dict,
        'analysis_text': analysis_text,
        'firm_data': firm_data.to_dict(orient='records')[0],
        'stacked_bar_chart_savings_html': stacked_bar_chart_savings_dict,
    }
    
    return JsonResponse(response_data)

@api_view(['GET'])
def firm_list(request):
    firm_links = [
        f'<li><a href="/api/firms/firm-list/firm?firm_name={row["FileName"]}">{row["FileName"]}</a></li>'
        for index, row in df.iterrows()
    ]
    firm_links_str = '\n'.join(firm_links)
    return render(request, 'index-firms.html', {'firm_links': firm_links_str})

@api_view(['GET'])
def get_firm_list(request):
    firm_links = [ row['FileName'] for index, row in df.iterrows() ]
    return JsonResponse({'firm_names': firm_links})


@api_view(['GET'])
def book_call(request):
    return redirect("https://calendly.com/aaditya_bhc/30min")
