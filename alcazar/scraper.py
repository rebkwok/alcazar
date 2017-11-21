#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from datetime import timedelta
from os import path

# alcazar
from .cleaner import Cleaner
from .datastructures import Query
from .fetcher import Fetcher

#----------------------------------------------------------------------------------------------------------------------------------

class Scraper(object):

    id = None
    cache_id = None

    def __init__(self, **kwargs):
        self.id = kwargs.pop('id', self.id) or self.__class__.__name__
        self.cache_id = kwargs.pop('cache_id', self.cache_id) or self.id
        self.fetcher = Fetcher(**_fetcher_kwargs(kwargs, self))
        self.cleaner = Cleaner()
        if kwargs:
            raise TypeError("Unknown kwargs: %s" % ','.join(sorted(kwargs)))

    def request(self, *args, **kwargs):
        # A convenience shortcut. The list of parameters, and the returned type, are up to the fetcher.
        return self.fetcher.compile_request(*args, **kwargs)

    def fetch(self, query, **kwargs):
        # If you want to set fetcher kwargs for a request submitted via `scrape`, you'll need to override this.
        return self.fetcher.fetch(query, **kwargs)

    def parse(self, page):
        # You'll most certainly want to override this
        return page

    def scrape(self, request, parse=None, fetch=None, **extras):
        query = self.compile_query(request, **extras)
        fetch = fetch or self.fetch
        parse = parse or self.parse
        # TODO retry on error
        page = fetch(query)
        return parse(page, **query.extras)

    def compile_query(self, request, **kwargs):
        # 2017-11-20 - I expect crawler.compile_query will override this to parse its own methods (fetch, parse, save)
        methods = {
            name: kwargs.pop(name)
            for name in ('fetch', 'parse')
            if name in kwargs
        }
        return Query(
            self.fetcher.compile_request(request),
            methods,
            extras=kwargs,
        )

#----------------------------------------------------------------------------------------------------------------------------------
# config utils

# This is not especially elegant, but I wanted to be able to:
#
#  * subclass Scraper and set config options as subclass fields
#  * alternatively, directly instantiate Scraper, setting config options as Scraper(**config)
#  * not have to define every class' config options in one big list
#  * not have to define default values more than once
#
# I tried a few 'clever' implementations, which did reduce typing, but meant you actually had to study the config system in order
# to use it. I ended up concluding this was overkill, and hence this little blemish.

FETCHER_KWARGS = (
    'max_cache_life',
    'cache_root_path',
    'timeout',
    'user_agent',
    'html_encoding',
    'html_encoding_errors',
)

def _fetcher_kwargs(kwargs, host=None):
    compiled_kwargs = {}
    missing = object()
    for key in FETCHER_KWARGS:
        value = kwargs.pop(key, getattr(host, key, missing))
        if value is not missing:
            compiled_kwargs[key] = value
    return compiled_kwargs

#----------------------------------------------------------------------------------------------------------------------------------
