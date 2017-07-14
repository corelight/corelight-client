
.. _brobox-client:

.. Version number is filled in automatically.
.. |version| replace:: 1.0.5

==========================
BroBox Command Line Client
==========================

.. contents::

Overview
========

This tool provides a command-line client for `BroBox One
<https://www.corelight.com>`_, a `Bro <https://www.bro.org>`_
appliance engineered from the ground up by Bro's creators
to transform network traffic into
high-fidelity data for your analytics pipeline. Using the command-line
client, you can configure and control a BroBox remotely through its
comprehensive RESTful API. See the BroBox documentation for an
extended version of this client overview.

:Version: |version|
:Home: http://www.corelight.com
:GitHub: https://github.com/corelight/brobox-client
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

    # pip3 install brobox-client

Alternatively, you can install the latest version from GitHub::

    # git clone https://github.com/corelight/brobox-client
    # cd brobox-client
    # python3 setup.py install

If everything is installed correctly, ``--help`` will give you a usage
message::

    # brobox --help
    Usage: brobox [<global options>] <command> <subcommand> [<options>]
              [--ssl-ca-cert SSL_CA_CERT] [--ssl-no-verify-certificate]
              [--ssl-no-verify-hostname] [--cache CACHE]
    [...]

Note that initially, ``--help`` will not yet show you any further
commands to use. Proceed to the next section to let the client connect
to your device.

Access and Authentication
=========================

You need to enable access to the BroBox API through the device's
configuration interface. You also need to set passwords for the API
users ``admin`` (for unlimited access) and ``monitor`` (for read-only
access). See the BroBox documentation for more information.

Next, you need to tell the ``brobox`` client the network address of
your BroBox. You have three choices for doing that:

- Add ``-b <address>`` to the command-line.

- Create a configuration file ``~/.broboxrc`` with the content
  ``brobox=<address>``.

- Set the environment variable ``BROBOX=<address>``.

If that's all set up, ``brobox --help`` will now ask you for a
username and password, and then show you the full list of commands
that the device API enables the client to offer. If you confirm saving
the credentials, the client will store them in
``~/.brobox/credentials`` for future reuse. You can also specify
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

.. _brobox-client-options:

Global Options
--------------

The ``brobox`` client support the following global command-line
options with all operations:

``--async``
    Does not wait for asynchronous commands to complete before exiting.

``--brobox``
    Specifies the network address of the BroBox device.

``--cache=<file>``
    Sets a custom file for caching BroBox meta data.

``--debug``
    Enables debugging output showing HTTP requests and replies.

``--password``
    Specifies the password for authentication.

``--ssl-ca-cert``
    Specifies a file containing a custom SSL CA certificate for
    validating the device's authenticity.

``--ssl-no-verify-certificate``
    Instructs the client to accept any BroBox device SSL certificate.

``--ssl-no-verify-hostname``
    Instructs the client to accept the BroBox's device SSL certificate
    even if it does not match its hostname.

``--user``
    Specifies the user name for authentication.

``--version``
    Displays the version of the ``brobox`` client and exits.


.. _brobox-client-config:

Configuration File
==================

The ``brobox`` clients looks for a configuration file ``~/.broboxrc``.
The file must consist of lines ``<key>=<value>``. Comments starting
with ``#`` are ignored. ``brobox`` support the following keys:

``brobox``
    The network address of the BroBox device.

``user``
    The user name for authentication.

``password``
    The password for authentication.

``ssl-ca-cert``
    A file containing a custom SSL CA certificate for validating the device's
    authenticity.

``ssl-no-verify-certificate``
    If set to ``false``, the client will accept any BroBox device SSL
    certificate.

``ssl-no-verify-hostname``
    If set to ``false``, the client will accept the BroBox' device SSL
    certificate even if it does not match its hostname.


