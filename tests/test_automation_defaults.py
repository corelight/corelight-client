# Copyright (c) 2026, Corelight. All rights reserved.
#
# See COPYING for license information.

import io
import sys
import unittest

import client
from client import argparser
from client import exitcodes
from client import util


class _NS:
    def __init__(self, **kw):
        self.automation = kw.get("automation", False)
        self.timeout = kw.get("timeout", None)
        self.retries = kw.get("retries", None)
        self.retry_max_time = kw.get("retry_max_time", None)
        self.error_format = kw.get("error_format", None)
        self.noblock = kw.get("noblock", False)


class TestApplyAutomationDefaults(unittest.TestCase):
    def test_automation_fills_defaults(self):
        ns = _NS(automation=True)
        argparser.applyAutomationDefaults(ns)
        self.assertEqual(ns.timeout, "10,300")
        self.assertEqual(ns.retries, 3)
        self.assertEqual(ns.retry_max_time, 120.0)
        self.assertEqual(ns.error_format, "json")
        self.assertTrue(ns.noblock)

    def test_automation_respects_overrides(self):
        ns = _NS(automation=True, retries=0, error_format="text")
        argparser.applyAutomationDefaults(ns)
        self.assertEqual(ns.retries, 0)
        self.assertEqual(ns.error_format, "text")

    def test_legacy_leaves_everything_off(self):
        ns = _NS(automation=False)
        argparser.applyAutomationDefaults(ns)
        self.assertIsNone(ns.timeout)
        self.assertEqual(ns.retries, 0)
        self.assertEqual(ns.error_format, "text")
        self.assertFalse(ns.noblock)


class TestParserErrorRoutesThroughFail(unittest.TestCase):
    """
    Regression coverage for ComponentArgumentParser.error() and
    CommandArgumentParser.error(): both now funnel through
    client.util.fail(exitcodes.USAGE, ...) instead of calling self.exit()
    directly, so fail() is solely responsible for terminating the process.
    """

    def setUp(self):
        util.enableExitCodes(False)
        util.setErrorFormat("text")

    def tearDown(self):
        util.enableExitCodes(False)
        util.setErrorFormat("text")

    def _assertLegacyError(self, parser):
        err = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = err
        try:
            with self.assertRaises(SystemExit) as cm:
                parser.error("boom")
        finally:
            sys.stderr = old_stderr

        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(err.getvalue(), "{} error: boom\n".format(client.NAME))

    def test_component_parser_error_legacy_mode(self):
        self._assertLegacyError(argparser.ComponentArgumentParser())

    def test_command_parser_error_legacy_mode(self):
        self._assertLegacyError(argparser.CommandArgumentParser())

    def _assertTaxonomyError(self, parser):
        util.enableExitCodes(True)
        err = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = err
        try:
            with self.assertRaises(SystemExit) as cm:
                parser.error("boom")
        finally:
            sys.stderr = old_stderr

        self.assertEqual(cm.exception.code, exitcodes.USAGE)

    def test_component_parser_error_taxonomy_mode(self):
        self._assertTaxonomyError(argparser.ComponentArgumentParser())

    def test_command_parser_error_taxonomy_mode(self):
        self._assertTaxonomyError(argparser.CommandArgumentParser())


if __name__ == "__main__":
    unittest.main()
