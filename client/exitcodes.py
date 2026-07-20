# Copyright (c) 2026, Corelight. All rights reserved.
#
# See COPYING for license information.

"""Curated process exit codes for automation-friendly output.

These are only surfaced when the exit-code taxonomy is enabled (automation
mode). In legacy mode every nonzero code collapses to 1; see client.util.fail.
"""

SUCCESS = 0
GENERIC = 1
USAGE = 2
CONNECT = 3
AUTH = 4
NOT_FOUND = 5
SERVER = 6
CONFIRMATION = 7
VERSION_UNSUPPORTED = 8


def classify_status(status):
    """
    Maps an HTTP status code to a taxonomy exit code.

    status (int or None): The HTTP status of a failed response.

    Returns: The matching exit code; GENERIC if the status is not an error we
    map specifically (or is None).
    """
    if status is None:
        return GENERIC

    if status in (401, 403):
        return AUTH

    if status == 404:
        return NOT_FOUND

    if 500 <= status < 600:
        return SERVER

    return GENERIC
