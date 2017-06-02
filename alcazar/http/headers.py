#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# 3rd parties
from requests.structures import CaseInsensitiveDict

# alcazar
from alcazar import __version__

#----------------------------------------------------------------------------------------------------------------------------------

class DefaultHeadersMixin(object):

    headers = {
        'User-Agent': 'Alcazar/%s' % __version__,

        # Many servers check the presence and content of the Accept header, and use it to block non-browser clients, so it's
        # important to use a browser-like value.
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    def __init__(self, default_headers={}, **rest):
        super(DefaultHeadersMixin, self).__init__(**rest)
        self.headers = CaseInsensitiveDict(self.headers)
        self.headers.update(default_headers)

    def request(self, request, **rest):
        for key, value in self.headers.items():
            request.headers.setdefault(key, value)
        return super(DefaultHeadersMixin, self).request(request, **rest)

#----------------------------------------------------------------------------------------------------------------------------------
