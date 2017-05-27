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

class CourtesySleep(object):

    max_dict_size = 10000

    default_ports = {
        'http': 80,
        'https': 443,
    }

    def __init__(self, courtesy_seconds=5, **rest):
        super(CourtesySleep, self).__init__(**rest)
        self.courtesy_seconds = courtesy_seconds
        self.last_request_time = OrderedDict()

    def request(self, request, **kwargs):
        courtesy_seconds = kwargs.pop('courtesy_seconds', self.courtesy_seconds)
        if courtesy_seconds:
            key = self._key(request)
            self._courtesy_sleep(key, courtesy_seconds)
        try:
            return super(CourtesySleep, self).request(request, **kwargs)
        finally:
            if courtesy_seconds:
                self.last_request_time[key] = time()
                while len(self.last_request_time) > self.max_dict_size:
                    self.last_request_time.popitem(last=False)

    def _key(self, request):
        parsed = urlparse(request.url)
        hostname = parsed.hostname
        port = parsed.port or self.default_ports.get(parsed.scheme) or '?'
        return '%s:%s' % (hostname, port)

    def _courtesy_sleep(self, key, courtesy_seconds):
        last_request_time = self.last_request_time.get(key)
        if last_request_time:
            earliest_allowed_time = last_request_time + courtesy_seconds
            delay = earliest_allowed_time - time()
            if delay > 0:
                # if delay > 0.5:
                #     print('sleeping %ds courtesy seconds', int(delay+0.5))
                self._sleep(delay)

    def _sleep(self, delay):
        # This is in its own method so that tests can override this to check how long we sleep without actually sleeping
        sleep(delay)

#----------------------------------------------------------------------------------------------------------------------------------
