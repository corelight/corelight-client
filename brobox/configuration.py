# Copyright (c) 2016, Broala. All rights reserved.
#
# See COPYING for license information.

import os

import brobox.util

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
                brobox.util.fatalError("cannot parse line {} in configuration file".format(cnt), path)

            for option in ("brobox", "user", "password", "ssl-ca-cert", "ssl-no-verify-hostname", "ssl-no-verify-certificate"):
                if k.lower() == option:
                    config[option] = v
                    break

            else:
                brobox.util.fatalError("unknown option '{}' in configuration file".format(k), path)

    except IOError as e:
        brobox.util.fatalError("cannot read configuration file: {}".format(e), path)
