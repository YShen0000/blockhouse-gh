def build_chart(response, chart_type=None):
    chart = {
        "type": "chart", # [line, bar, grouped_bar_chart]
        "chart_type": chart_type,
        "data": response,
        "sender": "assistant"
    }

    return chart
