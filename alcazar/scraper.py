#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from datetime import timedelta
from os import path

# alcazar
from .cleaner import Cleaner
from .fetcher import Fetcher

#----------------------------------------------------------------------------------------------------------------------------------

class Scraper(Cleaner, Fetcher):

    id = None
    cache_id = None

    refresh_interval = timedelta(days=1)

    def __init__(self):
        if self.id is None:
            self.id = self.__class__.__name__
        if self.cache_id is None:
            self.cache_id = self.id
        if self.cache_id and self.http_cache_root_path:
            self.http_cache_root_path = path.join(
                self.http_cache_root_path,
                self.cache_id,
            )
        super(Scraper, self).__init__()

    def scrape_all(self):
        raise NotImplementedError

#----------------------------------------------------------------------------------------------------------------------------------
