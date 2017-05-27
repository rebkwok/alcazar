#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from contextlib import closing
from itertools import count
import json
from shutil import rmtree
from tempfile import mkdtemp

# 3rd parties
import requests

# alcazar
from alcazar import HttpClient
from alcazar.http.cache import DiskCache
from alcazar.utils.compatibility import text_type

# tests
from .plumbing import FetcherFixture, ClientFixture, ServerFixture, compile_test_case_classes

#----------------------------------------------------------------------------------------------------------------------------------
# fixtures

class CacheTestServer(object):

    def __init__(self):
        self.count = count()

    def counter(self):
        return text_type(next(self.count)).encode('ascii')

    def fail_once(self):
        self.fail_once = lambda: b'OK'
        return {'body': b'', 'status': 404}

    def echo_headers(self):
        return json.dumps(dict(self.headers)).encode('UTF-8')

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
        return self.client.get(self.server_url(path), **kwargs)

    def test_counter_is_frozen(self):
        self.assertEqual(self.fetch('/counter').text, '0')
        self.assertEqual(self.fetch('/counter').text, '0')

    def test_counter_is_frozen_with_stream(self):
        with closing(self.fetch('/counter', stream=True)) as response:
            self.assertEqual(response.raw.read(), b'0')
        with closing(self.fetch('/counter', stream=True)) as response:
            self.assertEqual(response.raw.read(), b'0')

    def test_failonce_fails_every_time(self):
        with self.assertRaises(requests.HTTPError):
            self.fetch('/fail_once')
        with self.assertRaises(requests.HTTPError):
            self.fetch('/fail_once')

    def test_cache_life_zero_disables_cache(self):
        self.assertEqual(self.fetch('/counter').text, '0')
        self.assertEqual(self.fetch('/counter').text, '0')
        self.assertEqual(self.fetch('/counter', cache_life=0).text, '1')
        self.assertEqual(self.fetch('/counter').text, '1')

    # def test_streaming_fixture(self):
    #     with closing(self.fetch('/get_baton', stream=True)) as response:
    #         self.handler.baton = b'something else!'
    #         self.assertEqual(response.raw.read(), b'something else!')

#----------------------------------------------------------------------------------------------------------------------------------

class CachedTestsWithCustomMethods(object):

    __fixtures__ = (
        CacheFixture.__subclasses__(),
        [ClientFixture],
        [ServerFixture],
    )

    new_server = CacheTestServer

    def test_cache_key_includes_method(self):
        self.assertEqual(self.client.get(self.server_url('/counter')).text, '0')
        self.assertEqual(self.client.post(self.server_url('/counter'), b'data').text, '1')
        self.assertEqual(self.client.get(self.server_url('/counter')).text, '0')
        self.assertEqual(self.client.post(self.server_url('/counter'), b'data').text, '1')

    def test_cache_key_includes_data(self):
        self.assertEqual(self.client.post(self.server_url('/counter'), b'data_0').text, '0')
        self.assertEqual(self.client.post(self.server_url('/counter'), b'data_1').text, '1')
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

compile_test_case_classes(globals())

#----------------------------------------------------------------------------------------------------------------------------------
