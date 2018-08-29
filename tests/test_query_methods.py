#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import unittest

# alcazar
import alcazar

#----------------------------------------------------------------------------------------------------------------------------------

class NonFetcherScraper(alcazar.Scraper):

    def fetch(self, request, **kwargs):
        return {
            'url': request.url,
            'kwargs': kwargs,
        }

#----------------------------------------------------------------------------------------------------------------------------------

class TestQueryMethods(unittest.TestCase):

    def test_basics(self):
        scraper = NonFetcherScraper()
        result = scraper.scrape('123')
        self.assertEqual(
            result,
            {'url': '123', 'kwargs': {'attempt_i': 0}},
        )

    def test_fetch_kwargs(self):
        scraper = NonFetcherScraper()
        result = scraper.scrape('234', fetcher_kwargs={'x': 'y'})
        self.assertEqual(
            result,
            {'url': '234', 'kwargs': {'attempt_i': 0, 'x': 'y'}},
        )

#----------------------------------------------------------------------------------------------------------------------------------
