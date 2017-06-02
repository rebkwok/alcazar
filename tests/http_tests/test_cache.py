#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from contextlib import closing
import gzip
from itertools import count
import json
from os import path, walk
import re
from shutil import rmtree
from tempfile import mkdtemp

# 3rd parties
import requests

# alcazar
from alcazar.http.cache import DiskCache
from alcazar.utils.compatibility import native_string

# tests
from .plumbing import FetcherFixture, ClientFixture, ServerFixture, compile_test_case_classes
from .test_content_encoding import ContentEncodingTests, ContentEncodingTestServer

#----------------------------------------------------------------------------------------------------------------------------------
# fixtures

class CacheTestServer(object):

    def __init__(self):
        self.count = count()

    def counter(self):
        count_text = '%d' % next(self.count)
        return {
            'body': count_text.encode('us-ascii'),
            'headers': {
                'Set-Cookie': 'counter=%s; Path=/' % count_text,
            },
        }

    def five_hundred(self):
        text = "I have failed %d times" % next(self.count)
        return {'body': text.encode('us-ascii'), 'status': 500}

    def fail_once(self):
        self.fail_once = lambda: b'OK'
        return {'body': b'', 'status': 404}

    def echo_headers(self):
        return json.dumps(dict(self.headers)).encode('UTF-8')

    def redirect(self):
        return {
            'body': b'', 
            'status': 301,
            'headers': {
                'Location': '/landing',
                'Set-Cookie': 'redirect=%d; Path=/' % next(self.count),
            },
        }

    def landing(self):
        return {
            'body': b'You got redirected',
            'headers': {
                'Set-Cookie': 'landing=%d; Path=/' % next(self.count),
            }
        }

#----------------------------------------------------------------------------------------------------------------------------------

class CacheFixture(object):
    pass


class DiskCacheFixture(CacheFixture):

    def setUp(self):
        self.temp_dir = mkdtemp()
        super(DiskCacheFixture, self).setUp()

    def cache(self):
        return DiskCache.build(self.temp_dir)

    def tearDown(self):
        super(DiskCacheFixture, self).tearDown()
        rmtree(self.temp_dir)

#----------------------------------------------------------------------------------------------------------------------------------

class UncachedTests(object):

    __fixtures__ = (
        FetcherFixture.__subclasses__(),
        [ClientFixture],
        [ServerFixture],
    )

    new_server = CacheTestServer

    def test_counter_just_counts_up(self):
        self.assertEqual(self.fetch('/counter').text, '0')
        self.assertEqual(self.fetch('/counter').text, '1')
        self.assertEqual(self.fetch('/counter').text, '2')

    def test_failonce_only_fails_once(self):
        with self.assertRaises(requests.exceptions.HTTPError):
            self.fetch('/fail_once')
        self.assertEqual(self.fetch('/fail_once').text, 'OK')

#----------------------------------------------------------------------------------------------------------------------------------

class CachedTests(object):

    __fixtures__ = (
        CacheFixture.__subclasses__(),
        [ClientFixture],
        [ServerFixture],
    )

    new_server = CacheTestServer

    def fetch(self, path, **kwargs):
        client = kwargs.pop('client', self.client)
        return client.get(self.server_url(path), **kwargs)

    def test_counter_is_frozen(self):
        for _ in ('live', 'from-cache'):
            self.assertEqual(self.fetch('/counter').text, '0')

    def test_counter_is_frozen_with_stream_and_dottext(self):
        for _ in ('live', 'from-cache'):
            with closing(self.fetch('/counter', stream=True)) as response:
                self.assertEqual(response.text, '0')

    def test_counter_is_frozen_with_stream_and_rawread(self):
        for _ in ('live', 'from-cache'):
            with closing(self.fetch('/counter', stream=True)) as response:
                self.assertEqual(response.raw.read(), b'0')

    def test_failonce_fails_every_time(self):
        for _ in ('live', 'from-cache'):
            with self.assertRaises(requests.HTTPError):
                self.fetch('/fail_once')

    def test_cache_life_zero_disables_cache(self):
        self.assertEqual(self.fetch('/counter').text, '0')
        self.assertEqual(self.fetch('/counter').text, '0')
        self.assertEqual(self.fetch('/counter', cache_life=0).text, '1')
        self.assertEqual(self.fetch('/counter').text, '1')

    def test_exception_response_is_cached(self):
        for _ in ('live', 'from-cache'):
            with self.assertRaises(requests.HTTPError) as raised:
                self.fetch('/five_hundred')
            self.assertEqual(
                raised.exception.response.text,
                'I have failed 0 times',
            )

    def test_manually_specify_cache_key(self):
        for _ in ('live', 'from-cache'):
            self.assertEqual(self.fetch('/counter', cache_key=('zero',)).text, '0')
            self.assertEqual(self.fetch('/counter', cache_key=('one',)).text, '1')

    # def test_cookies_are_cached(self):
    #     for sweep in ('live', 'from-cache'):
    #         self.client.session.cookies.clear()
    #         response = self.fetch('/landing')
    #         self.assertEqual(
    #             (sweep, dict(response.cookies)),
    #             (sweep, {'landing': '0'}),
    #         )
    #         self.assertEqual(
    #             (sweep, dict(self.client.session.cookies)),
    #             (sweep, {'landing': '0'}),
    #         )

    def test_redirects_are_cached(self):
        for sweep in ('live', 'from-cache'):
            self.assertEqual(
                re.sub(r'^http://[^/]+', '', self.fetch('/redirect').url),
                '/landing',
            )

    # def test_cookies_are_saved_at_every_step_of_redirection(self):
    #     for sweep in ('live', 'from-cache'):
    #         with self.new_client() as client:
    #             self.assertEqual(
    #                 dict(client.session.cookies),
    #                 {},
    #             )
    #             self.fetch('/redirect', client=client)
    #             self.assertEqual(
    #                 (sweep, dict(client.session.cookies)),
    #                 (sweep, {'a': '0', 'b': '1'}),
    #             )

#----------------------------------------------------------------------------------------------------------------------------------

class CachedTestsWithCustomMethods(object):

    __fixtures__ = (
        CacheFixture.__subclasses__(),
        [ClientFixture],
        [ServerFixture],
    )

    new_server = CacheTestServer

    def test_cache_key_includes_method(self):
        for _ in ('live', 'from-cache'):
            self.assertEqual(self.client.get(self.server_url('/counter')).text, '0')
            self.assertEqual(self.client.post(self.server_url('/counter'), b'data').text, '1')

    def test_cache_key_includes_data(self):
        for _ in ('live', 'from-cache'):
            self.assertEqual(self.client.post(self.server_url('/counter'), b'data_0').text, '0')
            self.assertEqual(self.client.post(self.server_url('/counter'), b'data_1').text, '1')

    def _get_x_headers(self, request_headers):
        response = self.client.get(
            self.server_url('/echo_headers'),
            headers=request_headers
        )
        return {
            key.title(): value
            for key, value in response.json().items()
            if key.title().startswith('X-')
        }

    def test_cache_key_excludes_header_keys(self):
        self.assertEqual(
            self._get_x_headers({'X-Header': '0'}),
            {'X-Header': '0'},
        )
        self.assertEqual(
            self._get_x_headers({'X-Header-Bis': '0'}),
            {'X-Header': '0'},
        )

    def test_cache_key_excludes_header_values(self):
        self.assertEqual(
            self._get_x_headers({'X-Header': '0'}),
            {'X-Header': '0'},
        )
        self.assertEqual(
            self._get_x_headers({'X-Header': '1'}),
            {'X-Header': '0'},
        )

#----------------------------------------------------------------------------------------------------------------------------------

# As part of the cache tests, we re-run every content-encoding test method, but each method's body is run twice in succession, to
# ensure that the content-encoding is handled properly both when writing to cache and reading from it

def call_twice(method):
    def wrapped(self):
        method(self)
        method(self)
    return wrapped

ContentEncodingTestsDoubled = type(
    native_string('ContentEncodingTestsDoubled'),
    (object,),
    {
        native_string(key): call_twice(method)
        for key, method in ContentEncodingTests.__dict__.items()
        if key.startswith('test_')
        and callable(method)
    }
)

#----------------------------------------------------------------------------------------------------------------------------------

class CachedContentEncodingTests(ContentEncodingTestsDoubled):

    __fixtures__ = (
        [DiskCacheFixture],
        FetcherFixture.__subclasses__(),
        [ClientFixture],
        [ServerFixture],
    )

    new_server = ContentEncodingTestServer

    def _find_cached_data_file(self):
        all_files = []
        root_path = self.cache().storage.cache_root_path
        for dirpath, dirnames, filenames in walk(root_path):
            if dirpath != root_path:
                all_files.extend(path.join(dirpath, f) for f in filenames)
        self.assertEqual(len(all_files), 1)
        return all_files[0]

    def test_gzipped_contents_is_stored_gzipped(self):
        # 2017-05-29 - Here we're testing what could be said is an implementation detail, but I do feel it's important in practice
        # that storage is always gzipped.
        content = self.fetch('/gzipped').content
        self.assertEqual(content, b"This is the text")
        file_path = self._find_cached_data_file()
        with gzip.open(file_path, 'r') as handle:
            self.assertEqual(handle.read(), content)

    def test_unzipped_contents_also_stored_gzipped(self):
        content = self.client.get(self.server_url('/unzipped')).content
        self.assertEqual(content, b"This is the text")
        file_path = self._find_cached_data_file()
        with gzip.open(file_path, 'r') as handle:
            self.assertEqual(handle.read(), content)

    def test_identity_contents_also_stored_gzipped(self):
        content = self.client.get(self.server_url('/identity')).content
        self.assertEqual(content, b"This is the text")
        file_path = self._find_cached_data_file()
        with gzip.open(file_path, 'r') as handle:
            self.assertEqual(handle.read(), content)

    def test_cached_data_is_never_decoded(self):
        # This test ensures that we don't gunzip and then re-gzip the data, but rather just use the server's encoding
        for _ in ('live', 'from-cache'):
            self.assertEqual(
                self.fetch('/invalid', stream=True).raw.read(),
                b'This is not gzip data',
            )
        with self.assertRaises(requests.exceptions.ContentDecodingError):
            # actually trying to decode it should fail
            bytes().join(self.fetch('/invalid', stream=True).iter_content())

#----------------------------------------------------------------------------------------------------------------------------------

compile_test_case_classes(globals())

#----------------------------------------------------------------------------------------------------------------------------------
