import pandas as pd
from django.db.models import F, Avg
from Analytics.models import Trade, Market_Prices

from Chatbot.Functions.utils import default_start_end_dates, build_chart
from Chatbot.Functions import trade_vs_trace


def trade_vs_trace_chart(file_id, start_date=None, end_date=None):
    start_date, end_date = default_start_end_dates(start_date, end_date)

    tr_vs_tc = trade_vs_trace(file_id, start_date, end_date)

    final_result = []

    for row in tr_vs_tc["data"]["rows"]:
        date = row[0]
        your_trade_yield = float(row[1])
        average_trace_yield = float(row[2])
        # yield_differential = float(row[3])

        group = {}
        group["groupName"] = date

        values = []

        values.append({
            "category": "Your Trade Yield",
            "value": your_trade_yield
        })

        values.append({
            "category": "Average TRACE Yield",
            "value": average_trace_yield
        })

        # values.append({
        #     "category": "Yield Differential",
        #     "value": yield_differential
        # })

        group["values"] = values

        final_result.append(group)

    chart = build_chart(final_result, "grouped_bar_chart")

    return chart