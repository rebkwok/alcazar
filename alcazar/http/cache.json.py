#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from collections import namedtuple
from copy import copy
from datetime import timedelta
from hashlib import md5
import json
from os import path, makedirs, rename, rmdir, unlink
import pickle
from time import time

# 3rd parties
import requests

# alcazar
from ..utils.compatibility import bytes_type, dbm, text_type

#----------------------------------------------------------------------------------------------------------------------------------

CacheEntry = namedtuple('CacheEntry', (
    'response',
    'exception',
    'timestamp',
))

#----------------------------------------------------------------------------------------------------------------------------------

class CacheHandler(object):
    """
    Mixin for the HttpClient that adds caching capabilities.
    """

    def __init__(self, max_cache_life=None, **kwargs):
        self.max_cache_life = max_cache_life
        self.cache, rest = self._build_cache_from_kwargs(**kwargs)
        self.needs_purge = max_cache_life is not None
        super(CacheHandler, self).__init__(**rest)

    @staticmethod
    def _build_cache_from_kwargs(**kwargs):
        if 'cache' in kwargs:
            cache = kwargs.pop('cache')
        else:
            cache_root_path = kwargs.pop('cache_root_path', None)
            if cache_root_path is not None:
                cache = DiskCache.build(cache_root_path)
            else:
                cache = None
        return cache, kwargs

    def request(self, request, cache_life=None, **rest):
        if self.cache is None:
            return super(CacheHandler, self).request(request, **rest)
        else:
            cache_key, entry = self._get(request, cache_life)
            if entry is None:
                entry = self._fetch(request, rest)
                self.cache.put(cache_key, entry)
            if entry.exception is not None:
                raise entry.exception
            else:
                return entry.response

    def _get(self, request, cache_life):
        now = time()
        if self.needs_purge:
            self.cache.purge(now - self.max_cache_life)
            self.needs_purge = False
        cache_key = self.compute_cache_key(request)
        if cache_life is None:
            cache_life = self.max_cache_life
        min_timestamp = 0 if cache_life is None else (now - cache_life)
        entry = self.cache.get(cache_key, min_timestamp)
        return cache_key, entry

    def _fetch(self, request, rest):
        exception = None
        try:
            response = super(CacheHandler, self).request(request, **rest)
        except Exception as _exception:
            exception = _exception
            response = exception.response
        return CacheEntry(response, exception, time())

    def compute_cache_key(self, request):
        # Note on the use of md5 rather than something stronger:
        # * MD5 hashes are comparatively short, which is convenient when logging and debugging
        # * experience shows it's plenty good enough
        # * if a particular scraper is going to scrape billions of pages, then this method can be overriden
        hexdigest = md5(b''.join(
            repr(part).encode('UTF-8')
            for part in (
                request.method,
                request.url,
                request.params,
                request.data,
            )
        )).hexdigest()
        hexdigest = text_type(hexdigest)
        return (hexdigest[:3], hexdigest[3:])

    def close(self):
        super(CacheHandler, self).close()
        if self.cache is not None:
            self.cache.close()

#----------------------------------------------------------------------------------------------------------------------------------

class Cache(object):

    def get(self, key, min_timestamp):
        """
        Looks up an entry in the cache by key, and returns it. If min_timestamp is not `None`, entries with a timestamp less than
        `min_timestamp` must be ignored.
        """
        raise NotImplementedError

    def put(self, key, entry):
        """
        Saves an entry in the cache, under the given key
        """
        raise NotImplementedError

    def purge(self, min_timestamp):
        """
        Removes from the cache all entries whose `timestamp` is less than the given min_timestamp.
        """

    def close(self):
        """
        Closes any open resources such as file handles. The cache will not be used after it has been closed.
        """
        pass

#----------------------------------------------------------------------------------------------------------------------------------

class DiskCache(Cache):
    """
    The default cache implementation, uses a `shelf` object for the index and one gzipped file per request for the response data.
    """

    def __init__(self, index, storage):
        self.index = index
        self.storage = storage

    @classmethod
    def build(cls, cache_root_path):
        if not path.isdir(cache_root_path):
            makedirs(cache_root_path)
        return cls(
            index=DbmIndex(path.join(cache_root_path, 'index.shelf')),
            storage=FlatFileStorage(cache_root_path),
        )

    def get(self, key, min_timestamp):
        # NB In likely usage scenarios, a `get' that returns None will almost always be followed by a `put' to save a fresh entry
        # under the same key, so deleting entries that are present but outdated might actually slow things down. So don't do it.
        entry = self.index.lookup(key, min_timestamp)
        response = entry and entry.response
        if response is not None:
            self.storage.load(key, response)
        return entry

    def put(self, key, entry):
        # NB doing storage first, then index, ensures that if we're interrupted in between the two we won't end up with an index
        # entry that points to nonexistent data in the storage.
        insert_in_index = lambda: self.index.insert(key, entry)
        if entry.response is not None:
            self.storage.store(
                key,
                entry.response,
                on_completion=insert_in_index,
            )
        else:
            insert_in_index()

    def purge(self, min_timestamp):
        all_keys = tuple(self.index.keys())
        for key in all_keys:
            entry = self.index.lookup(key)
            if entry is not None and entry.timestamp < min_timestamp:
                self.index.delete(key)
                self.storage.remove(key)

    def close(self):
        self.index.close()

#----------------------------------------------------------------------------------------------------------------------------------

class DbmIndex(object):

    # 2017-05-26 - why no pickle? - the requests library has good support for pickling, but there's a few reasons why we're not
    # using that here. When you pickle a Response object, its __getstate__ method ensures that the whole response body is read into
    # the `content' field; this makes sense in general, but in our specific case, we want to store the contents separately from the
    # response, so it makes things a bit messier.
    #
    # Another reason for using JSON instead of pickling is that the data is much easier to inspect manually for debugging purposes,
    # and that's an important feature.

    def __init__(self, file_path):
        self.db = dbm.open(file_path, 'c')
        self.json = RequestsJsonEncoder()

    @staticmethod
    def _key_to_string(key):
        assert isinstance(key, tuple), repr(key)
        return json.dumps(key)

    @staticmethod
    def _string_to_key(text):
        parsed = json.loads(text)
        assert isinstance(parsed, list), repr(parsed)
        return tuple(parsed)

    def lookup(self, key, min_timestamp=None):
        try:
            entry_json = self.db[self._key_to_string(key)]
        except KeyError:
            return None
        else:
            entry = self.json.loads(entry_json)
            if min_timestamp is None or entry.timestamp >= min_timestamp:
                return entry

    def insert(self, key, entry):
        self.db[self._key_to_string(key)] = self.json.dumps(entry)

    def delete(self, key):
        self.db.pop(self._key_to_string(key), None)

    def keys(self):
        for key_string in self.db.keys():
            yield self._string_to_key(key_string)

    def close(self):
        self.db.close()


class RequestsJsonEncoder(object):

    all_encoders = {
        "entry.response": lambda response: response and {
            key: getattr(response, key)
            for key in response.__attrs__
            if key != '_content'
        },
        "entry.response.cookies": lambda jar: dict(jar.items()),
        "entry.response.elapsed": lambda elapsed: elapsed.total_seconds(),
        "entry.exception.response": lambda response: None,
    }

    def default_encoder(self, obj):
        if obj is None or isinstance(obj, (text_type, bytes_type, int, float, bool)):
            return obj
        else:
            return dict(obj.__dict__)

    def encode(self, obj, path):
        encoder = self.all_encoders.get(path, self.default_encoder)
        json_obj = encoder(obj)
        if isinstance(json_obj, dict):
            json_obj = {
                key: self.encode(value, path + '.' + key)
                for key, value in json_obj.items()
            }
        elif isinstance(json_obj, list):
            json_obj = [
                self.encode(value, path + '[]')
                for value in json_obj
            ]
        return json_obj

    @staticmethod
    def set_all_attrs(obj, all_attrs):
        for key, value in all_attrs.items():
            setattr(obj, key, value)
        return obj

    all_decoders = {
        "entry": lambda entry_dict: CacheEntry(
            response=entry_dict['response'],
            exception=set_all_attrs(
                entry_dict['exception'],
                {'response': entry_dict['response']},
            ),
            timestamp=entry_dict['timestamp'],
        ),
        "entry.response": lambda json_dict: set_all_attrs(requests.Response(), json_dict),
        "entry.response.cookies": lambda cookies: requests.cookies.RequestsCookieJar(cookies),
        "entry.response.elapsed": lambda seconds: timedelta(seconds=seconds),
    }

    def decode(self, json_obj, path):
        if isinstance(json_obj, dict):
            json_obj = {
                key: self.decode(value, path + '.' + key)
                for key, value in json_obj.items()
            }
        elif isinstance(json_obj, list):
            json_obj = [
                self.decode(value, path + '[]')
                for value in json_obj
            ]
        decoder = self.all_decoders.get(path)
        if decoder is not None:
            return decoder(json_obj)
        else:
            return json_obj

    def dumps(self, entry):
        return json.dumps(self.encode(entry, 'entry'))

    def loads(self, json_text):
        json_dict = json.loads(json_text)
        return self.decode(json_dict, 'entry')

#----------------------------------------------------------------------------------------------------------------------------------

class FlatFileStorage(object):

    def __init__(self, cache_root_path):
        self.cache_root_path = cache_root_path

    def _file_path(self, key):
        assert isinstance(key, tuple) \
            and all(isinstance(e, text_type) for e in key), \
            repr(key)
        return path.join(self.cache_root_path, *key)

    def load(self, key, response):
        file_path = self._file_path(key)
        handle = open(file_path, 'rb')
        if response._content_consumed:
            with handle:
                response._content = handle.read()
        else:
            response.raw = handle

    def store(self, key, response, on_completion):
        file_path = self._file_path(key)
        if not path.isdir(path.dirname(file_path)):
            makedirs(path.dirname(file_path))
        if response._content_consumed:
            handle = open(file_path, 'wb')
            with handle:
                handle.write(response._content)
            on_completion()
        else:
            part_file_path = file_path + '.part'
            handle = open(part_file_path, 'wb')
            response.raw = StreamTee(
                source=response.raw,
                sink=handle,
                on_close=lambda: [
                    rename(part_file_path, file_path),
                    on_completion(),
                ],
            )

    def remove(self, key):
        file_path = self._file_path(key)
        unlink(file_path)
        self._remove_empty_directories(path.dirname(file_path))

    def _remove_empty_directories(self, dir_path):
        while dir_path != self.cache_root_path:
            try:
                rmdir(dir_path)
            except OSError:
                break # we'll assume it wasn't empty
            dir_path = path.dirname(dir_path)


class StreamTee(object):

    def __init__(self, source, sink, on_close):
        self._source = source
        self._sink = sink
        self._on_close = on_close

    def read(self, *args, **kwargs):
        chunk = self._source.read(*args, **kwargs)
        self._sink.write(chunk)
        return chunk

    def stream(self, *args, **kwargs):
        for chunk in self._source.stream(*args, **kwargs):
            self._sink.write(chunk)
            yield chunk

    def close(self):
        self._source.close()
        self._sink.close()
        self._on_close()

    def __getattr__(self, attr):
        return getattr(self._source, attr)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

#----------------------------------------------------------------------------------------------------------------------------------

class MemoryCache(Cache):
    """
    An alternative implementation of `Cache` that only stores responses to memory. Probably only useful for debugging. 
    """

    def __init__(self, root_path=None):
        assert root_path is None, repr(root_path)
        self.store = {}

    def get(self, key, min_timestamp):
        entry = self.store.get(key)
        if entry is not None and entry.timestamp >= min_timestamp:
            return entry

    def put(self, key, entry):
        self.store[key] = entry

    def purge(self, min_timestamp):
        for key, entry in tuple(self.store.items()):
            if entry.timestamp < min_timestamp:
                del self.store[key]

#----------------------------------------------------------------------------------------------------------------------------------
