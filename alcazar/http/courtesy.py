#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from collections import OrderedDict
from time import sleep, time
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

#----------------------------------------------------------------------------------------------------------------------------------

class CourtesySleepAdapterMixin(object):

    max_dict_size = 10000

    default_ports = {
        'http': 80,
        'https': 443,
    }

    def __init__(self, **rest):
        super(CourtesySleepAdapterMixin, self).__init__(**rest)
        self.last_request_time = OrderedDict()

    def send(self, prepared_request, config, **kwargs):
        courtesy_seconds = 0 if kwargs.get('redirect_count', 0) > 0 else config.courtesy_seconds
        if courtesy_seconds:
            key = self._key(prepared_request)
            self._courtesy_sleep(key, courtesy_seconds, kwargs['log'])
        try:
            return super(CourtesySleepAdapterMixin, self).send(prepared_request, config, **kwargs)
        finally:
            if courtesy_seconds:
                self.last_request_time[key] = time()
                while len(self.last_request_time) > self.max_dict_size:
                    self.last_request_time.popitem(last=False)

    def _key(self, prepared_request):
        parsed = urlparse(prepared_request.url)
        hostname = parsed.hostname
        port = parsed.port or self.default_ports.get(parsed.scheme) or '?'
        return '%s:%s' % (hostname, port)

    def _courtesy_sleep(self, key, courtesy_seconds, log):
        last_request_time = self.last_request_time.get(key)
        if last_request_time:
            earliest_allowed_time = last_request_time + courtesy_seconds
            delay = earliest_allowed_time - time()
        else:
            delay = 0
        if delay > 0:
            printable_delay = int(delay + 0.5)
            if printable_delay:
                log['cache_or_courtesy'] = '%ds' % printable_delay
            self.logger.flush(log)
            self._sleep(delay)

    def _sleep(self, delay):
        # This is in its own method so that tests can override it to check how long we intended to sleep, without actually sleeping
        sleep(delay)

#----------------------------------------------------------------------------------------------------------------------------------
