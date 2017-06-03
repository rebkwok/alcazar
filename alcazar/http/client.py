#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# 3rd parties
import requests
from requests.structures import CaseInsensitiveDict

# alcazar
from .cache import CacheHandlerMixin
from .courtesy import CourtesySleepMixin
from .headers import DefaultHeadersMixin

#----------------------------------------------------------------------------------------------------------------------------------

class BaseHttpClient(object):

    def __init__(self, auto_raise_for_status=True):
        self.auto_raise_for_status = auto_raise_for_status
        self.session = requests.Session()

    def request(self, request, auto_raise_for_status=None, **rest):
        if auto_raise_for_status is None:
            auto_raise_for_status = self.auto_raise_for_status
        response = self.base_request(request, **rest)
        if auto_raise_for_status:
            response.raise_for_status()
        return response

    def base_request(self, request, **kwargs):
        # This is a method apart just so that tests can override it. Unlike `request` and `close`, handler mixins are not expected
        # to override it.
        prepared = self.session.prepare_request(request)
        return self.session.send(prepared, **kwargs)
            
    def close(self):
        self.session.close()

#----------------------------------------------------------------------------------------------------------------------------------

class HttpClient(
        DefaultHeadersMixin,
        CacheHandlerMixin,
        CourtesySleepMixin,
        BaseHttpClient,
        ):

    def _compile_request(self, kwargs):
        # NB this method modifies the `kwargs' dictionary
        return requests.Request(
            url=kwargs.pop('url'),
            data=kwargs.pop('data', None),
            headers=CaseInsensitiveDict(kwargs.pop('headers', {})),
            method=kwargs.pop('method'),
        )

    def get(self, url, **kwargs):
        kwargs['url'] = url
        kwargs['method'] = 'GET'
        request = self._compile_request(kwargs)
        return self.request(request, **kwargs)

    def post(self, url, data, **kwargs):
        kwargs['url'] = url
        kwargs['data'] = data
        kwargs['method'] = 'POST'
        request = self._compile_request(kwargs)
        return self.request(request, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *exception_info):
        self.close()

#----------------------------------------------------------------------------------------------------------------------------------
