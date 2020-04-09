#!/usr/bin/env python
# -*- coding: utf-8 -*-

# We access a lot of properties whose name starts with an underscore in here, e.g. ._fp -- pylint: disable=protected-access

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
import logging
from os import path, makedirs, rename, rmdir, unlink
import shelve
from time import time

# 3rd parties
try:
    from requests.packages import urllib3
except ImportError:
    import urllib3

# alcazar
from ..utils.compatibility import PY2, pickle, text_type

#----------------------------------------------------------------------------------------------------------------------------------
# data structures

class CacheEntry(namedtuple('CacheEntry', (
        'response',
        'exception',
        'timestamp',
        'raw_headers',
        ))):

    def __new__(cls, response, exception, timestamp, raw_headers=None):
        return super(CacheEntry, cls).__new__(cls, response, exception, timestamp, raw_headers)

#----------------------------------------------------------------------------------------------------------------------------------

class CacheAdapterMixin(object):
    """
    Mixin for the AlcazarHttpClient that adds caching capabilities.
    """

    def __init__(self, base_config, **kwargs):
        self.cache, rest = self._build_cache_from_kwargs(**kwargs)
        super(CacheAdapterMixin, self).__init__(base_config, **rest)
        self.needs_purge = base_config.max_cache_life is not None

    @staticmethod
    def _build_cache_from_kwargs(**kwargs):
        if 'cache' in kwargs:
            cache = kwargs.pop('cache')
            kwargs.pop('cache_id', None)
            if cache is None:
                cache = NullCache()
        else:
            cache_root_path = kwargs.pop('cache_root_path', None)
            cache_id = kwargs.pop('cache_id', None)
            if cache_root_path is not None:
                if cache_id:
                    cache_root_path = path.join(cache_root_path, cache_id)
                cache = DiskCache.build(cache_root_path)
            else:
                cache = NullCache()
        return cache, kwargs

    def send(self, prepared_request, config, **kwargs):
        if not config.use_cache:
            return super(CacheAdapterMixin, self).send(prepared_request, config, **kwargs)
        config_stream = kwargs['stream'] # NB we've passed it from config to kwargs before invoking Session.send()
        kwargs['stream'] = True # regardless of what config_stream is set to -- see below
        log = kwargs['log']
        cache_key, entry = self._get(prepared_request, config)
        log['cache_key'] = cache_key
        if entry is None:
            log['cache_or_courtesy'] = ''
            entry = self._fetch(prepared_request, config, kwargs)
            self.cache.put(cache_key, entry)
        else:
            log['cache_or_courtesy'] = 'cached'
            log['prepared_request'] = prepared_request
            self.logger.flush(log, end='\n')
        if entry.response is not None and not config_stream:
            # Reading the `content` property loads it to memory. We do this here because internally we always require stream=True,
            # but that might not be what the user wanted.
            entry.response.content # pylint: disable=pointless-statement
        if entry.exception is not None:
            raise entry.exception
        else:
            return entry.response

    def _get(self, prepared_request, config):
        now = time()
        if self.needs_purge:
            # NB the per-request config.max_cache_life is never used to purge the whole cache
            self.cache.purge(now - self.base_config.max_cache_life)
            self.needs_purge = False
        cache_key = config.cache_key or self.compute_cache_key(prepared_request, config.cache_key_salt)
        if config.force_cache_stale:
            entry = None
        else:
            min_timestamp = 0 if config.max_cache_life is None else (now - config.max_cache_life)
            entry = self.cache.get(cache_key, min_timestamp)
        return cache_key, entry

    def _fetch(self, prepared_request, config, kwargs):
        exception = None
        try:
            response = super(CacheAdapterMixin, self).send(prepared_request, config, **kwargs)
        except Exception as _exception:
            exception = _exception
            response = getattr(exception, 'response', None)
        return CacheEntry(
            response=response,
            raw_headers=response.raw.headers if response and response.raw else None,
            exception=exception,
            timestamp=time(),
        )

    def compute_cache_key(self, prepared_request, cache_key_salt):
        # Notes on the use of md5 rather than something stronger:
        # * MD5 hashes are comparatively short, which is convenient when logging and debugging
        # * experience shows it's plenty good enough
        # * if a particular scraper is going to scrape billions of pages, then this method can be overriden
        parts = [
            prepared_request.method,
            prepared_request.url,
            prepared_request.body,
        ]
        if cache_key_salt is not None:
            parts.append(cache_key_salt)
        hexdigest = md5(b''.join(
            repr(part).encode('UTF-8')
            for part in parts
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

    def discard(self, key):
        """
        Removed an entry from the cache, if present. Returns a bool indicating whether the entry was present in the cache.
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
        shelf_file_name = 'index.shelf'
        if PY2:
            # The index file contains pickled requests.Response objects, and you can't unpickle in Python 3 a Response object that
            # was pickled in Python 2. The culprit is the OrderedDict shim provided by urllib3. The pickled response includes an
            # OrderedDict object, but the Python 2 shim is not runnable in Python 3 -- unpickling tries to create a
            # urllib3.OrderedDict object in a Python 3 environment, which crashes with "No module named 'dummy_thread'".
            #
            # So Python 2 instances use a different shelf file name. If the same code base is run with both Python versions (as is
            # the case for the samples in the Alcazar distribution folder), they'll each get their own index file, though they can
            # share the request data files.
            shelf_file_name = 'index.p2.shelf'
        return cls(
            index=ShelfIndex(path.join(cache_root_path, shelf_file_name)),
            storage=FlatFileStorage(cache_root_path),
        )

    def get(self, key, min_timestamp):
        # NB In likely usage scenarios, a `get' that returns None will almost always be followed by a `put' to save a fresh entry
        # under the same key, so deleting entries that are present but outdated might actually slow things down. So we don't do it.
        entry = self.index.lookup(key, min_timestamp)
        if entry is not None and entry.response is not None:
            self.storage.load(key, entry)
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
                self.discard(key)

    def discard(self, key):
        was_present = self.index.delete(key)
        self.storage.remove(key)
        return was_present

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
        self.file_path = file_path
        # NB only open DB file on demand, as it opens it exclusively
        self._db = None

    @property
    def db(self):
        if self._db is None:
            try:
                self._db = shelve.open(
                    self.file_path,
                    'c',
                    protocol=pickle.HIGHEST_PROTOCOL,
                )
            except Exception:
                if PY2:
                    logging.exception("Failed to open %s", self.file_path)
                raise Exception("Failed to open %s" % self.file_path)
        return self._db

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
        # logging.debug(
        #     "Cache[%r] entry is %s",
        #     key,
        #     'None' if entry is None
        #     else 'stale (%d, min=%d)' % (entry.timestamp, min_timestamp) if entry.timestamp < (min_timestamp or 0)
        #     else 'fresh (%d, min=%s)' % (entry.timestamp, min_timestamp)
        # )
        if entry is not None and entry.timestamp >= (min_timestamp or 0):
            return entry
        else:
            return None

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
        entry = self.db.pop(self._key_to_string(key), None)
        return entry is not None

    def keys(self):
        for key_string in self.db.keys():
            yield self._string_to_key(key_string)

    def close(self):
        if self._db is not None:
            self._db.close()
            self._db = None

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
        return path.join(self.cache_root_path, *key) + '.gz'

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

    def load(self, key, entry):
        file_path = self._file_path(key)
        response = entry.response
        response.raw = urllib3.HTTPResponse(
            # The data that we write to disk is pre-decoding, which is good because it means in most cases we can have a gzipped
            # cache without expanding CPU cycles for it. However it means that in order to provide the user with decoded data, we
            # need to recreate an HTTPResponse object, since that's the object doing the decoding. Trying to pickle that got messy,
            # so we reconstruct it like this, which isn't pretty, but works.
            headers=urllib3._collections.HTTPHeaderDict(entry.raw_headers if entry.raw_headers is not None else response.headers),
            status=response.status_code,
            reason=response.reason,
            request_method=response.request.method,
            preload_content=False,
            decode_content=False,
            body=AutoClosingFile(self._open_local_file(response, file_path, 'r')),
        )
        response.raw._original_response = MockedHttplibResponse(response.raw)
        response._content_consumed = False
        response._content = False

    def store(self, key, response, on_completion):
        file_path = self._file_path(key)
        if not path.isdir(path.dirname(file_path)):
            makedirs(path.dirname(file_path))
        assert not response._content_consumed, response._content
        if response.raw.chunked:
            # 2017-08-19 - chunked responses can't be streamed to the user and cached simultaneously with the same StreamTee trick
            # that we use below for other responses. This dichotomy is a bit ugly, though, and I'm starting to think a better
            # solution is needed. This works for now, but I think the whole thing needs refactored at some point.
            self._first_download_then_read_from_cache(file_path, response, on_completion)
        else:
            self._download_and_save_to_cache_simultaneously(file_path, response, on_completion)

    def _first_download_then_read_from_cache(self, file_path, response, on_completion):
        with self._open_local_file(response, file_path, 'w') as cache_out:
            for chunk in response.raw.stream(decode_content=False):
                cache_out.write(chunk)
        on_completion()
        response.raw.chunked = False
        response.raw._fp = self._open_local_file(response, file_path, 'r')

    def _download_and_save_to_cache_simultaneously(self, file_path, response, on_completion):
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
        if path.isfile(file_path):
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

    # def readline(self, size=-1):
    #     line = self.source.readline(size)
    #     self.sink.write(line)
    #     if self.remaining is not None:
    #         self.remaining -= len(line)
    #         if self.remaining == 0:
    #             self._complete()
    #     return line

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

    def discard(self, key):
        return False

    def purge(self, min_timestamp):
        pass

    def close(self):
        pass

#----------------------------------------------------------------------------------------------------------------------------------
