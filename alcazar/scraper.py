#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from datetime import timedelta

# alcazar
from .cleaner import Cleaner
from .fetcher import Fetcher

#----------------------------------------------------------------------------------------------------------------------------------

class Scraper(Cleaner, Fetcher):

    id = None
    cache_id = None

    refresh_interval = timedelta(days=1)

    http_cache_life = timedelta(days=30)
    http_timeout = 30
    http_user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'

    html_encoding = 'UTF-8'
    html_encoding_errors = 'strict'
    html_do_decode_entities = False

    def __init__(self):
        if self.id is None:
            self.id = self.__class__.__name__
        if self.cache_id is None:
            self.cache_id = self.id
        super(Scraper, self).__init__()

    def build(self, cls, iter_values):
        return cls(**{
            key: self.clean(value)
            for key, value in iter_values
        })

    def scrape_all(self):
        raise NotImplementedError

#----------------------------------------------------------------------------------------------------------------------------------
