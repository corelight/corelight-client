# Copyright (c) 2017, Corelight. All rights reserved.
#
# See COPYING for license information.

import getpass
import sys

# Debug level. See ``enableDebug()`` for values.
_DebugLevel = 0

def fatalError(msg, arg=None):
    """Reports a fatal error and aborts the process."""
    if arg:
        print("Fatal error: {} ({})".format(msg, arg), file=sys.stderr)
    else:
        print("Fatal error: {}".format(msg), file=sys.stderr)

    sys.exit(1)

def error(msg, arg=None):
    """Reports a non-fatal error."""
    if arg:
        print("Error: {} ({})".format(msg, arg), file=sys.stderr)
    else:
        print("Error: {}".format(msg), file=sys.stderr)

def infoMessage(msg, arg=None):
    """Reports a notice to the user."""
    if arg:
        print("Note: {} ({})".format(msg, arg), file=sys.stderr)
    else:
        print("Note: {}".format(msg), file=sys.stderr)

def enableDebug(level):
    """
    Enables debugging outout to standard error.

    level (int): 0 means no output. 1 shows the HTTP messages for all
    API operations, except retrieving meta data. 2 includes meta data
    as well.
    """
    global _DebugLevel
    _DebugLevel = level

def debugLevel():
    """Returns the current debug level."""
    return _DebugLevel

def debug(msg, level=1):
    """
    If debug output is enabled for the given level, prints a message to standard error.

    level (int): The debug level of the message.
    """
    if _DebugLevel >= level:
        print(msg, file=sys.stderr)

def appendUrl(baseUrl, appendedPath):
    """
    Concatinates 2 url paths, eliminating the trailing / from the first one, if required.

    This function is not compatible with query paramters or anything other than urlpaths.

    baseUrl (str): The base url to be appended to.

    appendedPath (str): The appended portion of the path.

    Returns: A new url with the full path.
    """
    if not baseUrl or len(baseUrl) <= 0:
        return appendedPath

    if not appendedPath or len(appendedPath) <= 0:
        return baseUrl

    if baseUrl.endswith("/") and appendedPath.startswith("/"):
        baseUrl = baseUrl[:len(baseUrl)-1]

    return baseUrl + appendedPath

def formatTuples(tuples):
    """
    Renders a list of 2-tuples into a column-aligned string format.

    tuples (list of (any, any): The list of tuples to render.

    Returns: A new string ready for printing.
    """
    if not tuples:
        return ""

    tuples = [(str(x), str(y)) for (x, y) in tuples]
    width = max([len(x) for (x, y) in tuples])

    fmt = "  {{:{}}} {{}}\n".format(width + 2)

    result = ""

    for (x, y) in tuples:
        result += fmt.format(x, y)

    return result

def getInput(prompt, password=False):
    """
    Prompts the user for an input string.

    prompt (str): A string to print out as prompt.

    password (bool): If True, disable echo for the user's input.
    """
    assert (sys.stdin.isatty() and sys.stdout.isatty())

    sys.stdout.write(prompt)
    sys.stdout.write(": ")
    sys.stdout.flush()

    if password:
        return getpass.getpass("").strip()
    else:
        return sys.stdin.readline().strip()

def promptUserCredentials(args):
    """
    Prompts the user for username and password credentials.

    args (ArgumentParser): The current arguments to the application.

    Returns: a list of equivalent command line arguments for the prompted details.
    """
    new_args = []

    if not args.user:
        args.user = getInput("User name")

        if args.user:
            new_args = ["--user", args.user] + new_args

    if not args.password:
        args.password = getInput("Password", password=True)

        if args.password:
            new_args = ["--password", args.password] + new_args

    return new_args