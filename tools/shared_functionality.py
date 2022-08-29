"""This module houses functions that are used by both clients and servers."""
from datetime import datetime

from .constants import Actions


def get_now_time() -> float:
    """Get the current time as a float.

    Returns:
        float: Current UNIX timestamp.
    """
    # Get the current time.
    now = datetime.now()
    # Format to a float.
    timestamp = datetime.timestamp(now)

    return timestamp


def int_to_enum(input: int) -> Actions:
    """Given an integer, return the corresponding Actions enum.

    Args:
        input (int): A value from the client or server.

    Returns:
        Actions: The corresponding enum for the integer.
    """
    # Check in Actions for a match.
    for item in Actions:
        # If there is a match...
        if input == item.value:
            # ...return the enum.
            return item

    # Else return an error.
    return Actions.NOT_A_VALID_INTEGER
