from datetime import datetime, timedelta
from django.utils import timezone
from dateutil import parser


def parse_date(date_input):
    """
    Parses a date input (string or datetime) into a timezone-aware datetime object in UTC.
    If the input is already a datetime object, it ensures it is timezone-aware.

    :param date_input: The date input to parse.
    :return: A timezone-aware datetime object in UTC.
    """
    if isinstance(date_input, str):
        # Parse the string to datetime and make it timezone-aware, assuming it's in UTC if naive.
        date_parsed = parser.parse(date_input)
        if date_parsed.tzinfo is None or date_parsed.tzinfo.utcoffset(date_parsed) is None:
            date_parsed = timezone.make_aware(
                date_parsed, timezone=timezone.utc)
        return date_parsed
    elif isinstance(date_input, datetime):
        # Ensure the datetime is timezone-aware, assuming UTC if naive.
        if date_input.tzinfo is None or date_input.tzinfo.utcoffset(date_input) is None:
            return timezone.make_aware(date_input, timezone=timezone.utc)
        return date_input
    else:
        raise ValueError(
            "The date input must be a string or a datetime object.")


def default_start_end_dates(start_date=None, end_date=None, default_days=60):
    # TODO hardcode to 35 days for demo
    """
    Function to calculate default start and end dates based on input or default parameters,
    where start_date and end_date can be in multiple formats.

    :param start_date: input start date (default None) in string or datetime format
    :param end_date: input end date (default None) in string or datetime format
    :param default_days: default number of days to subtract from current date (default 7)
    :return: tuple of calculated start and end dates in datetime.datetime format with UTC timezone
    """

    # if start_date is not None:
    #     start_date = parse_date(start_date)
    # else:

    # if end_date is not None:
    #     end_date = parse_date(end_date)
    # else:

    end_date = timezone.now()
    start_date = timezone.now() - timedelta(days=default_days)
    return start_date, end_date
