#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import logging
from os import path, rename
from sys import exc_info
from time import sleep
from traceback import format_exc
from types import GeneratorType

# alcazar
from .config import ScraperConfig
from .datastructures import Page, Query, QueryMethods, Request
from .exceptions import HttpError, ScraperError, SkipThisPage
from .fetcher import Fetcher
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
        self.base_config = ScraperConfig.from_kwargs(kwargs, self)
        self.fetcher = Fetcher(self.base_config, **_extract_fetcher_kwargs(kwargs, self))
        if kwargs:
            raise TypeError("Unknown kwargs: %s" % ','.join(sorted(kwargs)))

    def fetch(self, query, **kwargs):
        return self.fetcher.fetch(
            self.query(query, **kwargs),
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
        if isinstance(error, HttpError):
            logging.error(str(error))
        else:
            logging.error(format_exc())

    def handle_error(self, _query_unused, _error_unused, attempt_i):
        """
        Called when an error has been encountered but the request will be re-attempted.
        """
        delay = 5 ** attempt_i
        _, exc_value, _ = exc_info()
        logging.info("%s - sleeping %d sec%s", exc_value, delay, '' if delay == 1 else 's')
        sleep(delay)

    def record_skipped_page(self, query, reason):
        logging.info("Skipped %s (%s)", query.request, reason)
        return None

    def scrape(self, request_or_query, **kwargs):
        query = self.query(request_or_query, **kwargs)
        methods = query.methods
        for attempt_i in range(query.config.num_attempts_per_scrape):
            if attempt_i > 0:
                query = query.replace_config(force_cache_stale=True)
            try:
                page = methods.fetch(query)
                payload = methods.parse(page)
                if isinstance(payload, GeneratorType):
                    # consume the generator here so that we can catch any exceptions it might raise
                    payload = tuple(payload)
            except SkipThisPage as reason:
                return methods.record_skipped_page(query, reason)
            except ScraperError as error:
                if attempt_i + 1 < query.config.num_attempts_per_scrape:
                    methods.handle_error(query, error, attempt_i)
                else:
                    substitute = methods.record_error(query, error)
                    if substitute is not None:
                        return substitute
                    else:
                        raise
            else:
                return methods.record_payload(page, payload)

    def download(self, request_or_query, local_file_path, overwrite=False, **kwargs):
        query = self.query(
            request_or_query,
            stream=True,
            **kwargs
        )
        if overwrite or not path.exists(local_file_path):
            self.scrape(
                query,
                record_payload=lambda page, _payload_unused: self._save_to_disk(local_file_path, page),
                extras={'local_file_path': local_file_path},
            )
            logging.info('%s saved', local_file_path)
        else:
            logging.info('%s already exists', local_file_path)

    @staticmethod
    def _save_to_disk(local_file_path, page):
        part_file_path = local_file_path + '.part'
        with open(part_file_path, 'wb') as file_out:
            for chunk in page.response.iter_content():
                file_out.write(chunk)
        rename(part_file_path, local_file_path)

    def query(self, request_or_query, **kwargs):
        if isinstance(request_or_query, Query):
            assert not kwargs, "Can't specify kwargs when a Query is used: %r" % kwargs
            return request_or_query
        if isinstance(request_or_query, Request):
            request = request_or_query
        else:
            assert 'url' not in kwargs, (request_or_query, kwargs['url'])
            kwargs['url'] = request_or_query
            request = Request.from_kwargs(kwargs)
        methods = QueryMethods({
            name: kwargs.pop(name, getattr(self, name))
            for name in QueryMethods.method_names
        })
        base_config = self.base_config
        extras = kwargs.pop('extras', {})
        depth = 0
        base = kwargs.pop('base', None)
        if base is not None:
            if isinstance(base, Page):
                base = base.query
            extras = dict(base.extras, **extras)
            base_config = base.config
            depth += 1
            request = request.modify_url(join_urls(base.url, request.url))
        config = ScraperConfig.from_kwargs(
            kwargs,
            base_config,
            consume_all_kwargs_for='query',
        )
        return Query(
            request=request,
            methods=methods,
            config=config,
            extras=extras,
            depth=depth,
        )

    def release_resources(self):
        self.fetcher.release_resources()

#----------------------------------------------------------------------------------------------------------------------------------
# config utils

FETCHER_KWARGS = (
    'cache_id',
    'cache_root_path',
    'headers',
    'http_client',
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
