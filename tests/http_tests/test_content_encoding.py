#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from gzip import GzipFile
from io import BytesIO
from shutil import copyfileobj

# alcazar
from alcazar import HttpClient

# tests
from .plumbing import FetcherFixture, ClientFixture, ServerFixture, compile_test_case_classes

#----------------------------------------------------------------------------------------------------------------------------------

class ContentEncodingTestServer(object):

    def gzipped(self):
        buffer = BytesIO()
        with GzipFile(fileobj=buffer, mode='w') as handle:
            handle.write(self.unzipped())
        return {
            'body': buffer.getvalue(),
            'headers': {'Content-Encoding': 'gzip'},
        }

    def unzipped(self):
        return b'This is the text'

    def identity(self):
        return {
            'body': self.unzipped(),
            'headers': {'Content-Encoding': 'identity'},
        }

    def invalid(self):
        return {
            'body': b'This is not gzip data',
            'headers': {'Content-Encoding': 'gzip'},
        }

    def conditional(self):
        if 'gzip' in self.headers.get('Accept-Encoding', ''):
            return self.gzipped()
        else:
            return self.unzipped()

#----------------------------------------------------------------------------------------------------------------------------------

class ContentEncodingTests(object):
    # NB this class is also re-used as part of the caching tests. In that setup these tests will be re-run, with caching enabled

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
        with HttpClient(headers={'Accept-Encoding': None}, logger=None) as client:
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

    def test_raw_file_handle_is_undecoded(self):
        response = self.fetch('/gzipped', stream=True)
        buffer = BytesIO()
        copyfileobj(response.raw, buffer)
        buffer.seek(0)
        with GzipFile(fileobj=buffer) as handle:
            self.assertEqual(
                handle.read(),
                b'This is the text',
            )

    def test_iter_content_is_decoded(self):
        response = self.fetch('/gzipped', stream=True)
        self.assertEqual(
            bytes().join(response.iter_content()),
            b'This is the text',
        )

    def test_iter_lines_is_decoded(self):
        response = self.fetch('/gzipped', stream=True)
        self.assertEqual(
            '\n'.join(response.iter_lines(decode_unicode=True)),
            'This is the text',
        )

#----------------------------------------------------------------------------------------------------------------------------------

compile_test_case_classes(globals())

#----------------------------------------------------------------------------------------------------------------------------------
