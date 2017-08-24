# Copyright (c) 2017, Corelight. All rights reserved.
#
# See COPYING for license information.

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
