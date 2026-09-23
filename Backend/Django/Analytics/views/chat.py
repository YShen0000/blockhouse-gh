import csv
from io import StringIO
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from openai import OpenAI

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from Analytics.models import Market_Prices, Trade

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):  # contains experimental data, will clean up once we finalise the chatbot approach
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    try:
        file_id = data.get('fileId')

        if not file_id:
            return JsonResponse({'error': 'No file ID provided'}, status=400)

        # # Fetching data for the specified file
        # file_link = Uploads.objects.get(id=file_id).file_path

        # # Download the file from S3
        # response = requests.get(file_link)
        # content = response.content.decode('utf-8')
        # csv_reader = csv.DictReader(content.splitlines())

        # # Convert each row into a JSON string (or you could format it as plain text)
        # lines = [json.dumps(row) for row in csv_reader]

        # # Join the lines into a single string to prepare for upload
        # file_content = "\n".join(lines).encode('utf-8')

        # # Upload the file to OpenAI
        # file = client.files.create(file=file_content, purpose="assistants")

        # class CustomJSONEncoder(DjangoJSONEncoder):
        #     def default(self, obj):
        #         if isinstance(obj, datetime):
        #             return obj.isoformat()
        #         return super().default(obj)

        trades = Trade.objects.filter(file_id=file_id).values()
        trades_csv_io = StringIO()
        # Assuming non-empty queryset; adjust as needed
        fieldnames = trades[0].keys()
        writer = csv.DictWriter(trades_csv_io, fieldnames=fieldnames)
        writer.writeheader()
        for trade in trades:
            writer.writerow(trade)
        trades_csv_content = trades_csv_io.getvalue().encode('utf-8')

        # Example for converting Market_Prices model data to CSV
        market_prices = Market_Prices.objects.all().values()
        market_prices_csv_io = StringIO()
        fieldnames = market_prices[0].keys()  # Adjust as needed
        writer = csv.DictWriter(market_prices_csv_io, fieldnames=fieldnames)
        writer.writeheader()
        for price in market_prices:
            writer.writerow(price)
        market_prices_csv_content = market_prices_csv_io.getvalue().encode('utf-8')

        # Upload the CSV data to OpenAI
        trade_prices_file = client.files.create(
            file=trades_csv_content, purpose="assistants")
        market_prices_file = client.files.create(
            file=market_prices_csv_content, purpose="assistants")

        # Creating an assistant
        instructions = f"You have access to trades_dataset file_id: {trade_prices_file.id} and market_prices dataset file_id: {market_prices_file.id}. You have access to these files and answer any user queries accordingly. \
                        Both the files are csvs, the trades_dataset contains columns cusip, trade_timestamp, trade_size, face_value, asset_inventory, fill, execution_time, trade_price, trade_direction, counterparty, trader. \
                        The market_prices dataset contains columns cusip, trade_timestamp, trade_price. \
                    If a trade references one of the metrics below, please take the following steps to calculate the relevant values: \
                    *Note: Assume that the benchmark price referred to in all of these calculations is the bid ask midpoint (BAM) or the market price 5 minutes after the trade occurs, unless otherwise specified by trader or instructions* \
                    - NBBO (national best bid offer) - Refers to two values, the bid (sell) and ask (buy) price of the market \
                    - BAM (bid ask midpoint) - Is calculated as the average of the bid and ask prices in the market prices file. If bid / ask is not given, assume the given price is the BAM \
                    - Slippage / Markout / Implementation Shortfall  - all refer the difference between the trade price and the market price. For a BUY order, this metric  “= trade price - benchmark”. For SELL order this metric  “= benchmark - trade price” \
                    - Effective Cost - same as implementation shortfall calculation, except the benchmark is the BAM at the time of the trade \
                    - Realized Cost - same as implementation shortfall using the post-trade benchmark \
                    - Price Impact - “Effective Cost - Realized Cost” \
                    - Price improvement  - for BUY orders, “= market ask (at time of trade) - trade price”. For SELL orders “= trade price - market bid (at time of trade)”. If bid / ask is not given in file, please tell the trader that it has not been supplied and that you cannot finish the calculation without those values \
                    - Bid ask spread - “ask price - bid price”, can refer to the bid/ask spread of the market or the trader. If bid / ask is not given in file, please tell the trader that it has not been supplied and that you cannot finish the calculation without those values \
                    - TWAP - refers to the time weighted average price. TWAP is calculated by dividing a specified time period into intervals, computing the average price for each interval, weighting these averages by the time duration, and then summing up the weighted prices, which is finally divided by the total time. \
                    - VWAP - refers to the volume weighted average price. VWAP is determined by calculating the product of each trade's price and volume, summing these volume-weighted prices, summing the total volume of shares traded, and then dividing the sum of volume-weighted prices by the total volume. This provides an average price reflecting the impact of trade volumes over a specified time period. \
                    - Fills / Fill Quality / Fill Time - Refers to completed trades. Fill quality refers to the characteristics around the implementation shortfall, whether it is positive or negative, etc. Fill time refers to the time it takes for the trade to be executed \
            "

        # assistant = client.beta.assistants.create(
        #     name="BlockhouseGPT",
        #     instructions=instructions,
        #     model="gpt-3.5-turbo-1106",
        #     tools=[{"type": "retrieval"}],
        #     file_ids=[trade_prices_file.id, market_prices_file.id]
        # )

        assistant_id = "asst_7c0rKP59pE26qagpLBzfm7z7"

        # Create a new thread
        thread = client.beta.threads.create()
        thread_id = thread.id
        # Replace with your actual assistant ID
        # assistant_id = "asst_bMy5ZOwX4pdCFTZlIqyiJs0i"
        # assistant_id = "asst_73dlMPtjQDdOFQR2WMAxBKSR"

        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content="hello"
        )

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            instructions=instructions
        )

        run_id = run.id

        return JsonResponse({'thread_id': thread_id, "run_id": run_id, "assistant_id": assistant_id}, status=201)

    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({'error': str(e)}, status=400)