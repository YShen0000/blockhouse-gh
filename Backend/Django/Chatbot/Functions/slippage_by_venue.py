from Chatbot.Functions.utils import build_table


def slippage_by_venue(file_id):
    data = [
        {
            "Venue": "Bloomberg",
            "Avg Slippage (bips)": 16.3,
            "% Notional Traded": "42.5%",
        },
        {
            "Venue": "Tradeweb",
            "Avg Slippage (bips)": 21.3,
            "% Notional Traded": "21.9%",
        },
        {"Venue": "Trumid", "Avg Slippage (bips)": 18.9, "% Notional Traded": "10.3%"},
        {
            "Venue": "MarketAxess",
            "Avg Slippage (bips)": 12.1,
            "% Notional Traded": "25.3%",
        },
    ]
    return build_table(data)
