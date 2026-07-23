# Copyright (c) 2026, Corelight. All rights reserved.
#
# See COPYING for license information.

import unittest
from unittest import mock

import requests.exceptions

import client.exitcodes
from client.session import RetryPolicy, Session, SessionError, statusIsRetriable


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
    def test_post_does_not_retry_connection_error(self, _sleep):
        # A bare ConnectionError is ambiguous (could be a reset after the body
        # was sent), so a mutation must not be replayed. Regression pin.
        p = RetryPolicy(retries=3)
        calls = {"n": 0}

        def attempt():
            calls["n"] += 1
            raise requests.exceptions.ConnectionError()

        with self.assertRaises(requests.exceptions.ConnectionError):
            p.execute("POST", attempt)
        self.assertEqual(calls["n"], 1)  # no retry on ConnectionError for POST

    @mock.patch("client.session.time.sleep", return_value=None)
    def test_get_retries_connection_error_then_succeeds(self, _sleep):
        # Idempotent methods still retry a ConnectionError; confirms we did not
        # over-correct the mutation fix.
        p = RetryPolicy(retries=2)
        seq = [requests.exceptions.ConnectionError(), _resp(200)]
        calls = {"n": 0}

        def attempt():
            item = seq[calls["n"]]
            calls["n"] += 1
            if isinstance(item, Exception):
                raise item
            return item

        out = p.execute("GET", attempt)
        self.assertEqual(out.status_code, 200)
        self.assertEqual(calls["n"], 2)

    @mock.patch("client.session.time.sleep", return_value=None)
    def test_ssl_error_not_retried_even_for_get(self, _sleep):
        # SSLError subclasses ConnectionError but is a config error, not
        # transient -- it must not be retried even for an idempotent method.
        p = RetryPolicy(retries=3)
        calls = {"n": 0}

        def attempt():
            calls["n"] += 1
            raise requests.exceptions.SSLError("bad cert")

        with self.assertRaises(requests.exceptions.SSLError):
            p.execute("GET", attempt)
        self.assertEqual(calls["n"], 1)

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


class TestSendGoesThroughRetry(unittest.TestCase):
    """
    Every send -- including the sensor-side 2FA re-auth -- must go through the
    timeout/retry path, so no request can hang unbounded under --automation.
    """

    def _session(self, timeout, retries, send):
        s = Session.__new__(Session)
        s._timeout = timeout
        s._retry = RetryPolicy(retries=retries)
        # _send calls Session._RequestsSession.send; stub the shared session.
        self._saved = Session._RequestsSession
        Session._RequestsSession = mock.Mock()
        Session._RequestsSession.send.side_effect = send
        return s

    def tearDown(self):
        Session._RequestsSession = getattr(self, "_saved", None)

    @mock.patch("client.session.time.sleep", return_value=None)
    def test_send_applies_timeout(self, _sleep):
        s = self._session(timeout=(5, 9), retries=0,
                          send=lambda *a, **k: _resp(200))
        prepared = mock.Mock()
        prepared.method = "GET"
        s._send(prepared)
        Session._RequestsSession.send.assert_called_once_with(prepared, timeout=(5, 9))

    @mock.patch("client.session.time.sleep", return_value=None)
    def test_send_retries_transient_status(self, _sleep):
        seq = [_resp(503), _resp(200)]
        calls = {"n": 0}

        def send(*a, **k):
            r = seq[calls["n"]]
            calls["n"] += 1
            return r

        s = self._session(timeout=None, retries=2, send=send)
        prepared = mock.Mock()
        prepared.method = "GET"
        out = s._send(prepared)
        self.assertEqual(out.status_code, 200)
        self.assertEqual(calls["n"], 2)


class TestRetriableClassification(unittest.TestCase):
    def test_status_is_retriable(self):
        for status in (429, 502, 503, 504):
            self.assertTrue(statusIsRetriable(status))
        for status in (200, 400, 401, 403, 404, 500, 501):
            self.assertFalse(statusIsRetriable(status))

    def test_session_error_derives_from_status(self):
        # A 503 carried by a SessionError is transient regardless of category.
        e = SessionError("x", status_code=503)
        self.assertTrue(e.isRetriable())
        e = SessionError("x", status_code=404)
        self.assertFalse(e.isRetriable())

    def test_session_error_connect_is_retriable(self):
        # A connect-level failure with no status derives retriable from category.
        e = SessionError("x", category=client.exitcodes.CONNECT)
        self.assertTrue(e.isRetriable())

    def test_session_error_explicit_override_wins(self):
        # SSL errors share the connect category but are not transient.
        e = SessionError("x", category=client.exitcodes.CONNECT, retriable=False)
        self.assertFalse(e.isRetriable())


if __name__ == "__main__":
    unittest.main()
