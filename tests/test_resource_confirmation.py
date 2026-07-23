# Copyright (c) 2026, Corelight. All rights reserved.
#
# See COPYING for license information.

import io
import json
import sys
import unittest
from unittest import mock

from client import exitcodes
from client import util
import client.resource as resource


class _Args:
    def __init__(self, **kw):
        self.noblock = kw.get("noblock", True)
        self.automation = kw.get("automation", True)
        self.assume_yes = kw.get("assume_yes", False)
        self.async_nowait = False
        self.json = False


class _Session:
    def __init__(self, args):
        self._args = args

    def arguments(self):
        return self._args


def _response(status=200):
    r = mock.Mock()
    r.status_code = status
    r.reason = "OK"
    return r


class TestConfirmationGate(unittest.TestCase):
    def setUp(self):
        util.enableExitCodes(True)
        util.setErrorFormat("text")

    def tearDown(self):
        util.enableExitCodes(False)
        util.setErrorFormat("text")

    def test_automation_without_assume_yes_exits_7(self):
        args = _Args(automation=True, assume_yes=False, noblock=True)
        session = _Session(args)
        resource_meta = {"response-fields": [], "responses": []}
        data = {"message": "delete everything?", "confirmation-url": "https://x/confirm"}
        with self.assertRaises(SystemExit) as cm:
            resource._processResponse(session, resource_meta, _response(200),
                                      "confirmation", "no-cache", data)
        self.assertEqual(cm.exception.code, exitcodes.CONFIRMATION)

    @mock.patch("client.resource.process")
    def test_automation_with_assume_yes_reissues(self, mock_process):
        args = _Args(automation=True, assume_yes=True, noblock=True)
        session = _Session(args)
        resource_meta = {"response-fields": [], "responses": []}
        data = {"message": "delete everything?", "confirmation-url": "https://x/confirm"}
        resource._processResponse(session, resource_meta, _response(200),
                                  "confirmation", "no-cache", data)
        mock_process.assert_called_once()
        self.assertEqual(mock_process.call_args[0][2], "https://x/confirm")

    @mock.patch("client.resource.process")
    def test_noblock_without_automation_still_reissues(self, mock_process):
        # Additive guarantee: plain --noblock WITHOUT automation must keep
        # today's auto-confirm behavior (fall through to reissue), with no
        # fail() / SystemExit.
        args = _Args(automation=False, assume_yes=False, noblock=True)
        session = _Session(args)
        resource_meta = {"response-fields": [], "responses": []}
        data = {"message": "delete everything?", "confirmation-url": "https://x/confirm"}
        resource._processResponse(session, resource_meta, _response(200),
                                  "confirmation", "no-cache", data)
        mock_process.assert_called_once()
        self.assertEqual(mock_process.call_args[0][2], "https://x/confirm")


class _RetryStub:
    def __init__(self, attempts):
        self.attempts = attempts


class _SessionWithRetry(_Session):
    def __init__(self, args, attempts):
        super(_SessionWithRetry, self).__init__(args)
        self._retry = _RetryStub(attempts)


class TestFailureAttempts(unittest.TestCase):
    def setUp(self):
        util.enableExitCodes(True)
        util.setErrorFormat("json")

    def tearDown(self):
        util.enableExitCodes(False)
        util.setErrorFormat("text")

    def _run(self, status):
        args = _Args(automation=False, assume_yes=False, noblock=False)
        session = _SessionWithRetry(args, attempts=3)
        resource_meta = {"response-fields": [], "responses": []}
        data = {"title": "boom", "description": "it broke", "diagnostics": ""}

        err = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = err
        try:
            with self.assertRaises(SystemExit):
                resource._processResponse(session, resource_meta, _response(status),
                                          "object", "no-cache", data)
        finally:
            sys.stderr = old_stderr

        return json.loads(err.getvalue())["error"]

    def test_failure_reports_real_attempts_in_json_envelope(self):
        self.assertEqual(self._run(503)["attempts"], 3)

    def test_transient_status_marked_retriable(self):
        # A transient HTTP status (503) must report retriable=true, regardless
        # of method -- the caller decides whether a retry is safe for its op.
        for status in (429, 502, 503, 504):
            self.assertTrue(self._run(status)["retriable"],
                            "status {} should be retriable".format(status))

    def test_permanent_status_not_retriable(self):
        for status in (400, 401, 404, 500):
            self.assertFalse(self._run(status)["retriable"],
                             "status {} should not be retriable".format(status))


if __name__ == "__main__":
    unittest.main()
