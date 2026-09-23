import datetime

def build_table(response):
    headers = [[key] for key in response[0].keys()]
    rows = []
    for item in response:
        row = []
        for key, value in item.items():
            if isinstance(value, datetime.date):
                row.append(value.strftime('%Y-%m-%d'))
            elif isinstance(value, (int, float)):
                row.append(f"{value:.2f}")
            else:
                row.append(value)
        rows.append(row)

    table = {
        "type": "table",
        "chart_type": None,
        "data": {
            "headers": headers,
            "rows": rows
        },
        "sender": "assistant"
    }

    return table