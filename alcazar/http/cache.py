#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from collections import namedtuple
from contextlib import contextmanager
import email.message
from functools import partial
import gzip
from hashlib import md5
import json
from os import path, makedirs, rename, rmdir, unlink
import shelve
from time import time

# 3rd parties
import requests

# alcazar
from ..utils.compatibility import pickle, text_type

#----------------------------------------------------------------------------------------------------------------------------------
# data structures

CacheEntry = namedtuple('CacheEntry', (
    'response',
    'exception',
    'timestamp',
))

#----------------------------------------------------------------------------------------------------------------------------------

class CacheAdapterMixin(object):
    """
    Mixin for the AlcazarHttpClient that adds caching capabilities.
    """

    def __init__(self, max_cache_life=None, **kwargs):
        self.cache, rest = self._build_cache_from_kwargs(**kwargs)
        super(CacheAdapterMixin, self).__init__(**rest)
        self.max_cache_life = max_cache_life
        self.needs_purge = max_cache_life is not None

    @staticmethod
    def _build_cache_from_kwargs(**kwargs):
        if 'cache' in kwargs:
            cache = kwargs.pop('cache')
            if cache is None:
                cache = NullCache()
        else:
            cache_root_path = kwargs.pop('cache_root_path', None)
            if cache_root_path is not None:
                cache = DiskCache.build(cache_root_path)
            else:
                cache = NullCache()
        return cache, kwargs

    def send(self, prepared_request, cache_life=None, cache_key=None, **rest):
        stream = rest.get('stream', False)
        rest['stream'] = True
        log = rest['log']
        cache_key, entry = self._get(prepared_request, cache_life, cache_key)
        log['cache_key'] = cache_key
        if entry is None:
            log['cache_or_courtesy'] = ''
            entry = self._fetch(prepared_request, rest)
            self.cache.put(cache_key, entry)
        else:
            log['cache_or_courtesy'] = 'cached'
            log['prepared_request'] = prepared_request
            self.logger.flush(log, end='\n')
        if entry.response is not None and not stream:
            # Reading the `content` property loads it to memory. We do this here because internally we always require stream=True,
            # but that might not be what the user wanted.
            entry.response.content
        if entry.exception is not None:
            raise entry.exception
        else:
            return entry.response

    def _get(self, prepared_request, cache_life, cache_key):
        now = time()
        if self.needs_purge:
            self.cache.purge(now - self.max_cache_life)
            self.needs_purge = False
        if cache_key is None:
            cache_key = self.compute_cache_key(prepared_request)
        if cache_life is None:
            cache_life = self.max_cache_life
        min_timestamp = 0 if cache_life is None else (now - cache_life)
        entry = self.cache.get(cache_key, min_timestamp)
        return cache_key, entry

    def _fetch(self, prepared_request, rest):
        exception = None
        try:
            response = super(CacheAdapterMixin, self).send(prepared_request, **rest)
        except Exception as _exception:
            exception = _exception
            response = getattr(exception, 'response', None)
        return CacheEntry(response, exception, time())

    def compute_cache_key(self, prepared_request):
        # Notes on the use of md5 rather than something stronger:
        # * MD5 hashes are comparatively short, which is convenient when logging and debugging
        # * experience shows it's plenty good enough
        # * if a particular scraper is going to scrape billions of pages, then this method can be overriden
        hexdigest = md5(b''.join(
            repr(part).encode('UTF-8')
            for part in (
                prepared_request.method,
                prepared_request.url,
                prepared_request.body,
            )
        )).hexdigest()
        hexdigest = text_type(hexdigest)
        return (hexdigest[:3], hexdigest[3:])

    def close(self):
        super(CacheAdapterMixin, self).close()
        self.cache.close()

#----------------------------------------------------------------------------------------------------------------------------------

class Cache(object):
    """ Abstract base class for HTTP cache implementations """

    def get(self, key, min_timestamp):
        """
        Looks up an entry in the cache by key, and returns it. Entries with a timestamp less than `min_timestamp` are ignored.
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

#----------------------------------------------------------------------------------------------------------------------------------

class DiskCache(Cache):
    """
    The default cache implementation, uses a `shelf` object as an index that maps cache key to response object, and one gzipped
    file per request for the response data.
    """

    def __init__(self, index, storage):
        self.index = index
        self.storage = storage

    @classmethod
    def build(cls, cache_root_path):
        if not path.isdir(cache_root_path):
            makedirs(cache_root_path)
        return cls(
            index=ShelfIndex(path.join(cache_root_path, 'index.shelf')),
            storage=FlatFileStorage(cache_root_path),
        )

    def get(self, key, min_timestamp):
        # NB In likely usage scenarios, a `get' that returns None will almost always be followed by a `put' to save a fresh entry
        # under the same key, so deleting entries that are present but outdated might actually slow things down. So we don't do it.
        entry = self.index.lookup(key, min_timestamp)
        if entry is not None and entry.response is not None:
            self.storage.load(key, entry.response)
        return entry

    def put(self, key, entry):
        # NB doing storage first, and only inserting into the index once all data has been saved to disk, ensures that if we're
        # interrupted in between the two we won't end up with an index entry that points to nonexistent data in the storage.
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

class ShelfIndex(object):
    """
    Stores request.Response objects into a shelf database. The Response objects are modified before being pickled, so that their
    body content data is not stored in the index (as happens by default when a response object is pickled). Because of this, when
    Response objects are retrieved from the index, they will be lacking their content data.
    """

    def __init__(self, file_path):
        self.db = shelve.open(file_path, 'c', protocol=pickle.HIGHEST_PROTOCOL)

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
        entry = self.db.get(self._key_to_string(key))
        if entry is not None and entry.timestamp >= min_timestamp:
            return entry

    def insert(self, key, entry):
        with self._modify_for_pickling(entry):
            self.db[self._key_to_string(key)] = entry

    @contextmanager
    def _modify_for_pickling(self, entry):
        previous = {}
        if entry.response is not None:
            for key in ('_content', '_content_consumed', 'raw'):
                previous[key] = getattr(entry.response, key)
                setattr(entry.response, key, None)
        yield
        if entry.response is not None:
            for key, value in previous.items():
                setattr(entry.response, key, value)

    def delete(self, key):
        self.db.pop(self._key_to_string(key), None)

    def keys(self):
        for key_string in self.db.keys():
            yield self._string_to_key(key_string)

    def close(self):
        self.db.close()

#----------------------------------------------------------------------------------------------------------------------------------

class FlatFileStorage(object):
    """
    Stores response body content data to disk. The data that gets written to disk is pre-decoding, so if the server gzips data for
    transport (as most web servers do), we'll store that gzipped data to disk.
    """

    def __init__(self, cache_root_path):
        self.cache_root_path = cache_root_path

    def _file_path(self, key):
        if not (
                isinstance(key, tuple)
                and all(isinstance(e, text_type) for e in key)
                ):
            raise ValueError("Invalid cache key: %r" % key)
        return path.join(self.cache_root_path, *key)

    @staticmethod
    def _open_local_file(response, file_path, mode):
        # If the response does not have an encoding, we use the 'gzip' module, so that the data is stored to disk in compressed
        # format
        content_encoding = response.headers.get('Content-Encoding')
        if content_encoding is None or content_encoding == 'identity':
            opener = gzip.open
        else:
            opener = open
            mode += 'b'
        return opener(file_path, mode)

    def load(self, key, response):
        file_path = self._file_path(key)
        response.raw = requests.packages.urllib3.HTTPResponse(
            # The data that we write to disk is pre-decoding, which is good because it means in most cases we can have a gzipped
            # cache without expanding CPU cycles for it. However it means that in order to provide the user with decoded data, we
            # need to recreate an HTTPResponse object, since that's the object doing the decoding. Trying to pickle that got messy,
            # so we reconstruct it like this, which isn't pretty, but works.
            headers=dict(response.headers),
            status=response.status_code,
            reason=response.reason,
            request_method=response.request.method,
            preload_content=False,
            decode_content=False,
            body=AutoClosingFile(self._open_local_file(response, file_path, 'r')),
        )
        response.raw._original_response = MockedHttplibResponse(response)
        response._content_consumed = False
        response._content = False

    def store(self, key, response, on_completion):
        file_path = self._file_path(key)
        if not path.isdir(path.dirname(file_path)):
            makedirs(path.dirname(file_path))
        assert not response._content_consumed, response._content
        part_file_path = file_path + '.part'
        response.raw._fp.fp = StreamTee(
            source=response.raw._fp.fp,
            sink=self._open_local_file(response, part_file_path, 'w'),
            length=response.raw._fp.length,
            on_completion=lambda: [
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


class MockedHttplibResponse(object):
    """
    Wherein we realise that under the requests library's respectable and elegant interface is a matryoshka of HTTP libraries,
    several layers deep, peppered with a generous amount of backwards compatibility and other hacks.

    We need this for requests' `extract_cookies_to_jar` to work.
    """

    def __init__(self, urllib3_response):
        self.msg = email.message.Message()
        self.msg._headers = list(urllib3_response.headers.items())
        self.msg.getheaders = partial(self.msg.get_all, failobj=[])

    def isclosed(self):
        return True


class StreamTee(object):
    """
    Readable file-like object that simply wraps around another file object (the "source") and pipes its data through, unmodified;
    every time some data is read, however, we also write it so a separate file (the "sink"). This allows us to save to cache
    streamed HTTP responses, without having to load the data to memory.
    """

    def __init__(self, source, sink, length, on_completion):
        self.source = source
        self.sink = sink
        self.remaining = length
        self.on_completion = on_completion

    def read(self, *args):
        chunk = self.source.read(*args)
        self.sink.write(chunk)
        want_everything = not args or (args[0] in (-1, None))
        if self.remaining is not None:
            self.remaining -= len(chunk)
        if want_everything or not chunk or self.remaining == 0:
            self._complete()
        return chunk

    def readinto(self, b):
        n = self.source.readinto(b)
        self.sink.write(b[:n])
        if self.remaining is not None:
            self.remaining -= n
        if n == 0 or self.remaining == 0:
            self._complete()
        return n

    def flush(self):
        self.source.flush()
        self.sink.flush()

    def close(self):
        self.source.close()
        self.sink.close()

    @property
    def closed(self):
        return self.source.closed

    def _complete(self):
        if self.on_completion is not None:
            self.on_completion()
            self.on_completion = None


class AutoClosingFile(object):
    """
    Readable file-like object that closes automatically once its data is exhausted.
    """

    def __init__(self, wrapped):
        self.wrapped = wrapped

    def read(self, *args):
        chunk = self.wrapped.read(*args)
        want_everything = not args or (args[0] in (-1, None))
        if want_everything or not chunk:
            self.close()
        return chunk

    def stream(self, *args, **kwargs):
        for chunk in self.wrapped.stream(*args, **kwargs):
            yield chunk
        self.close()

    def close(self):
        if not self.wrapped.closed:
            self.wrapped.close()

    @property
    def closed(self):
        return self.wrapped.closed

#----------------------------------------------------------------------------------------------------------------------------------

class NullCache(Cache):
    """
    Cache that does not cache. It makes the code lighter to use this when the client is configured without a cache, than to have 
    if/else checks throughout.
    """

    def get(self, key, min_timestamp):
        pass

    def put(self, key, entry):
        pass

    def purge(self, min_timestamp):
        pass

    def close(self):
        pass

#----------------------------------------------------------------------------------------------------------------------------------
