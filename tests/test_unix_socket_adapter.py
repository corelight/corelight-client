# Copyright (c) 2026, Corelight. All rights reserved.
#
# See COPYING for license information.

"""
Regression tests for the unix-socket transport (--socket).

requests 2.32 reworked HTTPAdapter connection handling: it stopped calling
HTTPAdapter.get_connection() from send() and now calls
get_connection_with_tls_context() instead. The client's _UnixSocketAdapter
overrode only the old hook, so under requests >= 2.32 the override was silently
bypassed and requests tried to open a normal TCP connection to the (bogus) host
instead of routing through the unix socket. These tests pin that the adapter
routes a real request through the AF_UNIX socket regardless of the installed
requests version.
"""

import os
import tempfile
import threading
import http.server
import socketserver
import unittest

import requests

from client.session import _UnixSocketAdapter


class _Args(object):
    """Minimal stand-in for the parsed argument namespace the adapter reads."""

    def __init__(self, sock_path):
        self.socket = sock_path
        self.timeout_read = 5


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class _UnixHTTPServer(socketserver.UnixStreamServer):
    allow_reuse_address = True


class TestUnixSocketAdapter(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._sock_path = os.path.join(self._tmpdir, "api.sock")
        self._server = _UnixHTTPServer(self._sock_path, _Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def tearDown(self):
        self._server.shutdown()
        self._server.server_close()
        if os.path.exists(self._sock_path):
            os.remove(self._sock_path)
        os.rmdir(self._tmpdir)

    def test_request_routes_through_unix_socket(self):
        # A deliberately unresolvable host: if the adapter is bypassed, requests
        # would try to DNS-resolve it and fail, so a success proves the socket
        # pool was actually used.
        session = requests.Session()
        adapter = _UnixSocketAdapter(_Args(self._sock_path), "unix.invalid")
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        resp = session.get("http://unix.invalid/api/", timeout=5)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True})

    def test_both_connection_hooks_return_socket_pool(self):
        # Guards both the pre-2.32 hook (get_connection) and the 2.32+ hook
        # (get_connection_with_tls_context) so neither regresses independently.
        adapter = _UnixSocketAdapter(_Args(self._sock_path), "unix.invalid")
        pool = adapter._unix_connection_pool
        self.assertIs(adapter.get_connection("http://unix.invalid/"), pool)
        self.assertIs(
            adapter.get_connection_with_tls_context(
                requests.Request("GET", "http://unix.invalid/").prepare(),
                verify=True),
            pool)


if __name__ == "__main__":
    unittest.main()
