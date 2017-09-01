# Copyright (c) 2017, Corelight. All rights reserved.
#
# See COPYING for license information.

import json
import os
import sys

import client.util

def read(path, config):
    """
    Read user configuration file.

    path (str): Full path to configuration file.

    config (dict str of str): Dictionary to add options to.
    """
    if not os.path.isfile(path):
        return config

    try:
        cnt = 0

        for line in open(path):
            cnt += 1
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            try:
                (k, v) = (m.strip() for m in line.split("="))
            except ValueError:
                client.util.fatalError("cannot parse line {} in configuration file".format(cnt), path)

            for option in ("device", "user", "password", "ssl-ca-cert", "ssl-no-verify-hostname", "ssl-no-verify-certificate", "brobox"):
                if k.lower() == option:
                    config[option] = v
                    break

            else:
                client.util.fatalError("unknown option '{}' in configuration file".format(k), path)

            # Legacy BroBox support. To be removed.
            if config.get("brobox", None) and not config.get("device", None):
                print("""Note: Please use 'device' instead of 'brobox' in {}.
      The old option is deprecated and support will be removed in a future version.
""".format(path), file=sys.stderr)
                config["device"] = config["brobox"]
                del config["brobox"]

    except IOError as e:
        client.util.fatalError("cannot read configuration file: {}".format(e), path)

def readCredentials(path, device_id):
    """
    Read credentials from the on-disk cache.

    path (str): Full path to credentials file.

    device_id (str): Unique ID for the device we are talking to.

    Returns: A tuple (user, password), with values being None that could not
    be determined.
    """
    if not os.path.isfile(path):
        return (None, None)

    try:
        with open(path, "r") as fp:
            data = json.load(fp)

        creds = data.get(device_id, None)
        if creds and "user" in creds and "password" in creds:
            return (creds.get("user", None), creds.get("password", None))
        else:
            return (None, None)

    except ValueError:
        # Problem with the JSON file, silently ignore.
        return (None, None)

    except IOError as e:
        client.util.fatalError("cannot read credentials file: {}".format(e), path)
        return (None, None)

def saveCredentials(path, args, device_id):
    """
    Saves credentials to the on-disk cache.

    path (str): Full path to credentials file.

    args (ArgumentParser): Arguments instance to retrieve credentials from.

    device_id (str): Unique ID for the device we are talking to.
    """
    try:
        with open(path, "r") as fp:
            data = json.load(fp)
            fp.close()
    except (IOError, ValueError):
        # Ok if it doesn't exist yet, or we cannot parse it.
        data = {}

    data[device_id] = { "user": args.user, "password": args.password }

    try:
        with open(path, "w") as fp:
            json.dump(data, fp, indent=2)
            fp.close()

        os.chmod(path, 0o600)
        print("Credentials saved to {}".format(path))

    except IOError as e:
        client.util.fatalError("cannot save credentials to '{}'".format(path), e)
