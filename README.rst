
.. _corelight-client:

.. Version number is filled in automatically.
.. |version| replace:: 1.5.22

====================================
Corelight Sensor Command Line Client
====================================

.. contents::

Overview
========

This tool provides a command-line client for the `Corelight Sensor
<https://www.corelight.com>`_, a `Bro <https://www.bro.org>`_
appliance engineered from the ground up by Bro's creators to transform
network traffic into high-fidelity data for your analytics pipeline.
Using the command-line client, you can configure and control a
Corelight Sensor remotely through its comprehensive RESTful API. See
the Corelight Sensor documentation for an extended version of this
client overview.

:Version: |version|
:Home: http://www.corelight.com
:GitHub: https://github.com/corelight/corelight-client
:Author: `Corelight, Inc. <https://www.corelight.com>`_ <info@corelight.com>

License
=======

This client is open-source under a BSD license. See ``COPYING`` for
details.

Installation
============

The command-line client needs Python >= 3.4 with the ``requests``
module installed as its main dependency.

The easiest way to install the client is through the Python Package
Index::

    # pip3 install corelight-client

Alternatively, you can install the latest version from GitHub::

    # git clone https://github.com/corelight/corelight-client
    # cd corelight-client
    # pip3 install setuptools
    # python3 setup.py install

If everything is installed correctly, ``--help`` will give you a usage
message::

    # corelight-client --help
    Usage: corelight-client [<global options>] <command> <subcommand> [<options>]
              [--ssl-ca-cert SSL_CA_CERT] [--ssl-no-verify-certificate]
              [--ssl-no-verify-hostname] [--cache CACHE]
    [...]

Note that initially, ``--help`` will not yet show you any further
commands to use. Proceed to the next section to let the client connect
to your device.

Access and Authentication
=========================

You need to enable access to the Corelight API through the device's
configuration interface. You also need to set passwords for the API
users ``admin`` (for unlimited access) and ``monitor`` (for read-only
access). See the Corelight Sensor documentation for more information.

Next, you need to tell the ``corelight-client`` the network address of
your Corelight Sensor. You have three choices for doing that:

- Add ``-b <address>`` to the command-line.

- Create a configuration file ``~/.corelight-client.rc`` with the content
  ``device=<address>``.

- Set the environment variable ``CORELIGHT_DEVICE=<address>``.

If that's all set up, ``corelight-client --help`` will now ask you for a
username and password, and then show you the full list of commands
that the device API enables the client to offer. If you confirm saving
the credentials, the client will store them in
``~/.corelight-client/credentials`` for future reuse. You can also specify
authentication information through the `Configuration File`_ or as
`Global Options`_.


Usage
=====

The client offers the API's functionality through a set of commands of
the format ``<command> <subcommand> [options]``. By adding ``--help``
to any command, you get a description of all its functionality and
options.

If the ``--help`` output lists a command's option as being of type
``file``, the client requires you to specify the path to a file to
send. In addition, you can prefix any option's value with ``file://``
to read its content from a file instead of giving it on the
command-line itself.

(Note: The ``--help`` output will contain the list of commands only if
the client can connect, and authenticate, to the device.)

.. _corelight-client-options:

Global Options
--------------

The ``corelight-client`` supports the following global command line
options. The ``--device`` and ``--fleet`` options should be used
mutually exclusively from each other. All other options apply to all
requests:

``--async``
    Does not wait for asynchronous commands to complete before exiting.

``--device``
    Specifies the network address of a Corelight Sensor device.

``--fleet``
    Specifies the network address of a Corelight Fleet Manager.

``--uid``
    Specifies the UID of a Corelight Sensor managed through the
    specified Corelight Fleet Manager.

``--cache=<file>``
    Sets a custom file for caching Corelight Sensor meta data.

``--debug``
    Enables debugging output showing HTTP requests and replies.

``--password``
    Specifies the password for authentication.

``--mfa``
    Specifies the 2FA verification code for authentication with the
    specifed Corelight Fleet Manager. Use '-' to ask the user.

``--ssl-ca-cert``
    Specifies a file containing a custom SSL CA certificate for
    validating the device's authenticity.

``--ssl-no-verify-certificate``
    Instructs the client to accept any Corelight Sensor SSL certificate.

``--ssl-no-verify-hostname``
    Instructs the client to accept the Corelight Sensor's SSL certificate
    even if it does not match its hostname.

``--socket``
    Instructs the client to use a unix domain socket for sending requests.

``--user``
    Specifies the user name for authentication.

``--version``
    Displays the version of the ``corelight-client`` and exits.

``--ignore-meta``
    Do not send metadata info to sensor API call, unless it's specified on CLI.

``--automation``
    Enables a bundle of automation-friendly behavior: request timeouts,
    transient-failure retries, structured JSON errors, the curated
    exit-code taxonomy, and strict non-interactive confirmation. See
    `Automation`_ below for details. Can also be enabled by setting the
    environment variable ``CORELIGHT_AUTOMATION=1``.

``--timeout``
    Sets the request timeout in seconds, either as a single number ``N``
    (applied to both connect and read) or as ``connect,read``. Defaults to
    ``10,3600`` when ``--automation`` is enabled.

``--retries``
    Sets the number of retries to attempt for transient failures (connection
    errors, and HTTP 429/502/503/504 for idempotent requests). Defaults to
    ``3`` when ``--automation`` is enabled, ``0`` otherwise.

``--retry-max-time``
    Sets the maximum total number of seconds to spend on retries. Defaults to
    ``120`` when ``--automation`` is enabled.

``--error-format``
    Sets the output/error format to ``text`` or ``json``. Defaults to
    ``json`` when ``--automation`` is enabled, ``text`` otherwise.

``--assume-yes``
    Proceeds through confirmation-gated operations without prompting
    (alias: ``--confirm``). Required to perform destructive operations
    while ``--automation`` is enabled; otherwise those operations fail
    with a confirmation-required error.

Automation
----------

Passing ``--automation`` (or setting ``CORELIGHT_AUTOMATION=1``) enables a
bundle of automation-friendly behaviors and turns on the exit-code taxonomy
below. It implies ``--noblock`` and defaults to a 10s connect / 3600s read
timeout, 3 retries (capped at 120s total), and JSON output for both success
and error. Each piece can be overridden with its own flag.

Without ``--automation`` there is no request timeout at all (the client blocks
indefinitely), so enabling it never shortens a timeout that existed before. The
default read timeout is deliberately long: it is meant only to bound a wedged
connection, not to cap normal work. Some operations, such as large uploads, can
legitimately take many minutes, and the read timeout applies per network read
rather than to the whole transfer, so a steady upload keeps resetting it. Lower
``--timeout`` if you want automation to give up faster, or raise it for an
unusually large transfer over a slow link.

Retries are idempotency-aware: ``GET``/``HEAD``/``OPTIONS`` requests retry on
connection failures and on HTTP 429/502/503/504. Unsafe methods
(``POST``/``PUT``/``DELETE``) retry only when the connection timed out before it
ever reached the server, so a mutation is never sent twice. For any other
transient failure on an unsafe method the client does not retry; it exits with
the matching code (and sets ``retriable`` in the JSON error envelope) so the
caller, which alone knows whether its operation is safe to repeat, can decide.

``--retry-max-time`` is a total wall-clock budget for the retry loop, measured
from the first attempt and including the time spent in the requests themselves.
It is checked before each new attempt: once the elapsed time plus the next
backoff would exceed it, no further attempt is started. It never interrupts a
request already in flight -- a single request's duration is bounded by the read
timeout above, not by this value.

Exit codes (only when automation is enabled):

===== ====================================================
Code  Meaning
===== ====================================================
0     Success
1     Generic / unexpected error
2     Usage / bad arguments
3     Connect failure or timeout (after retries)
4     Authentication / authorization (401/403)
5     Resource not found (404)
6     Server error (5xx)
7     Confirmation required (declined or blocked)
8     API version unsupported
===== ====================================================

.. _corelight-client-config:

Configuration File
==================

The ``corelight-client`` looks for a configuration file ``~/.corelight-client.rc``.
The file must consist of lines ``<key>=<value>``. Comments starting
with ``#`` are ignored. ``corelight-client`` support the following keys:

``device``
    The network address of a Corelight Sensor device.

``fleet``
    The network address of a Corelight Fleet Manager.

``uid``
    The UID of a Corelight Sensor managed through the specified Corelight Fleet Manager.

``user``
    The user name for authentication.

``password``
    The password for authentication.

``mfa``
    The 2FA verification code for authentication with a Corelight
    Fleet Manager. Use '-' to ask the user.

``ssl-ca-cert``
    A file containing a custom SSL CA certificate for validating the device's
    authenticity.

``ssl-no-verify-certificate``
    If set to ``false``, the client will accept any Corelight Sensor's SSL
    certificate.

``ssl-no-verify-hostname``
    If set to ``false``, the client will accept the Corelight Sensor's SSL
    certificate even if it does not match its hostname.

``socket``
    A unix domain socket to use for sending requests.

``automation``
    If set to a true value, enables automation-friendly behavior. See
    `Automation`_.

``timeout``
    The request timeout in seconds, either as ``N`` or ``connect,read``.

``retries``
    The number of retries to attempt for transient failures.

``retry-max-time``
    The maximum total number of seconds to spend on retries.

``error-format``
    The output/error format, ``text`` or ``json``.
