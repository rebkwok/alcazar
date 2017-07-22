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

#----------------------------------------------------------------------------------------------------------------------------------
# data structures

class Query(object):

    def __init__(self, stage, result_type, request, **extras):
        self.stage = stage
        self.result_type = result_type
        self.request = request
        self.extras = extras

    def __getitem__(self, item):
        return self.extras[item]

    def get(self, item, default=None):
        return self.extras.get(item, default)


class Page(Record):
    query = Query
    request = ScraperRequest
    response = requests.Response
    html = Husker
    url = property(lambda self: self.response.url)


class SkipThisItem(Exception):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

class StackScraper(Scraper):

    ### subclasses are expected to override these:

    # This should be set to a sequence of Query objects
    #
    initial_queries = NotImplemented


    ### These may be overriden, but they have defaults implementations, which will generally be good enough

    def request_for_query(self, query):
        return query.request

    def cache_key_for_query(self, query):
        # By returning None we let http.py pick the cache key the usual way, based on the item URL
        return None

    def get_initial_queries(self):
        """ Override this as a more flexible alternative to just setting `initial_queries` """
        return self.initial_queries


    ### The rest won't typically need to be overriden

    def scrape_all(self):
        stack = list(self.get_initial_queries())
        while stack:
            query = stack.pop()
            process = self.pick_method('process', query.stage)
            subqueries = []
            for result in process(query):
                if isinstance(result, Query):
                    subqueries.append(result)
                else:
                    yield result
            stack.extend(reversed(subqueries))

    def process_default(self, query):
        fetch = self.pick_method('fetch', query.stage)
        parse = self.pick_method('parse', query.stage)
        return parse(fetch(query))

    def fetch_default(self, query):
        request = self.request_for_query(query)
        response = self.fetch_response(request)
        return Page(
            query=query,
            request=request,
            response=response,
            html=self.parse_html(response),
        )

    def parse_default(self, page):
        husk = self.pick_method('husk', page.query.stage)
        yield self.build(page.query.result_type, husk(page))

    def husk_default(self, page):
        # There is no husk_default, if you've not overriden anything else in the chain above, you need to override this
        raise NotImplementedError("{0} should define either a parse_{1} or husk_{1} method".format(
            self.__class__.__name__,
            page.query.stage,
        ))

    def build(self, result_type, parts):
        yield result_type(*{
            key: self.clean(key, field.type, parts.get(key))
            for key, field in result_type.record_fields.items()
        })


    ### privates

    def pick_method(self, action, stage):
        return getattr(self, '%s_%s' % (action, stage), None) \
            or getattr(self, '%s_default' % (action,))

#----------------------------------------------------------------------------------------------------------------------------------
