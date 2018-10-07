#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from contextlib import closing
import re

# alcazar
from .datastructures import Page, Request
from .etree_parser import parse_html_etree, parse_xml_etree
from .http import HttpClient
from .husker import ElementHusker, JmesPathHusker

#----------------------------------------------------------------------------------------------------------------------------------

class Fetcher(object):
    """
    The fetcher turns a `Query` object into a `Page` object. This default implementation uses an in-process HTTP client (which in
    turn, in the default implementation, uses `requests`), but I'm hoping to add other implementations, e.g. a Selenium fetcher,
    or a Chrome DevTools fetcher, that connect to external browser processes.
    """

    def __init__(self, default_config, http_client=None, **kwargs):
        self.default_config = default_config
        self.http = http_client if http_client is not None else HttpClient(default_config, **kwargs)

    def fetch_response(self, query):
        return self.http.submit(query.request, query.config)

    def request(self, request_or_url, **kwargs):
        if isinstance(request_or_url, Request):
            assert not kwargs, "Can't specify kwargs when a Request is used: %r" % kwargs
            return request_or_url
        else:
            return Request(request_or_url, **kwargs)

    def fetch(self, query):
        with closing(self.fetch_response(query)) as response:
            content_type = re.sub(r'\s*;.*', '', response.headers.get('Content-Type') or '')
            if content_type == 'text/html':
                return self.html_page(query, response)
            elif content_type == 'text/xml':
                return self.xml_page(query, response)
            elif content_type == 'application/json':
                return self.json_page(query, response)
            else:
                return self.unparsed_page(query, response)

    def fetch_html(self, query):
        with closing(self.fetch_response(query)) as response:
            return self.html_page(query, response)

    def fetch_xml(self, query):
        with closing(self.fetch_response(query)) as response:
            return self.xml_page(query, response)

    def fetch_json(self, query):
        with closing(self.fetch_response(query)) as response:
            return self.json_page(query, response)

    def html_page(self, query, response):
        html_string = response.content.decode(
            encoding=self._pick_encoding(query, response),
            errors=query.config.encoding_errors,
        )
        husker = ElementHusker(
            parse_html_etree(html_string),
            is_full_document=True,
        )
        return Page(query, response, husker)

    @staticmethod
    def _pick_encoding(query, response):
        return (
            query.config.encoding
            or response.encoding # declared
            or response.apparent_encoding # autodetected
            # NB if we really have no idea what encoding to use, we fall back on UTF-8, which feels safe because it's pretty hard
            # to decode as UTF-8 data that's actually in another, incompatible encoding. We'd rather error out than silently decode
            # using the wrong encoding, and this is what's basically guaranteed to happen if the data isn't UTF-8.
            or 'UTF-8'
        )

    def xml_page(self, query, response):
        # NB we let lxml do the character decoding
        xml_bytes = response.content
        husker = ElementHusker(
            parse_xml_etree(
                xml_bytes,
                strip_namespaces=query.config.strip_namespaces,
            ),
            is_full_document=True,
        )
        return Page(query, response, husker)

    def unparsed_page(self, query, response):
        return Page(query, response, husker=None)

    def json_page(self, query, response):
        husker = JmesPathHusker(response.json())
        return Page(query, response, husker)

    @property
    def default_headers(self):
        # NB this should return the original, modifyable header dict
        return self.http.default_headers

#----------------------------------------------------------------------------------------------------------------------------------
