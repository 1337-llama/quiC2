# Introduction

This manual provides instructions for using quiC2.  The main program consists of three components: a dealer, a server, and a client.  Each of these modules will be explored in the sections that follow.

# The Dealer

The dealer component of quiC2 serves as the command-line interface for the operator.  The dealer can be used to add new commands, view responses, or select files to send to / receive from the client.

## Options

There are several options that the operator can select in order to interact with the dealer:

- `h` - provides a basic help screen to display possible input options
- `si` - view the current client that are connected to the server
- `cc` - choose a new with which to interact
- `nc` - send a new command to the chosen client
- `sc` - send a file from the server to the client
- `cs` - send a file from the client to the server
- `e` - used to exit the program

## Usage

> **NOTE:  It is important to have the dealer and the server running at the same time as their interactions are closely coupled.**

Once the dealer is started (with something similar to `python .\c2_dealer.py`), there are a variety of commands that can be utilized.  Entering an `h` (as shown above) will display these possibilities.

In order to view the current clients with which the server has established a connection, `si` must be entered.  This will also populate the list of available clients that can be chosen with the `cc` option.  

After a client is chosen, `nc`, `sc`, or `cs` can be used to send commands to or exchange files with the client.

Note that a command is sent from the server to the client *when the client checks in with the server*.  The command is not sent immediately upon being entered.  This is because of the nature of this framework:  the server relies upon the recent connection of the client to ensure traffic will be accepted by network intermediary devices (routers, firewalls, etc.).

### Entering Commands

There are two types of commands that can be utilized in quiC2: stock and custom.

- Stock commands are ordinary reconnaissance commands, such as `whoami`, `hostname` or `ls`.  An operator can directly select one of these commands to send to a client.
- Custom commands are typed in directly by the operator.  These can include any standard command that can be processed by PowerShell (on Windows) or a typical Linux shell.

Stock commands are requested by entering their corresponding numeric equivalent.  For example, when the operator enters `nc` for a new command, the option for `whoami` would require entering a value of `0`.  Custom commands are typed in by the operator after selecting `nc`.

### File Exchange

In order to exchange files, the options `sc` or `cs` must be entered.  A filename should be entered as `<file.ext>` if in the local directory or else `/<dir>/<file.ext>`.

# The Server

While the server operates as an independent process, there is no way to directly interact with it.  This is the purpose of the dealer.  The server will listen for connection attempts from various clients and log these clients in a backend database.  The database is shared with the dealer and is used to facilitate backend communications between the server and operator.

# The Client

Each client operates as an independent process on a host.  A basic hello message is sent to the server at a randomized interval along with identifying information.  The client performs no operations independently; the server must explicitly command the client to perform an operation.