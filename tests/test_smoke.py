# Copyright (c) 2026, Corelight. All rights reserved.
#
# See COPYING for license information.

import unittest

import client


class TestSmoke(unittest.TestCase):
    def test_package_has_version(self):
        self.assertTrue(client.VERSION)
        self.assertEqual(client.NAME, "corelight-client")


if __name__ == "__main__":
    unittest.main()
