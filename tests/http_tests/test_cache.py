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
from alcazar.exceptions import HttpError
from alcazar.http import HttpClient
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

    def one_kilo(self):
        char = '%d' % (next(self.count) % 10)
        text = char * 1024
        return text.encode('us-ascii')

    def double_cookie(self):
        return {
            'body': b'',
            'headers': {
                'Set-Cookie': [
                    'a=1; secure; HttpOnly',
                    'b=2; secure; HttpOnly',
                ],
            },
        }

    def redirect(self):
        return {
            'body': b'', 
            'status': 302,
            'headers': {
                'Location': '/redirect_again',
                'Set-Cookie': 'redirect=%d; Path=/' % next(self.count),
            },
        }

    def redirect_again(self):
        return {
            'body': b'', 
            'status': 302,
            'headers': {
                'Location': '/landing',
                'Set-Cookie': 'redirect_again=%d; Path=/' % next(self.count),
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

class NoCacheFixture(object):
    pass


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
        with self.assertRaises(HttpError):
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
            with self.assertRaises(HttpError):
                self.fetch('/fail_once')

    def test_cache_life_zero_disables_cache(self):
        self.assertEqual(self.fetch('/counter').text, '0')
        self.assertEqual(self.fetch('/counter').text, '0')
        self.assertEqual(self.fetch('/counter', cache_life=0).text, '1')
        self.assertEqual(self.fetch('/counter').text, '1')

    def test_exception_response_is_cached(self):
        for _ in ('live', 'from-cache'):
            with self.assertRaises(HttpError) as raised:
                self.fetch('/five_hundred')
            self.assertEqual(
                raised.exception.reason.response.text,
                'I have failed 0 times',
            )

    def test_manually_specify_cache_key(self):
        for _ in ('live', 'from-cache'):
            self.assertEqual(self.fetch('/counter', cache_key=('zero',)).text, '0')
            self.assertEqual(self.fetch('/counter', cache_key=('one',)).text, '1')

    def test_cookies_are_cached(self):
        for sweep in ('live', 'from-cache'):
            self.client.session.cookies.clear()
            response = self.fetch('/landing')
            self.assertEqual(
                (sweep, dict(response.cookies)),
                (sweep, {'landing': '0'}),
            )
            self.assertEqual(
                (sweep, dict(self.client.session.cookies)),
                (sweep, {'landing': '0'}),
            )
    
    def test_redirects_are_cached(self):
        for sweep in ('live', 'from-cache'):
            response = self.fetch('/redirect')
            self.assertEqual(
                self._url_path(response.url),
                '/landing',
            )
            self.assertEqual(
                response.text,
                'You got redirected',
            )

    def test_cookies_are_saved_at_every_step_of_redirection(self):
        for sweep in ('live', 'from-cache'):
            self.client.session.cookies.clear()
            self.assertEqual(
                dict(self.client.session.cookies),
                {},
            )
            response = self.fetch('/redirect')
            self.assertEqual(
                (sweep, dict(response.cookies)),
                (sweep, {'landing': '2'}),
            )
            self.assertEqual(
                (sweep, dict(self.client.session.cookies)),
                (sweep, {'redirect': '0', 'redirect_again': '1', 'landing': '2'}),
            )

    def test_response_history_is_present(self):
        for sweep in ('live', 'from-cache'):
            final_response = self.fetch('/redirect')
            self.assertEqual(
                (sweep, [self._url_path(response.url) for response in final_response.history + [final_response]]),
                (sweep, ['/redirect', '/redirect_again', '/landing']),
            )

    def test_refetching_a_redirect_without_allow_redirects(self):
        response = self.fetch('/redirect')
        self.assertEqual(self._url_path(response.url), '/landing')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(dict(response.cookies), {'landing': '2'})
        response = self.fetch('/redirect', allow_redirects=False)
        self.assertEqual(self._url_path(response.url), '/redirect')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(dict(response.cookies), {'redirect': '0'})

    def test_can_request_with_streamTrue_a_response_that_was_saved_with_streamFalse(self):
        self.assertEqual(
            self.fetch('/counter').text,
            '0',
        )
        self.assertEqual(
            self.fetch('/counter', stream=True).raw.read(),
            b'0',
        )

    def test_can_request_with_streamFalse_a_response_that_was_saved_with_streamTrue(self):
        self.assertEqual(
            self.fetch('/counter', stream=True).raw.read(),
            b'0',
        )
        self.assertEqual(
            self.fetch('/counter').text,
            '0',
        )

    def test_cacheNone_means_no_cache_not_default_cache(self):
        with HttpClient(cache=None, courtesy_seconds=0, logger=None) as client:
            self.assertEqual(self.fetch('/counter', client=client).text, '0')
            self.assertEqual(self.fetch('/counter', client=client).text, '1')

    def test_if_you_dont_read_from_stream_its_not_cached(self):
        for step, size, char in (
                (0, 512, '0'),  # first, stop half way -- it won't be cached
                (1, 1024, '1'), # then fetch it all -- it'll get cached
                (2, 512, '1'),  # from here on any read will be from cache
                (3, 1024, '1'), # whether partial or complete
                ):
            response = self.fetch('/one_kilo', stream=True)
            args = () if size == 1024 else (size,)
            content = response.raw.read(*args).decode('us-ascii')
            response.close()
            self.assertEqual(
                (step, len(content)),
                (step, size),
            )
            self.assertEqual(
                (step, content),
                (step, char * size),
            )

    @staticmethod
    def _url_path(url):
        return re.sub(r'^https?://[^/]+', '', url)

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

    def test_double_headers_are_available(self):
        headers_live = self.client.get(self.server_url('/double_cookie')).raw.headers._container
        headers_from_cache = self.client.get(self.server_url('/double_cookie')).raw.headers._container
        self.assertEqual(
            headers_live,
            headers_from_cache,
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
                for f in filenames:
                    if not f.endswith('.part'):
                        all_files.append(path.join(dirpath, f))
        self.assertEqual(len(all_files), 1)
        return all_files[0]

    def test_gzipped_contents_is_stored_gzipped(self):
        # 2017-05-29 - Here we're testing what could be said is an implementation detail, but I do feel it's important in practice
        # that storage is always gzipped.
        content = self.fetch('/gzipped').content
        self.assertEqual(content, b"This is the text")
        file_path = self._find_cached_data_file()
        try:
            with gzip.open(file_path, 'r') as handle:
                self.assertEqual(handle.read(), content)
        except OSError:
            from subprocess import check_output
            raise ValueError(check_output(['zcat', file_path]))

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
