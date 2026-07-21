# Copyright (c) 2026, Corelight. All rights reserved.
#
# See COPYING for license information.

import unittest

from client import argparser


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


if __name__ == "__main__":
    unittest.main()
