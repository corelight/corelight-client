"""Tests for _SSLAdapter.cert_verify SSL flag behavior with urllib3 2.x."""
import ssl
import types
import unittest

import urllib3.connectionpool

# Import the adapter under test
from client.session import _SSLAdapter


def _make_args(**kwargs):
    """Build a minimal args namespace for _SSLAdapter."""
    defaults = dict(
        ssl_ca_cert=None,
        ssl_no_verify_hostname=False,
        ssl_no_verify_certificate=False,
    )
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _make_pool():
    """Return a real HTTPSConnectionPool to pass to cert_verify."""
    return urllib3.connectionpool.HTTPSConnectionPool("example.com", 443)


class TestSSLAdapterNoVerifyCertificate(unittest.TestCase):
    def test_ssl_context_has_cert_none_when_no_verify_certificate(self):
        """--ssl-no-verify-certificate must produce CERT_NONE ssl context."""
        adapter = _SSLAdapter(_make_args(ssl_no_verify_certificate=True))
        pool = _make_pool()
        adapter.cert_verify(pool, "https://example.com", verify=True, cert=None)
        self.assertIsNotNone(pool.ssl_context)
        self.assertEqual(pool.ssl_context.verify_mode, ssl.CERT_NONE)

    def test_ssl_context_has_check_hostname_false_when_no_verify_certificate(self):
        """--ssl-no-verify-certificate must disable check_hostname."""
        adapter = _SSLAdapter(_make_args(ssl_no_verify_certificate=True))
        pool = _make_pool()
        adapter.cert_verify(pool, "https://example.com", verify=True, cert=None)
        self.assertFalse(pool.ssl_context.check_hostname)

    def test_assert_hostname_false_when_no_verify_certificate(self):
        """--ssl-no-verify-certificate must also disable hostname assertion."""
        adapter = _SSLAdapter(_make_args(ssl_no_verify_certificate=True))
        pool = _make_pool()
        adapter.cert_verify(pool, "https://example.com", verify=True, cert=None)
        self.assertFalse(pool.assert_hostname)


class TestSSLAdapterNoVerifyHostname(unittest.TestCase):
    def test_assert_hostname_false_when_no_verify_hostname(self):
        """--ssl-no-verify-hostname must set assert_hostname=False."""
        adapter = _SSLAdapter(_make_args(ssl_no_verify_hostname=True, ssl_ca_cert="system"))
        pool = _make_pool()
        adapter.cert_verify(pool, "https://example.com", verify=True, cert=None)
        self.assertFalse(pool.assert_hostname)

    def test_cert_required_still_set_when_only_no_verify_hostname(self):
        """--ssl-no-verify-hostname alone must not disable cert verification."""
        adapter = _SSLAdapter(_make_args(ssl_no_verify_hostname=True, ssl_ca_cert="system"))
        pool = _make_pool()
        adapter.cert_verify(pool, "https://example.com", verify=True, cert=None)
        # ssl_context should not be set to CERT_NONE
        ctx = getattr(pool, "ssl_context", None)
        if ctx is not None:
            self.assertNotEqual(ctx.verify_mode, ssl.CERT_NONE)


class TestSSLAdapterNoVerifyCertificateHostname(unittest.TestCase):
    def test_assert_hostname_false_even_with_explicit_ca_when_no_verify_cert(self):
        """--ssl-no-verify-certificate must disable hostname checking too.

        Old code set assert_hostname=u.hostname even with ssl_no_verify_certificate=True,
        which caused spurious hostname failures when cert verification was disabled.
        """
        adapter = _SSLAdapter(_make_args(ssl_no_verify_certificate=True, ssl_ca_cert="/some/ca.pem"))
        pool = _make_pool()
        adapter.cert_verify(pool, "https://mydevice.example.com", verify=True, cert=None)
        self.assertFalse(pool.assert_hostname)


class TestSSLAdapterVerifyHostname(unittest.TestCase):
    def test_assert_hostname_set_to_url_host_when_verify_enabled(self):
        """When hostname verification is on, assert_hostname must equal the URL host."""
        adapter = _SSLAdapter(_make_args(ssl_ca_cert="system"))
        pool = _make_pool()
        adapter.cert_verify(pool, "https://mydevice.example.com", verify=True, cert=None)
        self.assertEqual(pool.assert_hostname, "mydevice.example.com")


class TestSSLAdapterDefaultCorelightCA(unittest.TestCase):
    def test_default_uses_corelight_ca_with_hostname_disabled(self):
        """Default (no flags) uses Corelight root CA with assert_hostname=False."""
        adapter = _SSLAdapter(_make_args())
        pool = _make_pool()
        adapter.cert_verify(pool, "https://example.com", verify=True, cert=None)
        self.assertFalse(pool.assert_hostname)
        # Should point to the Corelight CA bundle, not None
        self.assertIsNotNone(pool.ca_certs)


if __name__ == "__main__":
    unittest.main()
