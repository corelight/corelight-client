# Copyright (c) 2017, Corelight. All rights reserved.
#
# See COPYING for license information.

import getpass
import json
import sys

import client.exitcodes

# Debug level. See ``enableDebug()`` for values.
_DebugLevel = 0

# Whether the curated exit-code taxonomy is active (automation mode).
_ExitCodesEnabled = False

# Error/output format: "text" (default) or "json".
_ErrorFormat = "text"


def enableExitCodes(enabled):
    """Enables or disables the curated exit-code taxonomy."""
    global _ExitCodesEnabled
    _ExitCodesEnabled = bool(enabled)


def exitCodesEnabled():
    """Returns whether the curated exit-code taxonomy is active."""
    return _ExitCodesEnabled


def setErrorFormat(fmt):
    """Sets the error/output format: 'text' or 'json'."""
    global _ErrorFormat
    _ErrorFormat = fmt


def errorFormat():
    """Returns the current error/output format ('text' or 'json')."""
    return _ErrorFormat


def parseTimeout(spec):
    """
    Parses a timeout spec into a (connect, read) tuple of floats.

    spec (str): Either a single number (applied to both connect and read) or
    "connect,read".

    Returns: A (connect, read) tuple of floats. Raises ValueError on bad input.
    """
    parts = str(spec).split(",")

    if len(parts) == 1:
        v = float(parts[0])
        return (v, v)

    if len(parts) == 2:
        return (float(parts[0]), float(parts[1]))

    raise ValueError("timeout must be 'N' or 'connect,read'")


def fail(code, title=None, description=None, diagnostics=None,
         http_status=None, retriable=False, attempts=1, legacy_lines=None):
    """
    Single funnel for terminal error exits.

    In JSON error-format mode, prints a structured envelope to stderr. In text
    mode, prints each entry of *legacy_lines* to stderr verbatim (so legacy
    output is preserved exactly). The process then exits with *code* when the
    taxonomy is enabled, otherwise with 1 (0 stays 0).
    """
    if _ErrorFormat == "json":
        envelope = {"code": code, "retriable": bool(retriable), "attempts": attempts}
        if http_status is not None:
            envelope["http_status"] = http_status
        if title:
            envelope["title"] = title
        if description:
            envelope["description"] = description
        if diagnostics:
            envelope["diagnostics"] = diagnostics
        json.dump({"error": envelope}, fp=sys.stderr)
        sys.stderr.write("\n")
    else:
        for line in (legacy_lines or []):
            print(line, file=sys.stderr)

    if _ExitCodesEnabled:
        sys.exit(code)
    else:
        sys.exit(0 if code == 0 else 1)


def fatalError(msg, arg=None):
    """Reports a fatal error and aborts the process."""
    if arg:
        line = "Fatal error: {} ({})".format(msg, arg)
    else:
        line = "Fatal error: {}".format(msg)

    fail(client.exitcodes.GENERIC, title=msg,
         description=(str(arg) if arg else None), legacy_lines=[line])

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