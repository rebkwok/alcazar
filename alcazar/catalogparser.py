#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from collections import Counter, namedtuple
from contextlib import contextmanager
import logging

# alcazar
from .datastructures import Query
from .exceptions import AlcazarException, SkipThisPage
from .husker import HuskerMismatch
from .scraper import Scraper

#----------------------------------------------------------------------------------------------------------------------------------

CatalogResultList = namedtuple('CatalogResultList', (
    'page',
    'items',
    'expected_total_items',

    # You can have several 'next' links, but they have to be within the same expected_total_items. Multiple lists with separate
    # totals have to be handled separately.
    'next_page_queries',
))

class FewerItemsThanExpected(AlcazarException):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

class CatalogParser(Scraper):

    # Either set these or override the methods that use them below. Some can be set to None to mean "this information is not on the
    # page" -- see how they're used below.
    result_list_path = NotImplemented
    result_item_path = NotImplemented
    no_results_apology_path = NotImplemented
    expected_total_items_path = NotImplemented
    next_page_request_path = NotImplemented
    item_request_path = './/a/@href'

    # In many cases this is the only method you'll need to override. `page` is the item's own page, `item` is whatever
    # `parse_result_items` yields, which by default is the husker for the item in the results list.
    def parse_catalog_item(self, page, item):
        raise NotImplementedError


    ### core loop

    def scrape_catalog(self, start_queries):
        queue = list(map(self.compile_result_list_query, start_queries))
        queue.reverse()
        with self.seen_items_counter() as counter:
            while queue:
                query = queue.pop()
                result_list = self.scrape(query)
                for item in result_list.items:
                    try:
                        yield self.scrape(self.compile_catalog_item_query(
                            result_list.page.link_url(self.husk_item_request(result_list, item)),
                            item,
                            **query.extras
                        ))
                    except SkipThisPage as reason:
                        logging.info("%s -- skipped", reason)
                    counter['seen_items'] += 1
                if result_list.expected_total_items:
                    counter['expected_total_items'] = result_list.expected_total_items
                queue.extend(reversed(result_list.next_page_queries))


    ### result list handling

    def compile_result_list_query(self, request, **extras):
        if isinstance(request, Query):
            assert not extras, (request, extras)
            return request
        else:
            return self.compile_query(
                request,
                fetch=self.fetch_result_list,
                parse=self.parse_result_list,
                record_error=self.record_result_list_error,
                **extras
            )

    def fetch_result_list(self, query, **kwargs):
        return self.fetch(query, **kwargs)

    def parse_result_list(self, page):
        return CatalogResultList(
            page=page,
            items=tuple(self.parse_result_items(page)),
            expected_total_items=self.husk_expected_total_items(page),
            next_page_queries=tuple(self.parse_next_page_queries(page)),
        )

    def parse_result_items(self, page):
        try:
            list_el = self.husk_result_list(page)
        except HuskerMismatch:
            apology = self.husk_no_results_apology(page)
            if apology:
                logging.info(str(apology))
                return []
            else:
                raise
        else:
            return self.husk_result_items(page, list_el)

    def husk_result_list(self, page):
        return page(self.result_list_path)

    def husk_no_results_apology(self, page):
        if self.no_results_apology_path is not None:
            return page.some(self.no_results_apology_path)

    def husk_result_items(self, page, list_el): # pylint: disable=unused-argument
        return list_el.all(self.result_item_path)

    def husk_expected_total_items(self, page):
        if self.expected_total_items_path is not None:
            return page(self.expected_total_items_path).text.sub(r',', '').one(r'(\d+)').int

    def parse_next_page_queries(self, page):
        for request in self.husk_next_page_requests(page):
            yield self.compile_result_list_query(request, **page.query.extras)

    def husk_next_page_requests(self, page):
        # This default implementation assumes there's only 1. If you have a tree-shaped list you need to override this.
        request = page.selection(self.next_page_request_path).dedup().some()
        if request:
            yield page.link_request(request)

    def record_result_list_error(self, query, error):
        return self.record_error(query, error)

    @contextmanager
    def seen_items_counter(self):
        counter = Counter()
        yield counter
        if 'expected_total_items' in counter:
            if counter['seen_items'] >= 0.9*counter['expected_total_items']:
                logging.info(
                    "Found %d of an expected %d catalog items",
                    counter['seen_items'],
                    counter['expected_total_items'],
                )
            else:
                raise FewerItemsThanExpected("Expected %d results, found %d" % (
                    counter['expected_total_items'],
                    counter['seen_items'],
                ))

    ### catalog item handling

    def compile_catalog_item_query(self, request, item, **extras):
        return self.compile_query(
            request,
            fetch=self.fetch_catalog_item,
            parse=lambda page: self.parse_catalog_item(page, item),
            record_payload=self.record_catalog_item_payload,
            record_error=self.record_catalog_item_error,
            **extras
        )

    def fetch_catalog_item(self, query, **kwargs):
        return self.fetch(query, **kwargs)

    def record_catalog_item_payload(self, query, payload):
        return self.record_payload(query, payload)

    def record_catalog_item_error(self, query, error):
        return self.record_error(query, error)

    def husk_item_request(self, _result_list_unused, item):
        return item.all(self.item_request_path).dedup().one()

#----------------------------------------------------------------------------------------------------------------------------------
