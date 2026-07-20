# Copyright (c) 2026, Corelight. All rights reserved.
#
# See COPYING for license information.

import io
import json
import sys
import unittest

from client import exitcodes
from client import util


class TestUtilState(unittest.TestCase):
    def setUp(self):
        util.enableExitCodes(False)
        util.setErrorFormat("text")

    def tearDown(self):
        util.enableExitCodes(False)
        util.setErrorFormat("text")

    def test_parse_timeout_pair(self):
        self.assertEqual(util.parseTimeout("10,300"), (10.0, 300.0))

    def test_parse_timeout_single(self):
        self.assertEqual(util.parseTimeout("30"), (30.0, 30.0))

    def test_parse_timeout_bad(self):
        with self.assertRaises(ValueError):
            util.parseTimeout("abc")

    def test_fail_legacy_collapses_to_1(self):
        err = io.StringIO()
        old = sys.stderr
        sys.stderr = err
        try:
            with self.assertRaises(SystemExit) as cm:
                util.fail(exitcodes.AUTH, title="nope",
                          legacy_lines=["Error: nope."])
        finally:
            sys.stderr = old
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(err.getvalue(), "Error: nope.\n")

    def test_fail_taxonomy_uses_code(self):
        util.enableExitCodes(True)
        err = io.StringIO()
        old = sys.stderr
        sys.stderr = err
        try:
            with self.assertRaises(SystemExit) as cm:
                util.fail(exitcodes.AUTH, title="nope",
                          legacy_lines=["Error: nope."])
        finally:
            sys.stderr = old
        self.assertEqual(cm.exception.code, exitcodes.AUTH)

    def test_fail_json_envelope(self):
        util.enableExitCodes(True)
        util.setErrorFormat("json")
        err = io.StringIO()
        old = sys.stderr
        sys.stderr = err
        try:
            with self.assertRaises(SystemExit):
                util.fail(exitcodes.SERVER, title="boom",
                          description="it broke", http_status=503,
                          retriable=True, attempts=3,
                          legacy_lines=["Error: boom."])
        finally:
            sys.stderr = old
        payload = json.loads(err.getvalue())
        self.assertEqual(payload["error"]["code"], exitcodes.SERVER)
        self.assertEqual(payload["error"]["http_status"], 503)
        self.assertEqual(payload["error"]["attempts"], 3)
        self.assertTrue(payload["error"]["retriable"])


if __name__ == "__main__":
    unittest.main()
