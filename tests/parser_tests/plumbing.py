#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from functools import wraps
from os.path import dirname, join as path_join
from random import randrange
import re
from threading import Event, Thread

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

# alcazar
from alcazar.html_parser import parse_html_etree
from alcazar.http import HttpClient
from alcazar.utils.compatibility import bytes_type

#----------------------------------------------------------------------------------------------------------------------------------

class AlcazarTest(object):

    def fixture_path(self, *relative_path):
        return path_join(
            dirname(__file__),
            'fixtures',
            *relative_path
        )

    def open_fixture(self, *relative_path):
        return open(
            self.fixture_path(*relative_path),
            'rb',
        )

#----------------------------------------------------------------------------------------------------------------------------------

class HtmlFixture(object):

    fixture_file = None
    fixture_encoding = 'us-ascii'

    def setUp(self):
        super(HtmlFixture, self).setUp()
        if self.fixture_file is not None:
            with self.open_fixture(self.fixture_file) as fh:
                self.html = parse_html_etree(fh.read().decode(self.fixture_encoding))
        else:
            self.html = None

    def assertXPath(self, xpath, expected):
        self.assertEqual(
            self.html.xpath(xpath),
            expected,
        )


def with_inline_html(html_string):
    def make_wrapper(func):
        @wraps(func)
        def wrapper(self):
            assert getattr(self, 'html', None) is None
            self.html = parse_html_etree(html_string)
            func(self)
            self.html = None
        return wrapper
    return make_wrapper

#----------------------------------------------------------------------------------------------------------------------------------
