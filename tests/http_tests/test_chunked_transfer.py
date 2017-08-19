#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# tests
from .plumbing import FetcherFixture, ClientFixture, ServerFixture, compile_test_case_classes
from .test_cache import CacheFixture, NoCacheFixture

#----------------------------------------------------------------------------------------------------------------------------------

class ChunkedTransferTestServer(object):

    def chunked(self):
        return {
            'headers': {
                'Transfer-Encoding': 'chunked',
            },
            'body': (
                b'10\r\n'
                + b'look: 16 octets\n\r\n'
                + b'10\r\n'
                + b'oh wow: 16 more\n\r\n'
                + b'0\r\n'
                + b'\r\n'
            ),
        }

#----------------------------------------------------------------------------------------------------------------------------------

class ChunkedTransferTests(object):

    __fixtures__ = [
        [NoCacheFixture] + CacheFixture.__subclasses__(),
        FetcherFixture.__subclasses__(),
        [ClientFixture],
        [ServerFixture],
    ]

    new_server = ChunkedTransferTestServer

    def test_chunked_content_text(self):
        self.assertEqual(
            self.fetch('/chunked').text,
            'look: 16 octets\noh wow: 16 more\n',
        )

    def test_chunked_content_read(self):
        self.assertEqual(
            self.fetch('/chunked', stream=True).raw.read(),
            b'look: 16 octets\noh wow: 16 more\n',
        )

    def test_chunked_content_iter_content(self):
        self.assertEqual(
            bytes().join(self.fetch('/chunked', stream=True).iter_content()),
            b'look: 16 octets\noh wow: 16 more\n',
        )

    # def test_natrail(self):
    #     self.assertRegex(
    #         self.client.get('http://ojp.nationalrail.co.uk/service/timesandfares/EDB/GLQ/110817/1500/dep').text,
    #         r'^\s*<!DOCTYPE',
    #     )

#----------------------------------------------------------------------------------------------------------------------------------

compile_test_case_classes(globals())

#----------------------------------------------------------------------------------------------------------------------------------

def main_debug():
    # Test the test: check that my bogus chunked server above at least spits out correct chunked output
    from .plumbing import HTTPServer, HTTPRequestHandler, native_string
    port = 9871
    handler = ChunkedTransferTestServer()
    server = HTTPServer(('0.0.0.0', port), type(
        native_string('HTTPRequestHandler'),
        (HTTPRequestHandler, object),
        {'handler': handler},
    ))
    print("Starting server in port %d..." % port)
    server.serve_forever()

if __name__ == '__main__':
    main_debug()

#----------------------------------------------------------------------------------------------------------------------------------
