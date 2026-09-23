from Chatbot.Functions.calculate_slippage import calculate_slippage

from Chatbot.Functions.utils import default_start_end_dates, build_chart


def calculate_slippage_chart(file_id, start_date=None, end_date=None):
    start_date, end_date = default_start_end_dates(start_date, end_date)

    res = calculate_slippage(file_id, start_date, end_date)

    slippage, price_deviation, trade_completeness = [], [], []

    for row in res["data"]["rows"]:
        slippage.append([row[0], row[1]])

        price_deviation.append([row[0], row[2]])

        trade_completeness.append([row[0], row[3]])

    final_result = {
        "slippage": slippage,
        "price_deviation": price_deviation,
        "trade_completeness": trade_completeness
    }

    chart = build_chart(final_result, "line")

    return chart
