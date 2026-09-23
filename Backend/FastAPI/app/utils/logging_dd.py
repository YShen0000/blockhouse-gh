import logging
import sys
import json
from app.config.settings import Settings

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.model.content_encoding import ContentEncoding
from datadog_api_client.v2.model.http_log import HTTPLog
from datadog_api_client.v2.model.http_log_item import HTTPLogItem

settings = Settings()

# Set up the Datadog API client
config = Configuration()
config.api_key['DD-API-KEY'] = settings.DD_API_KEY
print('DD_API_KEY: ', settings.DD_API_KEY)
config.host = 'https://http-intake.logs.datadoghq.com'
api_client = ApiClient(configuration=config)
logs = LogsApi(api_client)

# Set up logging to file and terminal
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(filename="./app.log", mode="w"),
        logging.StreamHandler(sys.stdout)
    ]
)

# # Set up the logger for Uvicorn to use
# logger = logging.getLogger("uvicorn")
# logger.handlers = logging.getLogger().handlers
# logger.info('Starting the app logging...')

# Define a custom logging handler that sends logs to Datadog
class DatadogHandler(logging.Handler):
    def emit(self, record):
        # # Ignore debug messages
        # if record.levelno == logging.DEBUG:
        #     return

        toJson = json.dumps(
            {
                "python-logging": {
                    "py-env": settings.DD_LOGGING_ENV,
                    "py-message": record.getMessage(),
                    "py-status": record.levelname.lower(),
                    "py-logger": record.name,
                    "py-stacktrace": record.exc_info,
                    "py-exception": record.exc_text,
                    "py-line": record.lineno,
                    "py-file": record.filename,
                    "py-function": record.funcName,
                    "py-level": record.levelno,
                    "py-path": record.pathname,
                    "py-thread": record.thread,
                    "py-threadName": record.threadName,
                    "py-process": record.process,
                    "py-processName": record.processName,
                    "py-args": record.args,
                    "py-msecs": record.msecs,
                    "py-relativeCreated": record.relativeCreated,
                    "py-created": record.created,
                    "py-module": record.module,
                }
            }

        )

        # Send the log to Datadog using the Logs API
        try:
            body = HTTPLog(
                [
                    HTTPLogItem(
                        ddsource="Python",
                        ddtags=f"env:{settings.DD_LOGGING_ENV}",
                        hostname=settings.DD_HOSTNAME,
                        message= toJson,
                        service=settings.DD_SERVICE,
                        status=record.levelname.lower()
                    ),
                ]
            )

            logs.submit_log(content_encoding=ContentEncoding.DEFLATE, body=body)
            # print(response)

        except Exception as e:
            print(f"Error sending log to Datadog: {e}")


# Set up the logger for Uvicorn to use
logger = logging.getLogger("uvicorn")
# logger.handlers = logging.getLogger().handlers
logger.info('Starting the app logging...')
logger.addHandler(DatadogHandler())