#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# 3rd parties
import requests

# alcazar
from ..config import DEFAULT_CONFIG
from ..exceptions import HttpError, HttpRedirect
from .cache import CacheAdapterMixin
from .courtesy import CourtesySleepAdapterMixin
from .log import LogEntry, LoggingAdapterMixin

#----------------------------------------------------------------------------------------------------------------------------------

class AdapterBaseMixin(object):

    def __init__(self, base_config):
        super(AdapterBaseMixin, self).__init__()
        self.base_config = base_config

    def send(self, prepared_request, _config_unused, **kwargs):
        return self.send_base(prepared_request, **kwargs)

    def send_base(self, prepared_request, **kwargs):
        """ This is only here so that tests can override it """
        kwargs.pop('redirect_count', None) # this is for internal Alcazar use only
        return super(AdapterBaseMixin, self).send(prepared_request, **kwargs)


class AlcazarHttpAdapter(
        CacheAdapterMixin,
        CourtesySleepAdapterMixin,
        LoggingAdapterMixin,
        AdapterBaseMixin,
        requests.adapters.HTTPAdapter,
        ):
    pass


class AlcazarSession(requests.Session):

    default_headers = {
        # Many servers check the presence and content of the Accept header, and use it to block non-browser clients, so it's
        # important to use a browser-like value.
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    def __init__(self, base_config, headers={}, **kwargs):
        super(AlcazarSession, self).__init__()
        self.headers.update(self.default_headers)
        self.headers.update(headers)
        adapter = AlcazarHttpAdapter(base_config, **kwargs)
        self.mount('http://', adapter)
        self.mount('https://', adapter)

    def send(self, prepared_request, config, **kwargs): # pylint: disable=arguments-differ
        # NB this calls itself via indirect recursion (in requests.Session) to handle redirects
        kwargs['redirect_count'] = kwargs.get('redirect_count', -1) + 1
        kwargs['log'] = LogEntry(is_redirect=(kwargs['redirect_count'] > 0))
        return super(AlcazarSession, self).send(prepared_request, config=config, **kwargs)

#----------------------------------------------------------------------------------------------------------------------------------

class HttpClient(object):

    def __init__(self, base_config=DEFAULT_CONFIG, **kwargs):
        kwargs.setdefault('headers', {}) \
            .setdefault('User-Agent', base_config.user_agent)
        self.session = AlcazarSession(base_config, **kwargs)

    def submit(self, request, config):
        try:
            prepared = self.session.prepare_request(request.to_requests_request())
            response = self.session.send(
                prepared,
                config,
                **self._requests_kwargs_from_config(config)
            )
            if config.auto_raise_for_status:
                response.raise_for_status()
            if config.auto_raise_for_redirect and 300 <= response.status_code < 400:
                raise HttpRedirect('HTTP %s' % response.status_code, reason=response)
            return response
        except requests.HTTPError as error:
            error_class = getattr(HttpError, 'Http%d' % error.response.status_code, HttpError)
            raise error_class(str(error), reason=error)
        except requests.RequestException as exception:
            raise HttpError(str(exception), reason=exception)

    @staticmethod
    def _requests_kwargs_from_config(config):
        requests_kwargs = {
            'allow_redirects': config.allow_redirects,
            'stream': config.stream,
            'timeout': config.timeout,
            'verify': config.ssl_verification,
        }
        if config.http_proxy:
            requests_kwargs['proxies'] = {
                'http': config.http_proxy,
                'https': config.https_proxy,
            }
        return requests_kwargs

    def __enter__(self):
        return self

    def __exit__(self, *exception_info):
        self.close()

    def close(self):
        self.session.close() # this will call close on the AlcazarHttpAdapter instance

    @property
    def default_headers(self):
        # NB this returns the original, modifyable header dict
        return self.session.headers

#----------------------------------------------------------------------------------------------------------------------------------
