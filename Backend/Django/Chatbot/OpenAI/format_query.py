from django.conf import settings

from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Assistant Information
# BlockhouseFormatV1
assistant_id = "asst_3JS10mQN2fUAQoq70d4PvYA4"
instructions = "You are an AI assistant of Blockhouse, a financial platform that helps companies get insights into their financial metrics. You have to provide useful entity extraction like start date, end dates, asset classes or other relevant information from the query in a json format. use snakecase formatting and keep intent of user as a mandatory field in the output. The intent should be a sentence and \
    provide start_date and end_date in ISO 8601 format with utc timezone."


def format_query(input_query, calculated_response):
    thread = client.beta.threads.create()
    thread_id = thread.id

    query = f"user query: {input_query}, answer: {calculated_response}"

    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=query
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    run_id = run.id

    messages = check_messages(thread_id, run_id)

    last_message = messages[-1]["message"]

    return last_message


def check_messages(thread_id, run_id):
    run = client.beta.threads.runs.retrieve(
        thread_id=thread_id, run_id=run_id)

    run_status = run.status
    print("run_status", run_status)
    if run_status == "completed":
        message = client.beta.threads.messages.list(
            thread_id=thread_id, order="asc"
        )

        messages = [{
            'message': msg.content[0].text.value,
            'sender': msg.role,
        } for msg in message]

        return messages

    else:
        return check_messages(thread_id, run_id)
