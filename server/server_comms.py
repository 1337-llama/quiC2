"""This module handles communication functionality on the server side."""
import logging
import sys
from typing import Tuple

from c2_dealer import QuiC2Database
from tools.constants import Actions


# Ignore all other loggers from imported modules.
loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
for logger in loggers:
    ql = logging.getLogger(logger.name)
    ql.disabled = True
# This base logger can be imported into multiple server modules.
bls = logging
bls.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                format='%(asctime)s %(levelname)s: %(message)s')


def respond_to_sdr(db_con: QuiC2Database,
                   stream_id: int, value: Actions) -> Tuple[Actions, list]:
    """Respond to a StreamDataReceived QuicEvent.

    Args:
        db_con (QuiC2Database): A connection to the database.
        stream_id (int): The stream ID of the current stream.  This uniquely
            identifies the client.
        value (Actions): The enum value received by the server.

    Returns:
        Actions: Return the appropriate response for the client.
        list: A list of commands for the client to perform.
    """
    # TODO need to actually handle the stream_id values - this may change the
    # response based on whether or not this has been seen, if it's not a
    # "defined" member of the "team", etc.

    # Add this stream_id to the database (if it doesn't already exist).
    added = db_con.insert_new_stream_id(stream_id)
    if added:
        bls.info(f'Add new stream_id {stream_id} to the database')

    if value != Actions.CLIENT_HELLO:
        bls.info(f'{stream_id} info: {value.name}')

    # Respond based on the message received.
    match value:
        # Initial message sent from the client on initial connection.
        case Actions.CLIENT_HELLO:
            # Check the database for any commands for this client.
            cmds, error = db_con.sel_and_del_cmd(stream_id)
            if not error and cmds:
                bls.debug(f'Client {stream_id} has commands to process')
                return Actions.SERVER_SEES_HELLO, cmds

            # Check the database for any files to send.
            file_send, error = db_con.sel_and_del_file_send(stream_id)
            if not error and file_send:
                bls.debug(f'Client {stream_id} needs a file transfer')
                # Return as a list to match the type description.  Only one
                # element will ever be returned.
                return Actions.SERVER_FILE_SEND, [file_send]

            # Check the database for any files to receive.
            file_recv, error = db_con.sel_and_del_file_recv(stream_id)
            if not error and file_recv:
                bls.debug(f'Client {stream_id}: server requests file')
                # Return as a list to match the type description.  Only one
                # element will ever be returned.
                return Actions.SERVER_FILE_RECV, [file_recv]

            return Actions.NO_RESPONSE_NEEDED, []

        case Actions.CLIENT_RESPONSE:
            # The caller will print the response from the client.
            return Actions.SERVER_SEES_RESPONSE, []

        case Actions.FILE_NOT_FOUND:
            # The client did not have the file requested by the server.
            return Actions.FILE_NOT_FOUND, []

        # This handles anything that wasn't handled explicitly above.
        case _:
            bls.warning('This value is not handled yet...')
            return Actions.NOT_A_VALID_INTEGER, []
