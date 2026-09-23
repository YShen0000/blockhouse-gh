from Chatbot.Functions.utils import default_start_end_dates, build_chart
from Chatbot.Functions import calculate_tca_metrics

def tca_metrics_chart(file_id, start_date=None, end_date=None):
    start_date, end_date = default_start_end_dates(start_date, end_date)

    result = calculate_tca_metrics(file_id, start_date, end_date)

    final_result = []

    for row in result["data"]["rows"]:
        
        date = row[0]
        price_improvement = float(row[1])
        slippage = float(row[2])
        price_impact = float(row[3])

        group = {}
        group["groupName"] = date

        values = []

        values.append({
            "category": "Price Improvement",
            "value": price_improvement
        })

        values.append({
            "category": "Slippage",
            "value": slippage
        })

        values.append({
            "category": "Price Impact",
            "value": price_impact
        })

        group["values"] = values

        final_result.append(group)

        # final_result[date] = {
        #     "price_improvement": price_improvement,
        #     "slippage": slippage,
        #     "price_impact": price_impact
        # }
    
    chart = build_chart(final_result, "grouped_bar_chart")

    return chart
