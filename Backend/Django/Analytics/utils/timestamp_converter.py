from dateutil import parser
import pytz


def convert_to_datetime(date_string, time_string, default_timezone='America/New_York'):
    """
    Convert a date string and a time string into a UTC datetime object.
    Supports a wide range of date and time formats and converts to UTC.

    Args:
    date_string (str): Date in various possible formats.
    time_string (str): Time in various possible formats.
    default_timezone (str): The timezone name for date and time if not included in strings.

    Returns:
    datetime or None: UTC datetime object corresponding to the given date and time, or None if an error occurs.
    """
    try:
        datetime_string = f"{date_string} {time_string}"
        datetime_obj = parser.parse(datetime_string)

        # If the datetime object doesn't have timezone information, assume default timezone
        if datetime_obj.tzinfo is None or datetime_obj.tzinfo.utcoffset(datetime_obj) is None:
            timezone = pytz.timezone(default_timezone)
            datetime_obj = timezone.localize(datetime_obj)

        # Convert to UTC
        utc_datetime_obj = datetime_obj.astimezone(pytz.utc)
        return utc_datetime_obj
    except Exception as e:  # Catching a broader exception to handle both ValueError and potential pytz exceptions
        print(f"Error converting to datetime: {e}")
        return None
