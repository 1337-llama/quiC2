"""This module handles communication functionality on the client side."""
import logging
import sys
from typing import Tuple

from client.cl_functions import stock_command, custom_command
from tools.constants import Actions


# Ignore all other loggers from imported modules.
loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
for logger in loggers:
    ql = logging.getLogger(logger.name)
    ql.disabled = True
# This base logger can be imported into multiple client modules.
blc = logging
blc.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                format='%(asctime)s %(levelname)s: %(message)s')


def respond_to_sdr(value: Actions, data: str) -> Tuple[bytes, Actions]:
    """Respond to a StreamDataReceived QuicEvent.

    Args:
        value (Actions): The enum value received by the client.
        data (str): The data received by the client.

    Returns:
        bytes: Output of command to be passed to the server.
        Actions: Return the appropriate action performed by client.
    """
    if value != Actions.NO_RESPONSE_NEEDED:
        blc.info(f'Info received:  {value}')

    match value.value:
        # This range encompasses all "stock" commands that can be used for
        # basic data gathering (does not include custom commands sent by the
        # server).
        case num if (Actions.WHOAMI.value <= num
                     <= Actions.NOT_A_VALID_INTEGER.value - 1):
            blc.debug('Prepare to execute stock command')
            output = stock_command(value)
            return output, Actions.CLIENT_RESPONSE

        # This value corresponds to executing a custom command.
        case num if num == Actions.CUSTOM.value:
            blc.debug('Prepare to execute custom command')
            output = custom_command(data)
            return output, Actions.CLIENT_RESPONSE

        case num if num == Actions.NO_RESPONSE_NEEDED.value:
            return b'', Actions.NO_RESPONSE_NEEDED

        # Something unexpected happened.
        case _:
            blc.debug(f'Value is unexpected:  {value.value}.  CLIENT_FAIL')
            return b'error', Actions.CLIENT_FAIL
