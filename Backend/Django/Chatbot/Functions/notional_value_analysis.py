from Chatbot.Functions.utils import build_table


def notional_value_analysis(file_id):
    data = [
        {
            "Bond Name": "JPM 5.35 06/01/34",
            "CUSIP": "46647PDR4",
            "Notional Value (in millions of USD)": 5.25,
            "Venue": "Tradeweb",
        },
        {
            "Bond Name": "JPM 5.299 07/24/29",
            "CUSIP": "US46647PDU75",
            "Notional Value (in millions of USD)": 5.65,
            "Venue": "Tradeweb",
        },
        {
            "Bond Name": "JPM 6.254 10/23/34",
            "CUSIP": "US46647PDY97",
            "Notional Value (in millions of USD)": 4.95,
            "Venue": "Tradeweb",
        },
        {
            "Bond Name": "JPM 5.336 01/23/35",
            "CUSIP": "US46647PEC68",
            "Notional Value (in millions of USD)": 5.35,
            "Venue": "Tradeweb",
        },
        {
            "Bond Name": "JPM 5.012 01/23/30",
            "CUSIP": "US46647PEB85",
            "Notional Value (in millions of USD)": 5.60,
            "Venue": "Tradeweb",
        },
    ]
    return build_table(data)
