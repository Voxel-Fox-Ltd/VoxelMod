from datetime import timedelta
import re


__all__ = (
    "get_datetime_until",
)


def get_datetime_until(time: str) -> timedelta:
    """
    Parse a duration string. If no duration qualifier is given, the default is days.

    Parameters
    ----------
    time : str
        The time that you want to parse.

    Returns
    -------
    datetime.timedelta
        A delta of the time.
    """

    # If a duration qualifier is not provided, assume days
    if time.isdigit():
        return timedelta(days=int(time))

    # Matches any digit followed by any of s, m, h, d, or y (seconds, month, hours, days, or year)
    pattern = r"(?:(?P<length>\d+)(?P<period>[smhdy]) *)"

    # If no match is found, the default time is 28 days
    if not re.match(f"^{pattern}+$", time):
        return timedelta(days=28)

    # Get the matches from the string
    matches = re.finditer(pattern, time.replace(' ', '').lower())
    builder = timedelta(seconds=0)

    # Loop through each match found and add their parsed time to the builder
    # This allows for entries such as '1d5h' to be added
    length_str: str
    period: str
    period_map = {
        "y": "years",
        "d": "days",
        "h": "hours",
        "m": "minutes",
        "s": "seconds",
    }
    for m in matches:
        length_str, period = m.group("length"), m.group("period")
        length = int(length_str)
        builder += timedelta(**{period_map[period[0]]: length})
    return builder
