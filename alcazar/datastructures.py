#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import re

# alcazar
from .utils.compatibility import string_types, text_type
from .utils.urls import join_urls

#----------------------------------------------------------------------------------------------------------------------------------

class Query(object):

    def __init__(self, request, methods, extras):

        # This holds whatever our fetcher's `compile_request` method returns. As of 2017-11-20 the only Fetcher implementation we
        # have uses the `requests` library as its engine, and this is a `requests.Request` object. It's not decided what the shared
        # interface (i.e. the abstract base class) for all request objects will be, but I figure they should at least have a
        # property called `url`.
        self.request = request

        # A dict that maps the main steps ('fetch' and 'parse') to callables of the correct signature. I've got this idea that if
        # one day Alcazar is extended to support distributed scraping, then the values here, instead of being callables, could be
        # strings that name their respective methods on the crawler object, but that's still to be refined.
        self.methods = methods

        # A dict of extra kwargs to be passed to the parse function.
        self.extras = extras

    @property
    def url(self):
        return self.request.url

    def __repr__(self):
        return "Query(%r, %r, %r)" % (
            self.request,
            self.methods,
            self.extras,
        )

#----------------------------------------------------------------------------------------------------------------------------------

class Page(object):

    def __init__(self, query, response, husker):

        # The Query object that was `fetch`ed
        self.query = query

        # 2017-11-20 - the situation here mirrors that descrived above for Query.request -- at the moment the only Fetcher we have
        # uses the `requests` library, and so this a `requests.Response` object. But eventually I intend to have other fetchers,
        # and it would be up to the fetcher to determine the class of this object. I've not decided yet what the shared interface
        # will be.
        self.response = response

        # A Husker for parsing the response data. Will be of the appropriate Husker subclass, depending on the content type of the
        # data (e.g. if it's an HTML document, this will be an ElementHusker)
        self.husker = husker

    @property
    def url(self):
        # NB this is the URL after redirections, so it could be different from query.url
        if self.response is None:
            return self.query.url
        else:
            return self.response.url

    def link(self, relative_url):
        if not relative_url:
            return relative_url
        if not isinstance(relative_url, string_types):
            relative_url = text_type(relative_url)
        relative_url = re.sub(r'#.*', '', relative_url)
        return join_urls(self.url, relative_url)

    def __call__(self, *args, **kwargs):
        return self.husker(*args, **kwargs)

    def __getattr__(self, attr):
        return getattr(self.husker, attr)

    def __repr__(self):
        return "Page(%r, %r, %r)" % (self.query, self.response, self.husker)

#----------------------------------------------------------------------------------------------------------------------------------
