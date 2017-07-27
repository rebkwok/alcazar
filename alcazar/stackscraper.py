#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# 3rd parties
from record import Record
import requests

# alcazar
from .datastructures import ScraperRequest
from .husker import Husker
from .scraper import Scraper
from .utils.compatibility import string_types

#----------------------------------------------------------------------------------------------------------------------------------
# data structures

class Query(object):

    def __init__(self, stage, request, extras={}):
        self.stage = stage
        self.request = request
        self.extras = extras

    def __str__(self):
        return str(self.request)


class Page(Record):
    query = Query
    request = ScraperRequest
    response = requests.Response
    html = Husker
    extras = property(lambda self: self.query.extras)
    url = property(lambda self: self.response.url)

    def __getattr__(self, attr):
        try:
            return getattr(self.html, attr)
        except AttributeError:
            return super(Page, self).__getattr__(attr)


class SkipThisPage(Exception):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

class StackScraper(Scraper):

    ### subclasses will typically override these:

    # This should be set to a sequence of Query objects
    initial_queries = NotImplemented

    # If you set this then your initial_queries can be just a list of requests, `get_initial_queries` will compile them into Query
    # objects automatically
    initial_stage = NotImplemented

    # If you set this then `parse_default` should be enough for your payload stage.
    payload_type = NotImplemented


    ### These may be overriden, but they have defaults implementations, which will generally be good enough

    def request_for_query(self, query):
        return query.request

    def cache_key_for_query(self, query):
        # By returning None we let http.py pick the cache key the usual way, based on the item URL
        return None

    def get_initial_queries(self):
        for query in self.initial_queries:
            if not isinstance(query, Query):
                query = Query(self.initial_stage, request=query)
            yield query


    ### The rest won't typically need to be overriden

    def scrape_all(self):
        stack = list(self.get_initial_queries())
        stack.reverse()
        while stack:
            query = stack.pop()
            process = self._dispatch('process', query.stage)
            try:
                # TODO presumably this is where auto-retry would fit
                query_results = tuple(process(query))
            except SkipThisPage as reason:
                self.log_skipped_page(query, reason)
            else:
                subqueries = []
                for result in query_results:
                    if isinstance(result, Query):
                        subqueries.append(result)
                    else:
                        yield result
                stack.extend(reversed(subqueries))

    def log_skipped_page(self, query, reason):
        logging.info("Skipped %s (%s)", query, reason)

    def process_default(self, query):
        """
        Process is just fetch+parse. Subclases will not typically override this
        """
        fetch = self._dispatch('fetch', query.stage)
        parse = self._dispatch('parse', query.stage)
        return parse(fetch(query))

    def fetch_default(self, query):
        """
        Turns a Query into a Page.
        """
        request = self.request_for_query(query)
        response = self.fetch_response(request)
        return Page(
            query=query,
            request=request,
            response=response,
            html=self.parse_html(response),
        )

    def parse_default(self, page):
        """
        Takes a Page and yields a sequence that can either contain payload objects or further Queries to be added to the stack.
        """
        husk = self._dispatch('husk', page.query.stage)
        yield self.build(self.payload_type, husk(page))

    def husk_default(self, page):
        """
        Takes a Page and returns husked parts for the `build` method.
        """
        # There is no husk_default, if you've not overriden anything else in the chain above, you need to override this
        raise NotImplementedError("{0} should define either a parse_{1} or husk_{1} method".format(
            self.__class__.__name__,
            page.query.stage,
        ))

    def build(self, record_cls, parts):
        """
        Instantiates the given `record_cls` using the given `parts` dict. Not typically overriden.
        """
        if not callable(getattr(parts, 'get', None)):
            parts = dict(parts)
        cleaned = {}
        for key, field in record_cls.record_fields.items():
            try:
                value = parts.get(key)
                if value is not None:
                    value = self.clean(key, field.type, value)
                cleaned[key] = value
            except Exception as exception:
                raise ValueError("Exception while cleaning %s:%r: %s" % (key, value, exception))
        return record_cls(**cleaned)


    ### privates

    def _dispatch(self, action, stage):
        return getattr(self, '%s_%s' % (action, stage), None) \
            or getattr(self, '%s_default' % (action,))

#----------------------------------------------------------------------------------------------------------------------------------
