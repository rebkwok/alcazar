#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import logging

# third parties
from record import Record, dict_of, nullable, seq_of
import requests

# alcazar
from .datastructures import HttpRequest
from .exceptions import retry_upon_scraper_error
from .husker import Husker
from .scraper import Scraper
from .utils.compatibility import text_type

#----------------------------------------------------------------------------------------------------------------------------------
# data structures

class ItemList(Record):
    starting_point = object
    item_huskers = seq_of(Husker)
    expected_total_items = nullable(int)
    next_page = nullable(HttpRequest)

class Item(Record):
    starting_point = object
    request = HttpRequest
    extra_data = dict_of(text_type, object)

#----------------------------------------------------------------------------------------------------------------------------------
# exceptions

class SkipThisOffer(Exception):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

class ListDrivenScraper(Scraper):

    ### subclasses are expected to override these:

    # This should be set to a sequence of whatever values `starting_point_request` accepts as its `starting_point` parameter. By
    # default this would be HttpRequest objects (so, URLs or request.Request objects)
    #
    starting_points = NotImplemented

    def item_list_parts(self, starting_point, husker):
        """ Returns a sequence of key/value pairs that are cleaned before being passed to the ItemList constructor """
        raise NotImplementedError

    def build_item(self, starting_point, item_husker):
        """ Returns a sequence of key/value pairs that are cleaned before being passed to the Item constructor """
        raise NotImplementedError

    def build_payload(self, item, husker):
        """ Returns one instance of whatever payload this scraper's `scrape_all` is meant to churn out """
        raise NotImplementedError


    ### these may be overriden, but they have defaults

    def cache_key_for_item(self, item):
        return None # let http.py pick the cache key the usual way, based on the offer URL

    def get_starting_points(self):
        """ Override this as a more flexible alternative to just setting `self.starting_points` """
        return self.starting_points

    def starting_point_request(self, starting_point):
        """
        If using a custom type for `starting_point` objects, this should return a URL (as bytes) or a requests.Request object that
        is to be fetched to retrieve the given starting point.
        """
        return starting_point

    def build_item_list(self, starting_point, husker):
        return self.build(ItemList, self.item_list_parts(starting_point, husker))

    def build_item(self, starting_point, item_husker):
        return self.build(Item, self.item_parts(starting_point, husker))


    ### the rest won't need to be overriden in the simple case

    def scrape_all(self):
        for starting_point in self.get_starting_points():
            for item in self.iter_all_items(starting_point):
                try:
                    payload = self.fetch_and_build_payload(starting_point, item)
                except SkipThisOffer as reason:
                    logging.info("  %s -- skipped", reason)
                else:
                    yield payload

    def iter_all_items(self, starting_point):
        request = self.starting_point_request(starting_point)
        seen_total_items = 0
        expected_total_items = None
        while request is not None:
            item_list, page_results = self.fetch_and_build_items(starting_point, request)
            for item in page_results:
                if item is not None:
                    yield item
                seen_total_items += 1
            expected_total_items = item_list.expected_total_items
            request = item_list.next_page
        self.report_total_items(expected_total_items, seen_total_items)

    @retry_upon_scraper_error
    def fetch_and_build_items(self, starting_point, request, **http_kwargs):
        item_list = self.fetch_and_build_item_list(starting_point, request, **http_kwargs)
        page_results = []
        for item_husker in item_list.item_huskers:
            try:
                item = self.build_item(starting_point, item_husker)
            except SkipThisOffer as reason:
                logging.info('  %s -- skipped a search result', reason)
                item = None
            page_results.append(None)
        return item_list, page_results

    def report_total_items(self, expected_total_items, seen_total_items):
        if expected_total_items is None:
            logging.warning(
                "expected_total_items is None, fix the scraper"
                + "or override `report_total_items` to silence this warning"
            )
        elif seen_total_items < 0.9 * expected_total_items:
            logging.error(
                'Expected %d items, found %d',
                expected_total_items,
                seen_total_items,
            )

    def fetch_and_build_item_list(self, starting_point, request, **http_kwargs):
        http_kwargs.setdefault('cache_life', self.refresh_interval)
        return self.build_item_list(
            starting_point,
            self.fetch_html(request, **http_kwargs),
        )

    @retry_upon_scraper_error
    def fetch_and_build_payload(self, item, **http_kwargs):
        http_kwargs.setdefault(
            'cache_key',
            self.cache_key_for_item(item),
        )
        return self.build_payload(
            item,
            self.fetch_html(item.request, **http_kwargs),
        )

#----------------------------------------------------------------------------------------------------------------------------------
