from Chatbot.Functions.utils import build_table

def execution_quality_by_asset_class(file_id):
    data = [
        {"Venue": "Bloomberg", "Treasuries": 4.5, "Corporate IG": 12.4, "Corporate HY": 55.5},
        {"Venue": "Tradeweb", "Treasuries": 3.2, "Corporate IG": 8.3, "Corporate HY": 34.1},
        {"Venue": "Trumid", "Treasuries": 3.7, "Corporate IG": 15.0, "Corporate HY": 15.2},
        {"Venue": "MarketAxess", "Treasuries": 4.2, "Corporate IG": 10.1, "Corporate HY": 44.3}
    ]
    return build_table(data)