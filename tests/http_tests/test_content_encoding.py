#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from gzip import GzipFile
from io import BytesIO

# alcazar
from alcazar import HttpClient

# tests
from .plumbing import FetcherFixture, ClientFixture, ServerFixture, compile_test_case_classes

#----------------------------------------------------------------------------------------------------------------------------------

class ContentEncodingTestServer(object):

    def gzipped(self):
        buffer = BytesIO()
        with GzipFile(fileobj=buffer, mode='w') as handle:
            handle.write(b'This is the text')
        return {
            'body': buffer.getvalue(),
            'headers': {'Content-Encoding': 'gzip'},
        }

    def unzipped(self):
        return b'This is the text'

    def conditional(self):
        if 'gzip' in self.headers.get('Accept-Encoding', ''):
            return self.gzipped()
        else:
            return self.unzipped()

#----------------------------------------------------------------------------------------------------------------------------------

class ContentEncodingTests(object):

    # see also `test_default_accept_encoding_header` in headers.py

    __fixtures__ = [
        FetcherFixture.__subclasses__(),
        [ClientFixture],
        [ServerFixture],
    ]

    new_server = ContentEncodingTestServer

    def test_unzipped_content_is_shown_as_is(self):
        self.assertEqual(
            self.fetch('/unzipped').text,
            'This is the text',
        )

    def test_gzipped_content_is_gunzipped_transparently(self):
        self.assertEqual(
            self.fetch('/gzipped').text,
            'This is the text',
        )

    def test_gzipped_content_requested_by_default(self):
        response = self.fetch('/conditional')
        self.assertEqual(
            response.headers.get('Content-Encoding'),
            'gzip',
        )
        self.assertEqual(
            response.text,
            'This is the text',
        )

    def test_unzipped_content_can_be_selected_in_constructor(self):
        with HttpClient(default_headers={'Accept-Encoding': None}) as client:
            response = self.fetch('/conditional', client=client)
        self.assertNotIn(
            'Content-Encoding',
            response.headers,
        )
        self.assertEqual(
            response.text,
            'This is the text',
        )

    def test_unzipped_content_can_be_selected_in_method(self):
        response = self.fetch(
            '/conditional',
            headers={'Accept-Encoding': None},
        )
        self.assertNotIn(
            'Content-Encoding',
            response.headers,
        )
        self.assertEqual(
            response.text,
            'This is the text',
        )

#----------------------------------------------------------------------------------------------------------------------------------

compile_test_case_classes(globals())

#----------------------------------------------------------------------------------------------------------------------------------
