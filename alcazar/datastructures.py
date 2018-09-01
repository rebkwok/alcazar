#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from collections import OrderedDict
import json

# alcazar
from .utils.compatibility import parse_qsl, urlencode, urlparse

# 3rd parties
import requests

#----------------------------------------------------------------------------------------------------------------------------------

class Request(object):
    # 2018-03-10 - for a while I resisted creating my own Request class, thinking requests already has one (2, even), why lengthen
    # the daisy chain. But ther's a few things I wanted that requests.Request doesn't have -- here they are:

    def __init__(self, url, method=None, params=None, data=None, headers=None, json=None): # pylint: disable=redefined-outer-name
        if method:
            assert method.isupper(), repr(method) # just to make sure caller doesn't swap method and url
        else:
            method = 'POST' if data or json else 'GET'
        self._url = url
        self._method = method
        self._params = params
        self._data = data
        self._headers = headers
        self._json = json

    def to_requests_request(self):
        return requests.Request(**self._compile())

    def _compile(self):
        headers = self._headers
        params = self._params
        if params:
            params = OrderedDict(sorted(params.items())) # to avoid thwarting the cache
        data = self._data
        if data and isinstance(data, dict):
            data = OrderedDict(sorted(data.items())) # ditto
        if self._json:
            assert data is None
            # The point of serialising to bytes before passing over to `requests` is to preserve the ordering, so that the cache
            # is still effective
            data = json.dumps(self._json, sort_keys=True).encode('UTF-8')
            headers = dict(headers or {})
            headers['Content-Type'] = 'application/json; charset=UTF-8'
        return {
            'method': self._method,
            'url': self._url,
            'params': params,
            'data': data,
            'headers': headers,
        }

    def modify_params(self, new_params):
        return Request(
            url=self._url,
            method=self._method,
            params=dict(self._params or {}, **new_params),
            data=self._data,
            headers=self._headers,
            json=self._json,
        )

    def add_header(self, key, value):
        return Request(
            url=self._url,
            method=self._method,
            params=self._params,
            data=self._data,
            headers=dict(self._headers or {}, **{key: value}),
            json=self._json,
        )

    def modify_method(self, method):
        return Request(
            url=self._url,
            method=method,
            params=self._params,
            data=self._data,
            headers=self._headers,
            json=self._json,
        )

    def modify_url(self, url):
        return Request(
            url=url,
            method=self._method,
            params=self._params,
            data=self._data,
            headers=self._headers,
            json=self._json,
        )

    @property
    def method(self):
        return self._method

    @property
    def path(self):
        return urlparse(self._url).path

    @property
    def params(self):
        if self._params is not None:
            return self._params
        else:
            return dict(parse_qsl(urlparse(self._url).query))

    @property
    def url(self):
        url = self._url
        if self._params:
            url += '?' + urlencode(OrderedDict(self._params.items()))
        return url

    @property
    def data(self):
        return self._compile()['data']

    def __str__(self):
        if self._method == 'GET':
            return self.url
        else:
            return '<%s %s>' % (self.method, self.url)

def GET(url, params=None, **kwargs): # pylint: disable=invalid-name
    return Request(url, method='GET', params=params, **kwargs)

def POST(url, data=None, **kwargs): # pylint: disable=invalid-name
    return Request(url, method='POST', data=data, **kwargs)

#----------------------------------------------------------------------------------------------------------------------------------

class Query(object):

    def __init__(self, request, methods, extras, depth=0):

        # This holds whatever our fetcher's `compile_request` method returns, typically a Request instance
        self.request = request

        # QueryMethods object that maps the main steps ('fetch' and 'parse') to callables of the correct signature. I've got this
        # idea that if one day Alcazar is extended to support distributed scraping, then the values here, instead of being
        # callables, could be strings that name their respective methods on the crawler object, but that's still to be refined.
        self.methods = methods

        # A dict of extra kwargs to be passed to the parse function. The framework doesn't care what goes in here, it's available
        # for implementations to use however they need.
        self.extras = extras

        # How far from the start query we are. This is maintained by `scraper.link_query`
        self.depth = depth

    @property
    def url(self):
        return self.request and self.request.url

    def __repr__(self):
        return "Query(%r, %r, %r%s)" % (
            self.request,
            self.methods,
            self.extras,
            (' depth=%d' % self.depth) if self.depth else '',
        )

#----------------------------------------------------------------------------------------------------------------------------------

class QueryMethods(object):

    method_names = (
        'fetch',
        'parse',
        'record_payload',
        'record_error',
    )

    def __init__(self, **methods):
        for name in self.method_names:
            setattr(self, name, methods.pop(name))
        assert not methods, repr(methods)

#----------------------------------------------------------------------------------------------------------------------------------

class Page(object):

    def __init__(self, query, response, husker):

        # The Query object that was `fetch`ed
        self.query = query

        # 2017-11-20 - the situation here mirrors that described above for Query.request -- at the moment the only Fetcher we have
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

    @property
    def extras(self):
        return self.query.extras

    def __call__(self, *args, **kwargs):
        return self.husker(*args, **kwargs)

    def __getattr__(self, attr):
        return getattr(self.husker, attr)

    def __repr__(self):
        return "Page(%r, %r, %r)" % (self.query, self.response, self.husker)

#----------------------------------------------------------------------------------------------------------------------------------
