from Chatbot.Functions.utils import build_chart
bond_data = {
    "Bond Name": ["06/01/34", "07/24/29", "10/23/34", "01/23/35", "01/23/30"],
    "Estimated Execution Price": [97.7, 98.8, 98.1, 97.9, 97.2]
}

def execution_price_chart(file_id, start_date=None, end_date=None):
    trading_volume_bar_chart_data = list(zip(bond_data["Bond Name"], bond_data["Estimated Execution Price"]))
    chart = build_chart(trading_volume_bar_chart_data, "bar")

    return chart
