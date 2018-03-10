#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from datetime import timedelta
import logging
from os import path, rename
from time import sleep
from traceback import format_exc
from types import GeneratorType

# alcazar
from .datastructures import Query, QueryMethods
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

    def compile_request(self, *args, **kwargs):
        # A convenience shortcut. The list of parameters, and the returned type, are up to the fetcher.
        return self.fetcher.compile_request(*args, **kwargs)

    def fetch(self, query, **kwargs):
        # If you want to set fetcher kwargs for a request submitted via `scrape`, you'll need to override this.
        return self.fetcher.fetch(query, **kwargs)

    def parse(self, page):
        # You'll most certainly want to override this
        return page

    def record_payload(self, query, page, payload):
        # If you're happy with just the scraper returning its payload to the caller, you don't need this. Override e.g. to save to
        # DB
        pass

    def record_error(self, query, error):
        # Same as record_payload. The error will be raised unless this returns a truthy value.
        return None

    def scrape(self, request_or_query, num_attempts=5, **kwargs):
        query = self.compile_query(request_or_query, **kwargs)
        methods = query.methods
        for attempt_i in range(num_attempts):
            delay = None
            try:
                # NB it's up to the Fetcher implementation to translate this attempt_i kwarg into config options that disable the
                # cache
                page = methods.fetch(query, attempt_i=attempt_i)
                payload = methods.parse(page)
                if isinstance(payload, GeneratorType):
                    # consume the generator here so that we can catch any exceptions it might raise
                    payload = tuple(payload)
            except ScraperError as error:
                if attempt_i+1 < num_attempts:
                    delay = 5 ** attempt_i
                    logging.error(format_exc())
                    logging.info("sleeping %d sec%s", delay, '' if delay == 1 else 's')
                else:
                    substitute = methods.record_error(query, error)
                    if substitute:
                        return substitute
                    else:
                        raise
            else:
                methods.record_payload(query, page, payload)
                return payload
            # Sleep outside the `except` handler so that a KeyboardInterrupt won't be chained with the ScraperError, which just
            # obfuscates the output
            sleep(delay)

    def download(self, request_or_query, local_file_path, overwrite=False, **kwargs):
        query = self.compile_query(request_or_query, **kwargs)
        if overwrite or not path.exists(local_file_path):
            kwargs['stream'] = True
            self.scrape(
                query,
                record_payload=self._save_to_disk,
            )
            logging.info('%s saved', local_file_path)
        else:
            logging.info('%s already exists', local_file_path)

    def _save_to_disk(self, query, page, payload):
        part_file_path = local_file_path + '.part'
        with open(part_file_path, 'wb') as file_out:
            for chunk in page.response.iter_content():
                file_out.write(chunk)
        rename(part_file_path, local_file_path)

    def compile_query(self, request_or_query, **kwargs):
        # 2017-11-20 - I expect crawler.compile_query will override this to parse its own methods (fetch, parse, save)
        if isinstance(request_or_query, Query):
            assert not kwargs, "Can't specify kwargs when a Query is used: %r" % kwargs
            return request_or_query
        else:
            return Query(
                self.fetcher.compile_request(request_or_query),
                methods=QueryMethods(**{
                    name: kwargs.pop(name, getattr(self, name))
                    for name in QueryMethods.method_names
                }),
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
    'cache_id',
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
