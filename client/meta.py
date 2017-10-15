# Copyright (c) 2017, Corelight. All rights reserved.
#
# See COPYING for license information.

import json

import client.util

class Meta:
    """
    A class storing a Corelight Sensor's meta information, mapping available URLs,
    to their corresponding API meta data.
    """
    def __init__(self, cache):
        """Constructor.
    
        cache (string): The cache ID associated with this set of meta data,
        as reported by the server. If the ID, any cached meta data becomes
        invalid.
        """
        self._cache = cache
        self._resources = {}

    def cacheID(self):
        """
        Returns the cache ID associated with this set of meta data,
        as reported by the server. If the ID, any cached meta
        data becomes invalid.
        """
        return self._cache

    def get(self, url):
        """
        Retrieves the API meta data for a URI.

        Returns: A dictionary with the meta data, nor None if the URL is not
        know."""
        return self._resources.get(url)

    def add(self, url, meta):
        """
        Add a mapping of URL to meta information.

        url (string): The URL to index on.

        meta (dict): A dictionary with Corelight Sensor meta data for the URL
        """
        self._resources[url] = meta

    def save(self, path):
        """
        Save the cache content to disk.

        path (str): The full path where to save the cache.
        """
        with open(path, "w") as fp:
            print("cache-id", self._cache, file=fp)
            json.dump(self._resources, fp=fp, indent=2, sort_keys=True)
            fp.close()

    @classmethod
    def load(cls, path):
        """
        Instantiates a new Meta object from a previously saved cache.

        path (str): The full path where to load the cache from.

        Return: A new ``Meta` instance if it could be successfully reloaded,
        or None if it the path didn't exist or another error occured.
        """
        meta = Meta(-1)

        try:
            with open(path, "r") as fp:
                meta._cache = fp.readline().split()[1]
                meta._resources = json.load(fp=fp)

        except:
            # We just ignore any errors.
            pass

        return meta

    def __iter__(self):
        return self._resources.items().__iter__()

def load(session, base_url, force=False, cache_file=None):
    """
    Downloads the complete set of meta information from a Corelight Sensor.

    session (client.session.Session): The session object to use for
    requests.

    base_url (string): The base URL of the Corelight Sensor's API interface.

    cache_file (str): File where to load cached meta data from if it exists.
    """
    try:
        (_, schema, cache, data) = session.retrieveResource(base_url, debug_level=2)
    except client.session.SessionError as e:
        e.fatalError()

    if schema != "index":
        client.util.fatalError("URL not pointing to API base address", base_url)

    if cache_file and not force:
        cache_file = Meta.load(cache_file)

        if cache_file.cacheID() == cache:
            # Same cache ID, can reuse cached meta data.
            return cache_file

    meta = Meta(cache)

    for url in data:
        _loadResource(session, meta, url)

    return meta

def _loadResource(session, meta, url):
    if meta.get(url):
        return

    try:
        (_, schema, _, data) = session.retrieveResource(url, method="OPTIONS", debug_level=2)
    except client.session.SessionError as e:
        e.fatalError()

    if schema == "index":
        return

    meta.add(url, data)

def _parseLinks(response, rel):
    """
    Parses an HTTP response's ``Link`` headers of a given relation, according
    to the Corelight API specification.

    response (requests.Response): The response to parse the ``Link`` headers
    out of.

    rel (str): The link relation type to parse; all other relations are ignored.

    Returns: A list of 2-tuples ``(string, string)`` where the 1st string is
    the URL parsed out of a ``Link`` header; and the 2nd string is the optional
    title associated with the link or None if none.
    """
    links = response.headers.get("Link", None)

    if not links:
        return []

    result = []

    for l in links.split(","):
        m = l.split(">", 1)
        url = m[0].strip()[1:]

        params = {}

        for p in m[1].split(";"):
            if not p:
                continue

            (k, v) = p.split("=")
            params[k.strip().lower()] = v.strip()

        if params.get("rel", None) != rel:
            continue

        title = params.get("title", None)
        result.append((url, title))

    return result
