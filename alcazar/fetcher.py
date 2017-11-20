#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from contextlib import closing
import re

# 3rd parties
import requests

# alcazar
from .datastructures import Page
from .etree_parser import parse_html_etree, parse_xml_etree
from .http import HttpClient
from .husker import ElementHusker
from .utils.compatibility import urljoin

#----------------------------------------------------------------------------------------------------------------------------------

class Fetcher(object):
    """
    The fetcher turns a `Query` object into a `Page` object. This default implementation uses an in-process HTTP client (which in
    turn, in the default implementation, uses `requests`), but I'm hoping to add other implementations, e.g. a Selenium fetcher,
    or a Chrome DevTools fetcher, that connect to external browser processes.
    """

    def __init__(self,
                 http=None,
                 encoding=None,
                 encoding_errors='strict',
                 **kwargs
                ):
        self.http = http if http is not None else HttpClient(**kwargs)
        self.encoding = encoding
        self.encoding_errors = encoding_errors

    def fetch_response(self, query, **kwargs):
        return self.http.request(query.request, **kwargs)

    def compile_request(self, request):
        if isinstance(request, requests.Request):
            return request
        else:
            return requests.Request('GET', request)

    def fetch(self, query, **kwargs):
        with closing(self.fetch_response(query, **kwargs)) as response:
            content_type = re.sub(r'\s*;.*', '', response.headers.get('Content-Type') or '')
            if content_type == 'text/html':
                return self.html_page(query, response)
            elif content_type == 'text/xml':
                return self.xml_page(query, response)
            else:
                raise ValueError("Don't know how to parse %s" % content_type)

    def fetch_html(self, query, **kwargs):
        encoding = kwargs.pop('encoding', None)
        encoding_errors = kwargs.pop('encoding_errors', None)
        with closing(self.fetch_response(query, **kwargs)) as response:
            return self.html_page(
                query,
                response,
                encoding=encoding,
                encoding_errors=encoding_errors,
            )

    def fetch_xml(self, query, **kwargs):
        with closing(self.fetch_response(query, **kwargs)) as response:
            return response, self.xml_page(query, response)

    def html_page(self, query, response, encoding=None, encoding_errors=None):
        html_string = response.content.decode(
            encoding=(
                encoding
                or self.encoding
                or response.encoding # declared
                or response.apparent_encoding # autodetected
                # NB if we really have no idea what encoding to use, we fall back on UTF-8, which feels safe because it's pretty
                # hard to decode as UTF-8 data that's actually in another, incompatible encoding. We'd rather error out than
                # silently decode using the wrong encoding, and this is what's basically guaranteed to happen if the data isn't
                # UTF-8.
                or 'UTF-8'
            ),
            errors=encoding_errors or self.encoding_errors,
        )
        husker = ElementHusker(
            parse_html_etree(html_string),
            is_full_document=True,
        )
        return Page(query, response, husker)

    def xml_page(self, query, response):
        # NB we let lxml do the character decoding
        xml_bytes = response.content
        husker = ElementHusker(parse_xml_etree(xml_bytes))
        return Page(query, response, husker)

#----------------------------------------------------------------------------------------------------------------------------------
