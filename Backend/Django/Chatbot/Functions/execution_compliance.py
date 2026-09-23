from Chatbot.Functions.utils import build_table


def execution_compliance(file_id):
    data = [
        {"CUSIP": "912810SZ41", "Timestamp": "9:44 1/2/2024", "Notional Trade Size (in millions USD)": 85.52, "Trade Direction": "BUY", "Counterparty": "Citibank", "Trade Price": 94.18, "Estimated Best Execution Price": 93.55},
        {"CUSIP": "912810SZ41", "Timestamp": "15:01 1/2/2024", "Notional Trade Size (in millions USD)": 91.83, "Trade Direction": "BUY", "Counterparty": "Citibank", "Trade Price": 94.19, "Estimated Best Execution Price": 94.10},
        {"CUSIP": "912810SZ41", "Timestamp": "15:43 1/2/2024", "Notional Trade Size (in millions USD)": 89.44, "Trade Direction": "SELL", "Counterparty": "Citibank", "Trade Price": 94.12, "Estimated Best Execution Price": 95.2}
    ]
    return build_table(data)

