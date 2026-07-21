# Copyright (c) 2026, Corelight. All rights reserved.
#
# See COPYING for license information.

import unittest
from unittest import mock

import requests.exceptions

import client.exitcodes
from client.session import RetryPolicy, SessionError


def _resp(status):
    r = mock.Mock()
    r.status_code = status
    r.headers = {}
    return r


class TestRetryPolicy(unittest.TestCase):
    @mock.patch("client.session.time.sleep", return_value=None)
    def test_get_retries_503_then_succeeds(self, _sleep):
        p = RetryPolicy(retries=3)
        seq = [_resp(503), _resp(503), _resp(200)]
        calls = {"n": 0}

        def attempt():
            r = seq[calls["n"]]
            calls["n"] += 1
            return r

        out = p.execute("GET", attempt)
        self.assertEqual(out.status_code, 200)
        self.assertEqual(calls["n"], 3)

    @mock.patch("client.session.time.sleep", return_value=None)
    def test_get_exhausts_returns_last_response(self, _sleep):
        p = RetryPolicy(retries=1)
        calls = {"n": 0}

        def attempt():
            calls["n"] += 1
            return _resp(503)

        out = p.execute("GET", attempt)
        self.assertEqual(out.status_code, 503)
        self.assertEqual(calls["n"], 2)  # 1 initial + 1 retry

    @mock.patch("client.session.time.sleep", return_value=None)
    def test_post_does_not_retry_on_status(self, _sleep):
        p = RetryPolicy(retries=3)
        calls = {"n": 0}

        def attempt():
            calls["n"] += 1
            return _resp(503)

        out = p.execute("POST", attempt)
        self.assertEqual(out.status_code, 503)
        self.assertEqual(calls["n"], 1)  # no retry on status for POST

    @mock.patch("client.session.time.sleep", return_value=None)
    def test_post_retries_connect_timeout(self, _sleep):
        p = RetryPolicy(retries=2)
        seq = [requests.exceptions.ConnectTimeout(), _resp(200)]
        calls = {"n": 0}

        def attempt():
            item = seq[calls["n"]]
            calls["n"] += 1
            if isinstance(item, Exception):
                raise item
            return item

        out = p.execute("POST", attempt)
        self.assertEqual(out.status_code, 200)

    @mock.patch("client.session.time.sleep", return_value=None)
    def test_post_does_not_retry_read_timeout(self, _sleep):
        p = RetryPolicy(retries=3)
        calls = {"n": 0}

        def attempt():
            calls["n"] += 1
            raise requests.exceptions.ReadTimeout()

        with self.assertRaises(requests.exceptions.ReadTimeout):
            p.execute("POST", attempt)
        self.assertEqual(calls["n"], 1)  # no retry on ReadTimeout for POST

    @mock.patch("client.session.time.sleep", return_value=None)
    def test_retry_after_header_used(self, _sleep):
        p = RetryPolicy(retries=1)
        r503 = _resp(503)
        r503.headers = {"Retry-After": "2"}
        seq = [r503, _resp(200)]
        calls = {"n": 0}

        def attempt():
            r = seq[calls["n"]]
            calls["n"] += 1
            return r

        out = p.execute("GET", attempt)
        self.assertEqual(out.status_code, 200)
        _sleep.assert_called_once_with(2.0)

    @mock.patch("client.session.time.sleep", return_value=None)
    def test_negative_retries_behaves_like_zero(self, _sleep):
        p = RetryPolicy(retries=-1)
        calls = {"n": 0}

        def attempt():
            calls["n"] += 1
            return _resp(200)

        out = p.execute("GET", attempt)
        self.assertEqual(out.status_code, 200)
        self.assertEqual(calls["n"], 1)


class TestSessionErrorAttempts(unittest.TestCase):
    def test_attempts_threads_through(self):
        e = SessionError("x", category=client.exitcodes.CONNECT, attempts=3)
        self.assertEqual(e.attempts, 3)


if __name__ == "__main__":
    unittest.main()
