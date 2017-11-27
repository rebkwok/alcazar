#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from datetime import timedelta
import logging
from os import path
from time import sleep
from traceback import format_exc
from types import GeneratorType

# alcazar
from .datastructures import Query
from .exceptions import ScraperError
from .fetcher import Fetcher

#----------------------------------------------------------------------------------------------------------------------------------

class Scraper(object):

    id = None
    cache_id = None

    def __init__(self, **kwargs):
        self.id = kwargs.pop('id', self.id)
        if not self.id and self.__class__.__name__ != 'Scraper':
            self.id = self.__class__.__name__
        self.cache_id = kwargs.pop('cache_id', self.cache_id) or self.id
        self.fetcher = Fetcher(**_fetcher_kwargs(kwargs, self))
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

    def scrape(self, request, parse=None, fetch=None, num_attempts=5, **extras):
        query = self.compile_query(request, **extras)
        fetch = fetch or self.fetch
        parse = parse or self.parse
        for attempt_i in range(num_attempts):
            delay = None
            try:
                # NB it's up to the Fetcher implementation to translate this attempt_i kwarg into config options that disable the
                # cache
                page = fetch(query, attempt_i=attempt_i)
                payload = parse(page, **query.extras)
                if isinstance(payload, GeneratorType):
                    # consume the generator here so that we can catch any exceptions it might raise
                    payload = tuple(payload)
                return payload
            except ScraperError as error:
                if attempt_i+1 < num_attempts:
                    delay = 5 ** attempt_i
                    logging.warning(format_exc())
                    logging.warning("sleeping %d sec%s", delay, '' if delay == 1 else 's')
                else:
                    raise
            # Sleep outside the `except` handler so that a KeyboardInterrupt won't be chained with the ScraperError, which just
            # obfuscates the output
            sleep(delay)

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
