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

class Scraper(Fetcher):

    id = None
    cache_id = None

    def __init__(self, **kwargs):
        self.id = kwargs.pop('id', self.id) or self.__class__.__name__
        self.cache_id = kwargs('cache_id', self.cache_id) or self.id
        self.cleaner = Cleaner()
        super(Scraper, self).__init__()

    def __call__(self, *args, **kwarg):
        return self.fetch(*args, **kwarg)

#----------------------------------------------------------------------------------------------------------------------------------
