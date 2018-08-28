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
from .. import __version__
from ..datastructures import Request
from ..exceptions import HttpError, HttpRedirect, ScraperError
from .cache import CacheAdapterMixin
from .courtesy import CourtesySleepAdapterMixin
from .log import LogEntry, LoggingAdapterMixin

#----------------------------------------------------------------------------------------------------------------------------------

class AdapterBase(object):

    def __init__(self, timeout=30, **kwargs):
        super(AdapterBase, self).__init__(**kwargs)
        self.timeout = timeout

    def send(self, prepared_request, **kwargs):
        kwargs.setdefault('timeout', self.timeout)
        return self.send_base(prepared_request, **kwargs)

    def send_base(self, prepared_request, **kwargs):
        """ This is only here so that tests can override it """
        return super(AdapterBase, self).send(prepared_request, **kwargs)


class AlcazarHttpAdapter(
        CacheAdapterMixin,
        CourtesySleepAdapterMixin,
        LoggingAdapterMixin,
        AdapterBase,
        requests.adapters.HTTPAdapter,
        ):
    pass


class AlcazarSession(requests.Session):

    default_headers = {
        'User-Agent': 'Alcazar/%s' % __version__,

        # Many servers check the presence and content of the Accept header, and use it to block non-browser clients, so it's
        # important to use a browser-like value.
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    def __init__(self, headers={}, **kwargs):
        super(AlcazarSession, self).__init__()
        headers = CaseInsensitiveDict(self.default_headers, **headers)
        if 'user_agent' in kwargs:
            headers['User-Agent'] = kwargs.pop('user_agent')
        self.headers.update(headers)
        adapter = AlcazarHttpAdapter(**kwargs)
        self.mount('http://', adapter)
        self.mount('https://', adapter)

    def send(self, prepared_request, **kwargs):
        # NB this calls itself via indirect recursion (in requests.Session) to handle redirects
        kwargs['is_redirect'] = not kwargs.get('allow_redirects', True)
        kwargs['log'] = LogEntry()
        kwargs['log']['is_redirect'] = kwargs['is_redirect']
        return super(AlcazarSession, self).send(prepared_request, **kwargs)

#----------------------------------------------------------------------------------------------------------------------------------

class HttpClient(object):

    def __init__(self, auto_raise_for_status=True, auto_raise_for_redirect=False, **kwargs):
        self.auto_raise_for_status = auto_raise_for_status
        self.auto_raise_for_redirect = auto_raise_for_redirect
        self.session = AlcazarSession(**kwargs)

    def request(self, request, **kwargs):
        auto_raise_for_status = kwargs.pop('auto_raise_for_status', self.auto_raise_for_status)
        auto_raise_for_redirect = kwargs.pop('auto_raise_for_redirect', self.auto_raise_for_redirect)
        try:
            prepared = self.session.prepare_request(request.to_requests_request())
            response = self.session.send(prepared, **kwargs)
            if auto_raise_for_status:
                response.raise_for_status()
            if auto_raise_for_redirect and 300 <= response.status_code < 400:
                raise HttpRedirect('HTTP %s' % response.status_code, reason=response)
            return response
        except requests.HTTPError as error:
            error_class = getattr(HttpError, 'HTTP_%d' % error.response.status_code, HttpError)
            raise error_class(str(error), reason=error)
        except requests.RequestException as exception:
            raise ScraperError(str(exception), reason=exception)

    def get(self, url, **kwargs):
        kwargs['url'] = url
        kwargs['method'] = 'GET'
        request, rest = self._compile_request(**kwargs)
        return self.request(request, **rest)

    def post(self, url, data, **kwargs):
        kwargs['url'] = url
        kwargs['data'] = data
        kwargs['method'] = 'POST'
        request, rest = self._compile_request(**kwargs)
        return self.request(request, **rest)

    def _compile_request(self, **kwargs):
        request = Request(
            url=kwargs.pop('url'),
            data=kwargs.pop('data', None),
            headers=CaseInsensitiveDict(kwargs.pop('headers', {})),
            method=kwargs.pop('method'),
        )
        return request, kwargs

    def __enter__(self):
        return self

    def __exit__(self, *exception_info):
        self.close()
            
    def close(self):
        self.session.close()

#----------------------------------------------------------------------------------------------------------------------------------
