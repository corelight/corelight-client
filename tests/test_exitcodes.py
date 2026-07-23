# Copyright (c) 2026, Corelight. All rights reserved.
#
# See COPYING for license information.

import unittest

from client import exitcodes


class TestClassifyStatus(unittest.TestCase):
    def test_auth_statuses(self):
        self.assertEqual(exitcodes.classify_status(401), exitcodes.AUTH)
        self.assertEqual(exitcodes.classify_status(403), exitcodes.AUTH)

    def test_not_found(self):
        self.assertEqual(exitcodes.classify_status(404), exitcodes.NOT_FOUND)

    def test_server_errors(self):
        self.assertEqual(exitcodes.classify_status(500), exitcodes.SERVER)
        self.assertEqual(exitcodes.classify_status(503), exitcodes.SERVER)

    def test_other_client_error_is_generic(self):
        self.assertEqual(exitcodes.classify_status(400), exitcodes.GENERIC)

    def test_none_is_generic(self):
        self.assertEqual(exitcodes.classify_status(None), exitcodes.GENERIC)


if __name__ == "__main__":
    unittest.main()
