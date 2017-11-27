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
from .crawler import Crawler
from .exceptions import AlcazarException, SkipThisPage
from .husker import HuskerMismatch, ListHusker
from .utils.compatibility import text_type

#----------------------------------------------------------------------------------------------------------------------------------

CatalogResultList = namedtuple('CatalogResultList', (
    'page',
    'items',
    'expected_total_items',
    'next_page_request',
))

class FewerItemsThanExpected(AlcazarException):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

class CatalogParser(object):

    # Either set these or override the methods that use them below. Some can be set to None to mean "this information is not on the
    # page" -- see how they're used below.
    result_list_path = NotImplemented
    result_item_path = NotImplemented
    no_results_apology_path = NotImplemented
    expected_total_items_path = NotImplemented
    next_page_request_path = NotImplemented
    item_request_path = './/a/@href'

    # In most cases this is the only method you'll need to override. `page` is the item's own page, `item` is whatever
    # `husk_result_items` yields, which by default is the husker for the item in the results list.
    def parse_catalog_item(self, page, item):
        raise NotImplementedError

    def scrape_catalog(self, start_requests, **extras):
        with self.seen_items_counter() as counter:
            for start_request in start_requests:
                request = start_request
                while request:
                    result_list = self.scrape(
                        request,
                        self.parse_result_list,
                        **extras
                    )
                    for item in result_list.items:
                        try:
                            yield self.scrape_item(result_list.page, item, **extras)
                        except SkipThisPage as reason:
                            logging.info("%s -- skipped", reason)
                        counter['seen_items'] += 1
                    if result_list.expected_total_items:
                        counter['expected_total_items'] = result_list.expected_total_items
                    request = result_list.next_page_request

    def parse_result_list(self, page, **extras_unused):
        return CatalogResultList(
            page=page,
            items=tuple(self.husk_result_items(page)),
            expected_total_items=self.husk_expected_total_items(page),
            next_page_request=self.husk_next_page_request(page),
        )

    def husk_result_items(self, page):
        try:
            list_el = page(self.result_list_path)
        except HuskerMismatch:
            apology = self.husk_no_results_apology(page)
            if apology:
                logging.info(str(apology))
                return []
            else:
                raise
        else:
            return list_el.all(self.result_item_path)

    def husk_expected_total_items(self, page):
        if self.expected_total_items_path is not None:
            return page(self.expected_total_items_path).text(r'(\d+)').int

    def husk_next_page_request(self, page):
        return page.link(
            page.selection(self.next_page_request_path).dedup().some()
        )

    def husk_no_results_apology(self, page):
        if self.no_results_apology_path is not None:
            return page.some(self.no_results_apology_path)

    @contextmanager
    def seen_items_counter(self):
        counter = Counter()
        yield counter
        if 'expected_total_items' in counter \
                and counter['seen_items'] < 0.9*counter['expected_total_items']:
            raise FewerItemsThanExpected("Expected %d results, found %d" % (
                page.extras['expected_total_items'],
                seen_items,
            ))

    def scrape_item(self, page, item, **extras):
        # Override this to e.g. raise SkipThisPage before fetching it
        return self.scrape(
            page.link(self.husk_item_request(item)),
            self.parse_catalog_item,
            item=item,
            **extras
        )

    def husk_item_request(self, item):
        return item.all(item_request_path).dedup().one()

#----------------------------------------------------------------------------------------------------------------------------------
