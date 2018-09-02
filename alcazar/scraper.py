#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from functools import partial
import logging
from os import path, rename
import re
from time import sleep
from traceback import format_exc
from types import GeneratorType

# alcazar
from .datastructures import Query, QueryMethods, Request
from .exceptions import ScraperError, SkipThisPage
from .fetcher import Fetcher
from .forms import Form
from .utils.compatibility import string_types, text_type
from .utils.urls import join_urls

#----------------------------------------------------------------------------------------------------------------------------------

class Scraper(object):

    id = None
    cache_id = None
    num_attempts_per_scrape = 5

    def __init__(self, **kwargs):
        super(Scraper, self).__init__()
        self.id = kwargs.pop('id', self.id)
        if not self.id and self.__class__.__name__ != 'Scraper':
            self.id = self.__class__.__name__
        self.cache_id = kwargs.pop('cache_id', self.cache_id) or self.id
        self.fetcher = Fetcher(**_extract_fetcher_kwargs(kwargs, self))
        if kwargs:
            raise TypeError("Unknown kwargs: %s" % ','.join(sorted(kwargs)))

    def fetch(self, query, **kwargs):
        # If you want to set fetcher kwargs for a request submitted via `scrape`, you'll need to override this.
        return self.fetcher.fetch(
            self.compile_query(query),
            **kwargs
        )

    def parse(self, page):
        # You'll most certainly want to override this
        return page

    def record_payload(self, page, payload): # pylint: disable=unused-argument
        # If you're happy with just the scraper returning its payload to the caller, you don't need this. Override e.g. to save to
        # DB
        return payload

    def record_error(self, query, error): # pylint: disable=unused-argument
        # Same as record_payload. The error will be raised unless this returns a truthy value.
        logging.error(format_exc())

    def record_skipped_page(self, query, reason):
        logging.info("Skipped %s (%s)", query.request, reason)
        return None

    def scrape(self, request_or_query, **kwargs):
        num_attempts = kwargs.pop('num_attempts', self.num_attempts_per_scrape)
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
            except SkipThisPage as reason:
                return self.record_skipped_page(query, reason)
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
                return methods.record_payload(page, payload)
            # Sleep outside the `except` handler so that a KeyboardInterrupt won't be chained with the ScraperError, which just
            # obfuscates the output
            sleep(delay)

    def link_url(self, page, url):
        base_url = page.url
        if not base_url:
            return url
        if not url:
            return base_url
        if not isinstance(url, string_types):
            url = text_type(url)
        url = re.sub(r'#.*', '', url)
        return join_urls(base_url, url)

    def link_request(self, page, request):
        if isinstance(request, Request):
            return request.modify_url(self.link_url(page, request.url))
        else:
            return Request(self.link_url(page, request))

    def link_query(self, page, request, **kwargs):
        merged_extras = dict(page.query.extras)
        merged_extras.update(kwargs.pop('extras', {}))
        kwargs['extras'] = merged_extras
        kwargs['depth'] = page.query.depth + 1
        return self.compile_query(
            self.link_request(page, request),
            **kwargs
        )

    def download(self, request_or_query, local_file_path, overwrite=False, **kwargs):
        query = self.compile_query(request_or_query, **kwargs)
        if overwrite or not path.exists(local_file_path):
            kwargs['stream'] = True
            self.scrape(
                query,
                record_payload=self._save_to_disk,
                extras={'local_file_path': local_file_path},
            )
            logging.info('%s saved', local_file_path)
        else:
            logging.info('%s already exists', local_file_path)

    def _save_to_disk(self, page, _payload_unused):
        part_file_path = page.extras['local_file_path'] + '.part'
        with open(part_file_path, 'wb') as file_out:
            for chunk in page.response.iter_content():
                file_out.write(chunk)
        rename(part_file_path, page.extras['local_file_path'])

    def compile_request(self, *args, **kwargs):
        # A convenience shortcut. The list of parameters, and the returned type, are up to the fetcher.
        return self.fetcher.compile_request(*args, **kwargs)

    def compile_query(self, request_or_query, **kwargs):
        if isinstance(request_or_query, Query):
            assert not kwargs, "Can't specify kwargs when a Query is used: %r" % kwargs
            return request_or_query
        else:
            methods = {
                name: kwargs.pop(name, getattr(self, name))
                for name in QueryMethods.method_names
            }
            fetcher_kwargs = _extract_fetcher_kwargs(kwargs)
            if fetcher_kwargs:
                methods['fetch'] = partial(methods['fetch'], **fetcher_kwargs)
            extras = kwargs.pop('extras', {})
            if kwargs:
                raise TypeError("Unknown kwargs: %s" % ','.join(sorted(kwargs)))
            return Query(
                self.fetcher.compile_request(request_or_query),
                methods=QueryMethods(**methods),
                extras=extras,
            )

    def parse_form(self, page, husker):
        return Form(page, husker)

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
    'allow_redirects',
    'cache_id',
    'cache_key',
    'cache_key_salt',
    'cache_root_path',
    'courtesy_seconds',
    'encoding',
    'encoding_errors',
    'max_cache_life',
    'timeout',
    'use_cache',
    'user_agent',
)

def _extract_fetcher_kwargs(kwargs, host=None):
    compiled_kwargs = {}
    missing = object()
    for key in FETCHER_KWARGS:
        value = kwargs.pop(key, getattr(host, key, missing))
        if value is not missing:
            compiled_kwargs[key] = value
    return compiled_kwargs

#----------------------------------------------------------------------------------------------------------------------------------
