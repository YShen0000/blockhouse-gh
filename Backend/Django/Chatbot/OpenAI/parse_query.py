from datetime import date
import time
import json
from django.conf import settings
import logging

from openai import OpenAI

# Set up logging
logger = logging.getLogger("django")

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Assistant Information
# BlockhouseV1
assistant_id = "asst_vqh5zL9X08uSv7RUWm7paF2P"


def parse_query(query):
    logger.info("Starting to parse query")
    try:
        thread = client.beta.threads.create()
        thread_id = thread.id

        query = f"{query} and todays date is {date.today()}"

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            # instructions=instructions
        )

        run_id = run.id

        messages = check_messages(thread_id, run_id)

        last_message = json.loads(messages[-1]["message"])

        intent, start_date, end_date = last_message['intent'], last_message['start_date'], last_message['end_date']

        logger.info(f"Query parsed successfully with intent: {intent}")
        return intent, start_date, end_date
    except Exception as e:
        logger.error(f"Failed to parse query: {e}")
        raise

def check_messages(thread_id, run_id):
    logger.info(f"Checking messages for thread_id: {thread_id} and run_id: {run_id}")
    try:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run_id)

        run_status = run.status

        if run_status == "completed":
            message = client.beta.threads.messages.list(
                thread_id=thread_id, order="asc"
            )

            messages = [{
                'message': msg.content[0].text.value,
                'sender': msg.role,
            } for msg in message]

            logger.info("Messages retrieved successfully")
            return messages

        else:
            logger.info("Run status not completed, retrying")
            time.sleep(1)  # Wait for 1 second before retrying
            return check_messages(thread_id, run_id)
    except Exception as e:
        logger.error(f"Error checking messages: {e}")
        raise

