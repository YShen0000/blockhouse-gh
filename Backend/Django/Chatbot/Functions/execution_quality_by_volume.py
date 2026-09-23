from Chatbot.Functions.utils import build_table


def execution_quality_by_volume(file_id):
    data = [
        {"Venue": "Bloomberg", "<$5M": 17.1, "$5 - 50M": 13.3, "$50M - 100M": 38.3},
        {"Venue": "Tradeweb", "<$5M": 12.3, "$5 - 50M": 17.9, "$50M - 100M": 58.4},
        {"Venue": "Trumid", "<$5M": 15.6, "$5 - 50M": 15.3, "$50M - 100M": 50.5},
        {"Venue": "MarketAxess", "<$5M": 11.2, "$5 - 50M": 23.1, "$50M - 100M": 40.8},
    ]
    return build_table(data)
