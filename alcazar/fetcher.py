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
from .husker import ElementHusker

#----------------------------------------------------------------------------------------------------------------------------------

class Fetcher(object):

    def __init__(self):
        self.http = requests.Session()
        # SimpleHTTPClient(
        #     cache_path = here(__file__, '..', '..', 'cache', cache_id),
        #     courtesy_delay = 5,
        #     timeout = config.http_timeout,
        #     user_agent = config.user_agent,
        # )

    def _compile_request(self, url_or_request, **kwargs):
        if isinstance(url_or_request, requests.Request):
            if kwargs:
                raise TypeError("Can't specify parameters AND a compiled request: %r, %r" % (url, kwargs))
            return url_or_request
        else:
            kwargs['url'] = url_or_request
            kwargs.setdefault('method', 'GET' if kwargs.get('data') is None else 'POST')

            # HACK until the session is implemented
            kwargs.pop('cache_life', None)

            return requests.Request(**kwargs)

    def fetch_response(self, *args, **kwargs):
        request = self._compile_request(*args, **kwargs)
        return self.http.request(request)

    # def fetch_bytes(self, *args, **kwargs):
    #     return self.http.request(*args, **kwargs).content

    def fetch_html(self, *args, **kwargs):
        encoding = kwargs.pop('encoding', None)
        encoding_errors = kwargs.pop('encoding_errors', None)
        response = self.fetch_response(*args, **kwargs)
        html = self.parse_html(
            response,
            encoding=encoding,
            encoding_errors=encoding_errors,
        )
        return ElementHusker(response, html)

    def parse_html(self, response, encoding=None, encoding_errors=None):
        html_string = response.content.decode(
            encoding=(
                encoding
                or self.html_encoding
                or response.encoding # declared
                or response.apparent_encoding # autodetected
                # NB if we really have no idea what encoding to use, we fall back on UTF-8, since it's pretty hard to decode as
                # UTF-8 data that's actually in another encoding, and we'd rather error out than silently decode using the wrong
                # encoding.
                or 'UTF-8'
            ),
            errors=encoding_errors or self.html_encoding_errors,
        )
        return parse_html_etree(html_string)

#----------------------------------------------------------------------------------------------------------------------------------
