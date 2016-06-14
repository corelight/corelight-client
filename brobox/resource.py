# Copyright (c) 2016, Broala. All rights reserved.
#
# See COPYING for license information.

import base64
import binascii
import json
import os
import os.path
import sys
import time

import brobox.util

# The format for the readable ASCII representation of times the API returns.
_TimeFormat = "%Y-%m-%d %H:%M:%S %Z"

def _prepareParameters(resource, key, values, params, files):
    """
    Prepares paramaters and fields for a request.

    resource (dict): The meta dictionary for the resource being accessed.

    key (string): The index into *resource* that contains the
    parameters/fields to prepare.

    values (dict string of any):  Dictionary mapping parameter/field names to
    the values we want to send with the request.

    params (dict string of string): A dictionary to which any parameters will
    be added that are to be sent as part of either the URL query or the body
    JSON, depending on the semantics going along with *key*.

    files (dict string of bytes): A dictionary to which any parameters will
    be added that are to be uploaded as files in a form.

    Returns: Nothing, but *params* and *files* will be adapted as suitable.
    """
    for p in resource.get(key, []):
        name = p["name"]
        type = p["type"]
        value = values[name.replace("-", "_")]

        if value is None:
            continue

        if isinstance(value, str) and value.startswith("file://"):
            type = "file"
            value = value[7:]

        if type == "bool" or type == "flag":
            value = ("1" if value else "0")

        if type == "file":
            try:
                file = open(value, "rb")

                if not files is None:
                    files[name] = (os.path.basename(value), file, "application/octet-stream")
                else:
                    params[name] = file.read().decode("utf8")

            except IOError as e:
                brobox.util.fatalError("Cannot open file {}".format(value), e)

            except UnicodeDecodeError:
                brobox.util.fatalError("The file {} contains non-UTF8 characters, which the parameter '{}' does not support".format(value, name))

        else:
            params[name] = str(value)

def _renderObject(response_fields_by_name, obj, hide):
    """
    Helper function to pretty print a dictionary received in a JSON response.

    obj (dict string of any): The dictionary to print.
    """
    def normalize(k, v):
        def fmt_tuple(t):
            return "{:.6f}: {}".format(t[0], t[1])

        field = response_fields_by_name.get(k, {})
        type = field.get("type")

        if isinstance(v, list) and len(v) > 0:
            # Format a time-series a bit more nicely.
            # TODO: We should use type information to make sure it's
            # really a time series.
            l = [(k, fmt_tuple((v[0])))]
            l += [("", fmt_tuple(i)) for i in v[1:]]
            return l

        if type == "time":
            v = time.strftime(_TimeFormat, time.localtime(v))

        return [(k, v)]

    values = sorted(obj.items())
    values = [normalize(k, v) for (k, v) in values if not k in hide]
    values = [i for j in values for i in j] # flatten

    return brobox.util.formatTuples(values)

def _saveFiles(response_fields, obj):
    """
    Helper function to save any files embedded in the response to disk.
    """
    for f in response_fields:
        if f["type"] != "file" or not f["name"] in obj:
            continue

        file = obj[f["name"]]

        try:
            content = base64.standard_b64decode(file["content"])
        except binascii.Error:
            brobox.util.fatalError("cannot decode server's base64 file content")

        # Save content, but don't overwrite existing files.
        fname = file["name"]

        if os.path.exists(fname):
            c = 2
            while True:
                p = "{}.{}".format(fname, c)

                if not os.path.exists(p):
                    fname = p
                    break

                c += 1

        try:
            out = open(fname, "wb")
            out.write(content)
            out.close()

            print("Saved {}".format(fname))

        except IOError:
            brobox.util.fatalError("error saving file", e)

def _responseString(resource, status_code, default=None):
    """
    Maps an error status code received when accessing a resource to the
    message we print to the user.

    resource (dict): The resource meta information.

    status_code (int): The response code from the server.

    default (str): A default to return if we don't know anything further about
    that code.

    Returns: A string with the message.
    """
    try:
        for r in resource["responses"]:
            if r["status"] == status_code:
                return r["description"]
    except KeyError:
        pass

    return {
        401: "Not authorized.",
        403: "Not allowed.",
        404: "Not found.",
        405: "Method not supported.",
        }.get(status_code, default)

def process(session, resource, force_url=None):
    """
    Contacts the BroBox to access a resource.

    session (brobox.session.Session): The session object to use for
    requests.

    resource (dict): The meta information for the resource to access and
    process.

    force_url (None): If given, force use of this URL instead of what would
    normally be used. All other processing remains the same.

    Returns: Nothing
    """
    values = vars(session.arguments())

    url = resource["resource"]
    method = resource.get("method", "GET")

    try:
        if session.arguments().stdin:
            try:
                # Read additional options from standard input.
                values.update(json.load(fp=sys.stdin))
            except ValueError:
                print("Cannot parse JSON on standard input.", file=sys.stderr)
                sys.exit(1)

    except AttributeError:
        # No --stdin option.
        pass

    params = {}
    fields = {}
    files = {}
    json_arg = None

    ### Prepare any request-side parameters/input.

    _prepareParameters(resource, "parameters", values, params, None)
    _prepareParameters(resource, "request-fields", values, fields, files)

    if not files:
        json_arg = fields
    else:
        # Can't send both JSON and multipart form, so we turn the fields
        # into multiparts as well.
        files.update(fields)

    # Replace any templated variables.
    for d in resource["variables"]:
        k = d["name"]
        url = url.replace("{" + k + "}", values[k])

    ### Request resource.

    if force_url:
        url = force_url
        params = {}

    (response, schema, cache, data) = session.retrieveResource(url, method=method, params=params, json=json_arg, files=files)

    _processResponse(session, resource, response, schema, cache, data)

def _processResponse(session, resource, response, schema, cache, data):
    """
    Processes the response after retrieving a resource. This funtion does *not*
    handle ``202 Accepted``.

    session (brobox.session.Session): The session object to use for
    requests.

    resource (dict): The meta information for the resource to access and
    process.

    The other parameters match the result of ``brobox.util.retrieveResource``.
    """
    status = response.status_code
    success = (status >= 200 and status < 300)

    response_fields = resource["response-fields"]
    response_fields_by_name = { f["name"]: f for f in response_fields }

    if not success:
        ### Problem with the request, print error message.

        title = data.get("title", "")
        description = data.get("description", "")
        msg = _responseString(resource, status)

        if title and description:
            error = "Error: {}. {}".format(title, description)

        elif description:
            error = "Error: " + description

        elif msg:
            error = "Error: " + msg

        else:
            error = "Error: {} {}".format(status, response.reason)

        if not error.endswith("."):
            error += "."

        print(error, file=sys.stderr)

        sys.exit(1)

    ### Success, handle result.

    if status == 202 and not session.arguments().async:
        # Print the response string for information.
        msg = _responseString(resource, status, None)

        if msg:
            print(msg)

        (response, schema, cache, data) = _waitForResult(session, response)
        _processResponse(session, resource, response, schema, cache, data)
        return

    if schema == "confirmation":
        # A confirmation is required, ask for it.
        msg = data["message"]
        url = data["confirmation-url"]

        print()
        print("== Confirmation required ==")
        print()
        print(msg)
        print()
        print("== To proceed, enter 'YES': ", end="")
        sys.stdout.flush()

        if sys.stdin.readline() != "YES\n":
            print("== Aborted")
            return

        print("== Confirmed, proceeding")
        print()

        # Reissue the request with the URL we got.
        return process(session, resource, url)

    if not response_fields:
        return

    hide = set([f["name"] for f in response_fields if not f.get("display", True)])

    try:
        if session.arguments().json:
            json.dump(data, fp=sys.stdout, indent=2, sort_keys=True)
            print()
            return

    except AttributeError:
        # No JSON option.
        pass

    if schema == "collection":
        if not isinstance(data, list):
            brobox.util.fatalError("server sent a collection that's not a list")

        if len(data) == 0:
            print("No entries.")

        else:
            first = True

            for obj in data:
                robj = _renderObject(response_fields_by_name, obj, hide)

                if not robj:
                    continue

                if first:
                    print()
                    first = False

                print(robj)

    elif schema == "object":
        _saveFiles(response_fields, data)

        robj = _renderObject(response_fields_by_name, data, hide)
        if robj:
            print()
            print(robj)

    else:
        # Just print the response strings for other schemas.
        msg = _responseString(resource, status, "Success.")
        print(msg)

def _waitForResult(session, response):
    """
    Handle a ``202 Accepted`` response by retrying until the actual response
    becomes available.

    session (brobox.session.Session): The session object to use for
    requests.

    response (requests.Response): The 202 response object.

    The return value matches that of ``brobox.util.retrieveResource``, now
    with the actual response to continue processing with.
    """
    have_output = False

    while True:
        # Result pending, keep trying.
        time.sleep(1)

        location = response.headers.get("location", None)

        if not location:
            brobox.util.fatalError("202 response from server did not have a location header")

        (response, schema, cache, data) = session.retrieveResource(location, method="GET")

        if response.status_code != 202:
            if have_output:
                print()

            return (response, schema, cache, data)

        if sys.stdout.isatty():
            print(".", end="")
            sys.stdout.flush()
            have_output = True


