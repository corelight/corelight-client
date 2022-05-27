
.. _corelight-client:

.. Version number is filled in automatically.
.. |version| replace:: 1.5.11

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
