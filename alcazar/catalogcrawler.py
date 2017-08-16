#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# 3rd parties
from record import Record, nullable
import requests

# alcazar
from .crawler import Crawler, Query
from .husker import ListHusker
from .utils.compatibility import text_type

#----------------------------------------------------------------------------------------------------------------------------------

class CatalogResultList(Record):
    items = ListHusker
    expected_total_items = nullable(int)
    next_page = nullable(text_type)

class FewerItemsThanExpected(Exception):
    pass

class SkipThisItem(Exception):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

class CatalogCrawler(Crawler):

    def husk_result_list(self, page):
        raise NotImplementedError

    def husk_result_item(self, page, item):
        raise NotImplementedError

    def husk_payload(self, page):
        raise NotImplementedError

    def start_referer(self):
        return Query(
            request=None,
            methods={
                'parse_method': 'parse_result_list',
            },
            extras={
                'scraper_id': self.id,
            },
        )

    def parse_result_list(self, page, links):
        results = self.build(CatalogResultList, self.husk_result_list(page))
        seen_items = page.extras.get('seen_items', 0)
        for item in results.items:
            try:
                self.parse_result_item(page, links, item)
            except SkipThisItem as reason:
                print(reason)
            seen_items += 1
        if results.next_page:
            links.follow(
                results.next_page,
                expected_total_items=results.expected_total_items or page.extras.get('expected_total_items'),
                seen_items=seen_items,
            )
        elif seen_items < 0.9*page.extras.get('expected_total_items', seen_items):
            raise FewerItemsThanExpected("Expected %d results, found %d" % (
                page.extras['expected_total_items'],
                seen_items,
            ))

    def parse_result_item(self, page, links, item):
        parts = dict(self.husk_result_item(page, item))
        request = parts.pop('request')
        links.follow(
            request,
            process_method=self.process_payload,
            parse_method=self.parse_payload,
            **dict(page.extras, **parts)
        )

    def process_payload(self, query, links):
        # TODO this is where you'd check storage to see whether we have a recent enough payload with the same ID.
        return self.process_default(query, links) # placeholder

    def parse_payload(self, page, links):
        parts = dict(page.extras)
        parts.update(self.husk_payload(page))
        yield self.build(self.payload_type, parts)

#----------------------------------------------------------------------------------------------------------------------------------
