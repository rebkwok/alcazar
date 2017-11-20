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

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise TypeError("Unknown kwarg: %s" % key)
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

    def __call__(self, *args, **kwarg):
        return self.fetch(*args, **kwarg)

#----------------------------------------------------------------------------------------------------------------------------------
