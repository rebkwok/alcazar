#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# 3rd parties
import requests

# alcazar
from .html_parser import parse_html_etree
from .http import HttpClient
from .husker import ElementHusker
from .utils.compatibility import string_types

#----------------------------------------------------------------------------------------------------------------------------------

class Fetcher(object):

    html_encoding = None
    html_encoding_errors = 'strict'

    def __init__(self, http=None):
        self.http = http if http is not None else HttpClient()

    def fetch_response(self, request):
        if isinstance(request, string_types):
            request = requests.Request(method='GET', url=request)
        return self.http.request(request)

    def fetch_html(self, *args, **kwargs):
        encoding = kwargs.pop('encoding', None)
        encoding_errors = kwargs.pop('encoding_errors', None)
        response = self.fetch_response(*args, **kwargs)
        return self.parse_html(
            response,
            encoding=encoding,
            encoding_errors=encoding_errors,
        )
        return html

    def parse_html(self, response, encoding=None, encoding_errors=None):
        html_string = response.content.decode(
            encoding=(
                encoding
                or self.html_encoding
                or response.encoding # declared
                or response.apparent_encoding # autodetected
                # NB if we really have no idea what encoding to use, we fall back on UTF-8, which feels safe because it's pretty
                # hard to decode as UTF-8 data that's actually in another, incompatible encoding. We'd rather error out than
                # silently decode using the wrong encoding, and this is what's basically guaranteed to happen if the data isn't
                # UTF-8.
                or 'UTF-8'
            ),
            errors=encoding_errors or self.html_encoding_errors,
        )
        return ElementHusker(parse_html_etree(html_string))

#----------------------------------------------------------------------------------------------------------------------------------
