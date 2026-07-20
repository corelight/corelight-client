# Copyright (c) 2017, Corelight. All rights reserved.
#
# See COPYING for license information.

import os
import ssl
import sys
import time
import random
import email.utils
import urllib.parse
import socket
import requests
import requests.exceptions
import requests.utils
import requests.adapters
import requests.packages.urllib3
import requests.packages.urllib3.poolmanager
import requests.packages.urllib3.connection
import requests.packages.urllib3.connectionpool
from client.multipart import MultipartEncoder
import client.util
import client.exitcodes

# The CA to validate default Corelight certificates with.
_CorelightRoot = os.path.join(os.path.dirname(__file__), "certs/corelight.pem")

# Maximum API  version we support. If server sends a more recent one, this
# client needs to be updated.
_Version = 1

requests.packages.urllib3.disable_warnings()

class SessionError(Exception):
    def __init__(self, msg, arg=None, status_code=None, category=None):
        super(SessionError, self).__init__(msg + (" ({})".format(arg) if arg else ""))
        self._msg = msg
        self._arg = arg
        self.status_code = status_code
        self.category = category if category is not None else client.exitcodes.GENERIC

    def fatalError(self):
        """Triggers a fatal error reporting the exception's information."""
        if self._arg:
            line = "Fatal error: {} ({})".format(self._msg, self._arg)
        else:
            line = "Fatal error: {}".format(self._msg)

        retriable = self.category in (client.exitcodes.CONNECT, client.exitcodes.SERVER)
        client.util.fail(self.category, title=self._msg,
                         description=(str(self._arg) if self._arg else None),
                         http_status=self.status_code, retriable=retriable,
                         legacy_lines=[line])

class RetryPolicy:
    """Retries transient request failures with idempotency-aware safety."""

    RETRIABLE_STATUSES = frozenset([429, 502, 503, 504])
    IDEMPOTENT_METHODS = frozenset(["GET", "HEAD", "OPTIONS"])

    # Base backoff seconds and absolute per-wait ceiling.
    _BASE_BACKOFF = 0.5
    _MAX_BACKOFF = 30.0

    def __init__(self, retries=0, timeout=None, max_time=None):
        self.retries = retries or 0
        self.timeout = timeout
        self.max_time = max_time
        self.attempts = 0

    def _is_idempotent(self, method):
        return method.upper() in RetryPolicy.IDEMPOTENT_METHODS

    def _should_retry_exception(self, method, exc):
        # Connection never established -> safe to retry for any method.
        if isinstance(exc, requests.exceptions.ConnectTimeout):
            return True
        if isinstance(exc, requests.exceptions.ConnectionError):
            return True
        # Response phase may have reached the server -> idempotent only.
        if isinstance(exc, requests.exceptions.Timeout):
            return self._is_idempotent(method)
        return False

    def _should_retry_status(self, method, status):
        return self._is_idempotent(method) and status in RetryPolicy.RETRIABLE_STATUSES

    def _retry_after(self, response):
        if response is None:
            return None
        value = response.headers.get("Retry-After", None)
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            parsed = email.utils.parsedate_tz(value)
            if not parsed:
                return None
            when = email.utils.mktime_tz(parsed)
            delta = when - time.time()
            return delta if delta > 0 else 0.0

    def _backoff(self, attempt, response):
        after = self._retry_after(response)
        if after is not None:
            return after
        window = min(RetryPolicy._BASE_BACKOFF * (2 ** (attempt - 1)),
                     RetryPolicy._MAX_BACKOFF)
        return random.uniform(0, window)

    def execute(self, method, attempt_fn):
        """
        Runs *attempt_fn* (a zero-arg callable returning a requests.Response or
        raising a requests exception), retrying transient failures per policy.

        Returns the final Response (success, non-retriable, or exhausted). Re-
        raises the last transient exception if all attempts fail on exceptions.
        """
        start = time.monotonic()
        last_exc = None
        total_tries = self.retries + 1

        for attempt in range(1, total_tries + 1):
            self.attempts = attempt
            response = None
            try:
                response = attempt_fn()
            except Exception as e:  # noqa: F841 (requests exceptions)
                if not self._should_retry_exception(method, e):
                    raise
                last_exc = e
            else:
                if not self._should_retry_status(method, response.status_code):
                    return response

            if attempt >= total_tries:
                break

            wait = self._backoff(attempt, response)
            if self.max_time is not None and (time.monotonic() - start) + wait > self.max_time:
                break

            # Retries are a transport event; route through the debug channel
            # (like the rest of the HTTP wire logging) so we add no new default
            # stderr output in any mode. Machine consumers read the retry count
            # from the error envelope's "attempts" field instead.
            client.util.debug(
                "retrying (attempt {}/{}) after {}, waiting {:.1f}s".format(
                    attempt + 1, total_tries,
                    ("HTTP {}".format(response.status_code) if response is not None
                     else type(last_exc).__name__),
                    wait))
            time.sleep(wait)

        if response is not None:
            return response  # exhausted on retriable status; let caller handle it
        raise last_exc

# requests adaptor giving more control over certificate validation.
# Adapted from http://docs.python-requests.org/en/master/user/advanced/#transport-adapters
class _SSLAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, args, *adapter_args, **adapter_kwargs):
        requests.adapters.HTTPAdapter.__init__(self, *adapter_args, **adapter_kwargs)
        self._args = args

    def cert_verify(self, conn, url, verify, cert):
        """Overridden from base class to control certificate validation."""
        ssl_ca_cert = self._args.ssl_ca_cert
        ssl_no_verify_hostname = self._args.ssl_no_verify_hostname
        ssl_no_verify_certificate = self._args.ssl_no_verify_certificate

        if not ssl_ca_cert:
            # Use Corelight root CA and disable hostname verification.
            ssl_ca_cert = _CorelightRoot
            ssl_no_verify_hostname = True

        if ssl_no_verify_certificate:
            # Must disable check_hostname before setting CERT_NONE; Python ssl
            # raises an error if you try to set CERT_NONE while check_hostname=True.
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            conn.ssl_context = ctx
            # urllib3 2.x overwrites context.verify_mode with resolve_cert_reqs(conn.cert_reqs)
            # at handshake time, so we must reset cert_reqs too or our CERT_NONE is clobbered.
            conn.cert_reqs = ssl.CERT_NONE
            conn.assert_hostname = False
        else:
            verify_arg = ssl_ca_cert if ssl_ca_cert != "system" else True
            super().cert_verify(conn, url, verify_arg, cert)
            if ssl_no_verify_hostname:
                conn.assert_hostname = False
            else:
                conn.assert_hostname = urllib.parse.urlparse(url).hostname

        if cert:
            if not isinstance(cert, str):
                conn.cert_file = cert[0]
                conn.key_file = cert[1]
            else:
                conn.cert_file = cert

    def build_response(self, req, resp):
        """Overridden from base class to get access to the server-side certificate."""
        response = super(_SSLAdapter, self).build_response(req, resp)
        response.peer_certificate = resp._connection.peer_certificate
        return response

class _UnixSocketConnection(requests.packages.urllib3.connection.HTTPConnection):
    def __init__(self, args, host_address):
        super(_UnixSocketConnection, self).__init__(
            host_address,
            timeout=(args.timeout_read if getattr(args, "timeout_read", None) else None))
        self.sock = None
        self._args = args
    
    def __del__(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def connect(self):
        client.util.debug("sock = sock.socket(AF_UNIX, SOCK_STREAM)")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.util.debug("sock.connect('{}')".format(self._args.socket))
        sock.connect(self._args.socket)
        self.sock = sock

class _HTTPSConnectionPool(requests.packages.urllib3.connectionpool.HTTPSConnectionPool):
    def _validate_conn(self, conn):
        """Overridden from base class to get access to the server-side certificate."""
        super(_HTTPSConnectionPool, self)._validate_conn(conn)

        try:
            conn.peer_certificate = conn.sock.getpeercert()
        except:
            conn.peer_certificate = None

# Patch our custom class into the pool manager.
requests.packages.urllib3.poolmanager.pool_classes_by_scheme["https"] = _HTTPSConnectionPool

class _UnixSocketConnectionPool(requests.packages.urllib3.connectionpool.HTTPConnectionPool):
    def __init__(self, args, host_address):
        self._host_address = host_address
        super(_UnixSocketConnectionPool, self).__init__(
            self._host_address,
            timeout=(args.timeout_read if getattr(args, "timeout_read", None) else None))
        self._args = args

    def _new_conn(self):
        return _UnixSocketConnection(self._args, self._host_address)


class _UnixSocketAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, args, host_address):
        super(_UnixSocketAdapter, self).__init__()
        self._unix_connection_pool = _UnixSocketConnectionPool(args, host_address)

    def get_connection(self, url, proxies=None):
        return self._unix_connection_pool

class Session:
    """Class issueing HTTP requests to the Corelight Sensor device."""
    # The joint requests.Session object used for all requests. Created on first use.
    _RequestsSession = None

    def __init__(self, args):
        """
        Constructor.

        args (ComponentArgumentParser): The top-level argument parse with
        command line options.
        """
        self._args = args

        timeout = None
        retries = 0
        max_time = None
        try:
            if getattr(args, "timeout", None):
                timeout = client.util.parseTimeout(args.timeout)
            retries = getattr(args, "retries", 0) or 0
            max_time = getattr(args, "retry_max_time", None)
        except ValueError as e:
            client.util.fatalError("invalid --timeout value", e)

        self._timeout = timeout
        self._retry = RetryPolicy(retries=retries, timeout=timeout, max_time=max_time)
        self._args.timeout_read = timeout[1] if timeout else None

        self.socket_pool = None

        if not Session._RequestsSession:
            Session._RequestsSession = requests.Session()
            if self._args.socket:
                socket_adapter = _UnixSocketAdapter(self._args, "localhost")
                Session._RequestsSession.mount('http://', socket_adapter)
                Session._RequestsSession.mount('https://', socket_adapter)
            else:
                Session._RequestsSession.mount('https://', _SSLAdapter(self._args))

    def arguments(self):
        """Returns the *ComponentArgumentParser* associated with the session."""
        return self._args

    def setArguments(self, args):
        """
        Associates a different argument parser with the session.

        args (ComponentArgumentParser): The argument parser to now associate
        with the session.
        """
        self._args = args

    def _performFleetLogin(self, **kwargs):
        """
        Performs fleet authentication
        """
        if self._args.auth_base_url:
            fullUrl = client.util.appendUrl(self._args.auth_base_url, "/login")
        else:
            return

        try:
            mfaToken = self._args.mfa
        except:
            mfaToken = None

        if self._args.user and self._args.password and not self._args.bearer_token:
            res = self._retrieveURL(fullUrl, json={"username": self._args.user, "password": self._args.password}, method="POST")
            res.raise_for_status()
            vals = res.json()
            if not vals or not "token" in vals or not vals["token"]:
                raise SessionError("Server did not return a valid authentication bearer token. Please check the url and try again.")

            bearer_token = vals["token"]
            
            if vals and "settings" in vals and "password.cache.disabled" in vals["settings"] and vals["settings"]["password.cache.disabled"]:
                self._args.no_password_save = True

            if vals and "2fa.required" in vals and vals["2fa.required"]:
                if "2fa.should_enroll" in vals and vals["2fa.should_enroll"]:
                    raise SessionError("The user needs to enroll an authenticator app before using corleight-client.")

                verifyUrl = client.util.appendUrl(self._args.auth_base_url, "/current/2fa/verify")

                if mfaToken and mfaToken == "-" and (not self._args.noblock):
                    mfaToken = client.util.getInput("Verification Code", password=True)

                if not mfaToken:
                    raise SessionError("No 2FA token has been provided. Please provide a proper 2FA token and try again.")

                res = self._retrieveURL(verifyUrl, json={"passcode": mfaToken}, method="POST")
                try:
                   res.raise_for_status()
                except requests.exceptions.HTTPError as e: 
                    data = res.json()

                    # 2fa/verify endpoint return json with error message
                    if "error" in data and "message" in data['error']:
                        raise SessionError(str(data['error']['message']))
                    else:
                        raise SessionError("Cannot get 2fa session from device")

                vals = res.json()

                if not vals or not "token" in vals or not vals["token"]:
                    raise SessionError("Server did not return a valid authentication bearer token. Please check the url and try again.")
                
                bearer_token = vals["token"]

            self._args.bearer_token = bearer_token

    def retrieveResource(self, url, **kwargs):
        """
        Retrieves a given URL through a ``GET`` request from a Corelight Sensor. The
        response' body is expected to be in JSON format and decoded. The
        response is also expected to come with ``schema``, ``version``,
        and ``cache`` parameters in the ``Content-Type``, per Corelight Sensor
        API specification.

        If the body is not JSON, or cannot be decoded as such, the
        function raises an ``SessionError``; same if no ``schema`` is
        found. The exception is when the response represents an error
        itself: in that case these issues are non-fatal and empty
        objects are returned for the element that couldn't be
        retrieved.

        This also verifies that the response's format, and version value,
        conforms to the Corelight API specification as we would expect. The
        function aborts otherwise.

        url (str): The full URL to retrieve.

        All other keyword arguments are passed through to the
        corresponding ``requests`` methods.

        Returns: A 4-tuple ``(requests.Response, string, string,
        any)``. The 1st element is the complete response object; the
        2nd is the ``schema`` parameter from response's
        ``Content-Type`` header; the 3rd is the ``version`` parameter;
        and the 4th element is a Python object representing the
        decoded JSON body. When the method encounters an error, it
        raises a ``SessionError`` exception. Usually this should be
        considered a fatal error and execution be aborted.
        """

        if self._args.fleet and not self._args.bearer_token:
            self._performFleetLogin(**kwargs)

        response = self._retrieveURL(url, **kwargs)
        success = (response.status_code >= 200 and response.status_code < 300)

        (ty, st, params) = self._parseContentType(response, ignore_errors=True)

        schema = None
        version = None
        data = None

        if ty == "application" and st == "json":
            try:
                data = response.json()
            except:
                if success:
                    raise SessionError("Cannot decode JSON body of response", url, response.status_code)
                else:
                    return (response, "", "", {})

        elif response.status_code == 202: # 202 Accepted.
            return (response, "", "", {})

        else:
            if success:
                raise SessionError("Received non-JSON response from Corelight Sensor", url, response.status_code)
            else:
                return (response, "", "", {})

        try:
            schema = params["schema"]
            version = params["version"]
            cache = params["cache"]
        except KeyError:
            if success:
                raise SessionError("Corelight Sensor response did not include all required API parameters", url, response.status_code)
            else:
                return (response, "", "", data)

        try:
            if int(version) > _Version:
                raise SessionError("Your current {} client does not support the device's version, please update the client.".format(client.NAME),
                                   status_code=response.status_code,
                                   category=client.exitcodes.VERSION_UNSUPPORTED)
        except ValueError:
            # This remains a fatal error even if request failed.
            raise SessionError("Cannot parse version in response.", url, response.status_code)

        return (response, schema, cache, data)

    def _retrieveURL(self, url, **kwargs):
        """
        Retrieves a given URL through a ``GET`` or ``HEAD`` request.

        When the method encounters an error retrieving the URL, it raises a
        `SessionError` exception.

        url (str): The full URL to retrieve.

        All other keyword arguments are passed through to the
        corresponding ``requests`` methods.
        """
        kwargs["method"] = kwargs.get("method", "GET")

        try:
            debug_level = kwargs["debug_level"]
            del kwargs["debug_level"]
        except KeyError:
            debug_level = 1

        # Basic Auth cred not required if bearer token available
        if self._args.user and self._args.password and not self._args.fleet and not self._args.bearer_token:
            auth = (self._args.user, self._args.password)
        else:
            auth = None
               
        if auth:
            req = requests.Request(url=url, headers=self._requestHeaders(), auth=auth, **kwargs)
        else:
            if "files" in kwargs :
                if len(kwargs["files"]) == 1 and "/fleet/v1/sensor-update/images" in url:
                    key = next(iter(kwargs["files"]))
                    file = kwargs["files"][key]
                    file_path = file[0]
                    f = file[1]
                    del kwargs["files"]
                    multipart_data = MultipartEncoder(
                        fields={
                            key:(file_path, f, "application/octet-stream"),
                            "filename": file_path
                        }
                    )
                    new_headers = self._requestHeaders().copy()
                    new_headers["Content-Type"]=multipart_data.content_type
                    req = requests.Request(url=url, headers=new_headers, data=multipart_data, **kwargs)
                else:
                    # convert name to base 
                    for key, file in kwargs["files"].items():
                        lst = list(kwargs["files"][key])
                        lst[0] = os.path.basename(file[0])
                        kwargs["files"][key]=tuple(lst)
                    req = requests.Request(url=url, headers=self._requestHeaders(), **kwargs)
            else:
                req = requests.Request(url=url, headers=self._requestHeaders(), **kwargs)


        prepared = Session._RequestsSession.prepare_request(req)

        if client.util.debugLevel():
            client.util.debug("== {} {}".format(prepared.method, prepared.url), level=debug_level)

            for (k, v) in prepared.headers.items():
                client.util.debug("| {}: {}".format(k, v), level=debug_level)

            client.util.debug("| ", level=debug_level)

            if prepared.body:
                for line in prepared.body.splitlines():
                    if isinstance(line, bytes):
                        line = line.decode("utf8", "ignore")

                    client.util.debug("| " + line, level=debug_level)

        try:
            def _attempt():
                if self._timeout is not None:
                    return Session._RequestsSession.send(prepared, timeout=self._timeout)
                return Session._RequestsSession.send(prepared)

            response = self._retry.execute(prepared.method, _attempt)

            info = response.headers.get("X-INFO-MESSAGE", None)
            if info:
                client.util.infoMessage(info)
                       
            info2faheader = response.headers.get("WWW-Authenticate", None)

            if info2faheader and info2faheader.startswith("BasicWith2fa"):
            
                 # 2fa is enabled on the sensor hence we will retry with 2fa code
                 # username password fields are constructed based on a agreed format 
                 # username 2fa|<authtype>|<username>
                 # password <passcode>|<password>
                 mfaToken = self._args.mfa
            
                 # prompt for a 2fa token
                 if mfaToken and mfaToken == "-" and (not self._args.noblock):
                    mfaToken = client.util.getInput("Verification Code", password=True)

                 # if no 2fa token provided  
                 if mfaToken is None:
                     raise SessionError("No 2FA token has been provided. Please provide a proper 2FA token and try again.")
             
                 # username has no authenticator type provided 
                 if self._args.user.find("|") == -1:
                    self._args.user = '2fa||' + self._args.user
                 else:
                    # username expected to be in format authenticator type|username
                    # As authenticator type can be any custom name, we cannot place a check for that 
                    self._args.user = '2fa|' + self._args.user

                 self._args.password = mfaToken + '|' + self._args.password
                 auth = (self._args.user, self._args.password)

                 if auth:
                     req = requests.Request(url=url, headers=self._requestHeaders(), auth=auth, **kwargs)
                 else:
                     req = requests.Request(url=url, headers=self._requestHeaders(), **kwargs)

                 prepared = Session._RequestsSession.prepare_request(req)
                 response = Session._RequestsSession.send(prepared)
                 # Get the bearer token which will be valid for the entire session 
                 info2faheader = response.headers.get("Authorization", None)
                 if info2faheader and info2faheader.startswith("Bearer "):
                     start = 'Bearer '
                     sessionID = (info2faheader.split(start,1))[1]
                     self._args.bearer_token = sessionID

                 elif info2faheader and info2faheader.startswith("SessionID="):
                     start = 'SessionID='
                     sessionID = (info2faheader.split(start,1))[1]
                     self._args.bearer_token = sessionID

                 else:
                     raise SessionError("cannot get 2fa session from device")
 
        except requests.exceptions.SSLError as e:
            u = urllib.parse.urlparse(url)
            raise SessionError("cannot connect to Corelight device at {}. {}".format(u.netloc, e),
                               category=client.exitcodes.CONNECT)

        except requests.exceptions.Timeout as e:
            u = urllib.parse.urlparse(url)
            raise SessionError("timed out connecting to Corelight device at {}".format(u.netloc), e,
                               category=client.exitcodes.CONNECT)

        except requests.ConnectionError as e:
            u = urllib.parse.urlparse(url)
            raise SessionError("cannot connect to Corelight device at {}".format(u.netloc), e,
                               category=client.exitcodes.CONNECT)

        except Exception as e:
            raise SessionError("cannot retrieve URL from Corelight device", e)

        # Available only for SSL connections.
        try:
            cert = response.peer_certificate

            if client.util.debugLevel():
                ppcert = ", ".join(["{}: {}".format(k, v) for sub in cert.get("subject", ()) for (k, v) in sub])
                client.util.debug("+ " + ppcert, level=debug_level)

        except AttributeError:
            assert urllib.parse.urlparse(url).scheme.lower() != "https"
            cert = None

        if client.util.debugLevel():
            client.util.debug("== {} {}".format(response.status_code, response.reason), level=debug_level)

            for (k, v) in response.headers.items():
                client.util.debug("| {}: {}".format(k, v), level=debug_level)

            client.util.debug("| ", level=debug_level)

            if response.content:
                for line in response.content.splitlines():
                    client.util.debug("| " + line.decode("utf8"), level=debug_level)

        # This check can help ensure that the SSL certificate wasn't accidently copied to another sensor.
        # We do this by verifying that the SSL cert matches the identity that the sensor believes it should be.
        if cert and not self._args.ssl_ca_cert and not self._args.ssl_no_verify_certificate and not self._args.ssl_no_verify_hostname and not self._args.fleet:
            uid = response.headers.get("X-CORELIGHT-UID", None)

            if not uid:
                # Fallback for legacy systems.
                uid = response.headers.get("X-BROALA-UID", None)

            if uid:
                # Using default device certificate. Check UID against headers.
                cn = "<unknown>"

                for sub in cert.get("subject", ()):
                    for (key, value) in sub:
                        if key == "commonName":
                            cn = value
                            break

                if cn != "{}.api.appliance.broala.com".format(uid) and \
                   cn != "{}.brobox.corelight.io".format(uid) and \
                   cn != "{}.device.corelight.io".format(uid):
                    raise SessionError("device's UID does not match its certificate (certificate {} for device {})".format(cn, uid))

        if response.status_code == 401:
            raise SessionError("Request not authorized. Did you specify a correct username and password?",
                               None, response.status_code, category=client.exitcodes.AUTH)

        if response.status_code == 403:
            raise SessionError("Operation forbidden. You do not have the needed access right.",
                               None, response.status_code, category=client.exitcodes.AUTH)

        return response

    def _parseContentType(self, response, ignore_errors=False):
        """Parses a Content-Type header from an HTTP response.

        This aborts with a fatal error if the request does not have a
        Content-Type header or it cannot be parsed, unless *ignore_errors* is given.

        response (requests.Response): The response to take the
        ``Content-Type`` header out of.

        ignore_errors (bool): If true, returns ``(None, None, None)`` in case of
        an error, instead if aborting.

        Returns: A 3-tuple ``(ct, st, params)`` where ``ct`` is the main
        type, ``st`` is the sub-type, and ``params`` is a dictionary of
        any additional parameters. The former two are converted to
        lower-case. The dictionaty, all keys are converted to lower-case.
        """
        try:
            ct = response.headers.get("Content-Type")
        except KeyError:
            if ignore_errors:
                return (None, None, None)

            raise SessionError("Response without Content-Type header")

        try:
            m = ct.split(";")
            (ty, st) = m[0].split("/")

            params = {}

            for p in m[1:]:
                (k, v) = p.split("=")
                params[k.strip().lower()] = v.strip()

            return (ty.strip().lower(), st.strip().lower(), params)

        except:
            if ignore_errors:
                return (None, None, None)

            raise SessionError("Cannot parse Content-Type", ct)

    def _requestHeaders(self):
        """
        Returns a pre-populated dictionary of headers we add to all
        outgoing HTTP requests.
        """
        headers = {
            "User-Agent": "{} v{}".format(client.NAME, client.VERSION),
            "Accept": "application/json"
            }

        if self._args.bearer_token:
            headers["Authorization"] = "Bearer {}".format(self._args.bearer_token)

        return headers
