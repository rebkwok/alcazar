#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import logging

# 3rd parties
from record import Record, dict_of, nullable, seq_of

# alcazar
from .datastructures import ScraperRequest
from .husker import ListHusker
from .stackscraper import Query, StackScraper
from .utils.compatibility import text_type

#----------------------------------------------------------------------------------------------------------------------------------

class CatalogListing(Record):
    entries = ListHusker
    expected_total_entries = nullable(int)
    next_page = nullable(ScraperRequest)

class CatalogEntry(Record):
    id = text_type
    request = ScraperRequest
    extras = nullable(
        dict_of(text_type, object),
        default={},
    )

class FewerEntriesThanExpected(Exception):
    pass

class SkipThisEntry(Exception):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

class CatalogScraper(StackScraper):

    ### subclasses typically need to define these

    payload_type = NotImplemented

    def husk_listing(self, page):
        raise NotImplementedError

    def husk_entry(self, page, entry):
        # NB there's no query stage called 'entry', this is done as part of parsing a catalog listing
        raise NotImplementedError

    def husk_payload(self, page):
        raise NotImplementedError


    ### subclasses typically don't need to override these

    initial_stage = 'listing'

    def parse_listing(self, page):
        listing = self.build(CatalogListing, self.husk_listing(page))
        seen_entries = page.extras.get('seen_entries', 0)
        for entry in listing.entries:
            try:
                yield self.parse_entry(page, entry)
            except SkipThisEntry as reason:
                print(reason)
            seen_entries += 1
        if listing.next_page:
            yield Query(
                'listing',
                listing.next_page,
                extras={
                    'expected_total_entries': listing.expected_total_entries or page.extras.get('expected_total_entries'),
                    'seen_entries': seen_entries,
                },
            )
        elif seen_entries < 0.9*page.extras.get('expected_total_entries', seen_entries):
            raise FewerEntriesThanExpected("Expected %d results, found %d" % (
                page.extras['expected_total_entries'],
                seen_entries,
            ))

    def parse_entry(self, page, entry):
        entry = self.build(CatalogEntry, self.husk_entry(page, entry))
        return Query(
            'payload',
            entry.request,
            entry.extras,
        )

#----------------------------------------------------------------------------------------------------------------------------------
