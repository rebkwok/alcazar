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

class MiscTests(unittest.TestCase):

    def test_crawler_invokes_parent_init(self):
        class MyClass(object):
            def __init__(self):
                self.wuz_here = True
        class MyCrawler(alcazar.Crawler, MyClass):
            pass
        crawler = MyCrawler()
        self.assertTrue(getattr(crawler, 'wuz_here', False))

    def test_scraper_invokes_parent_init(self):
        class MyClass(object):
            def __init__(self):
                self.wuz_here = True
        class MyScraper(alcazar.Scraper, MyClass):
            pass
        scraper = MyScraper()
        self.assertTrue(getattr(scraper, 'wuz_here', False))

#----------------------------------------------------------------------------------------------------------------------------------
