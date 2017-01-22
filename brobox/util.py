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
        print("Fatal error: {} ({})".format(msg, arg))
    else:
        print("Fatal error: {}".format(msg))

    sys.exit(1)

def error(msg, arg=None):
    """Reports a non-fatal error."""
    if arg:
        print("Error: {} ({})".format(msg, arg))
    else:
        print("Error: {}".format(msg))

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
