#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import logging

# 3rd parties
from record import Record, nullable, seq_of

# alcazar
from .datastructures import ScraperRequest
from .husker import Husker
from .stack import Query, StackScraper
from .utils.compatibility import text_type

#----------------------------------------------------------------------------------------------------------------------------------

class SearchResultsList(Record):
    items = seq_of(Husker)
    expected_total_items = nullable(int)
    next_page = nullable(ScraperRequest)

#----------------------------------------------------------------------------------------------------------------------------------

class SearchResultsScraper(StackScraper):
    """
    A refinement of StackScraper for handling the very common case of a site where one needs to submit search queries, iterate
    through the search results pages, and fetch each item individually.

    This class defines two query stages: 'search_results', for requests that fetch a page of search results, and 'payload', for
    pages that contain one instance of whatever payloads the scraper returns.
    """

    payload_type = NotImplemented

    def husk_list(self, page):
        """
        Returns a dict containing: {
            'next_page': optional request for next page in this search results list,
            'expected_total_items': optional int indicating how many items are expected from this search results list,
            'items': sequence of arguments to be passed to `parse_list_item`
        """
        raise NotImplementedError

    def husk_list_item(self, page, item):
        """
        Either:
         - returns a Query
         - returns a dict of extras for a Query of stage 'item'
         - raises SkipThisItem
        """
        raise NotImplementedError

    def get_initial_queries(self):
        for query in self.initial_queries:
            if not isinstance(query, Query):
                if not isinstance(query, dict):
                    query = {'request': query}
                query = Query('search_results', SearchResultsList, **query)
            yield query

    def parse_search_results(self, page):
        list_parts = self.husk_list(page)
        seen_items = page.query.get('seen_items', 0)
        for item in list_parts['items']:
            try:
                parsed_item = self.parse_list_item(page.query, page, item)
                if isinstance(parsed_item, dict):
                    parsed_item = Query('payload', self.payload_type, **item)
                yield parsed_item
            except SkipThisItem as reason:
                logging.info("Skipped one search result: %s" % reason)
            seen_items += 1
        if list_parts.get('next_page'):
            yield Query(
                'search_results',
                SearchResultsList,
                list_parts['next_page'],
                expected_total_items=list_parts.get('expected_total_items', page.query.get('expected_total_items')),
                seen_items=seen_items,
            )
        elif seen_items < 0.9*page.query.get('expected_total_items', seen_items):
            raise Exception("Expected %d results, found %d" % (page.query['expected_total_items'], seen_items))

#----------------------------------------------------------------------------------------------------------------------------------
