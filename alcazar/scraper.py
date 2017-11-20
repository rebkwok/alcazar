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

class Scraper(object):

    id = None
    cache_id = None

    def __init__(self, **kwargs):
        self.id = kwargs.pop('id', self.id) or self.__class__.__name__
        self.cache_id = kwargs.pop('cache_id', self.cache_id) or self.id
        self.fetcher = Fetcher(**self._compile_kwargs(kwargs, (
            'max_cache_life',
            'cache_root_path',
            'timeout',
            'user_agent',
        )))
        self.cleaner = Cleaner()

    def fetch(self, *args, **kwargs):
        return self.fetcher.fetch(*args, **kwargs)

    @classmethod
    def _compile_kwargs(cls, init_kwargs, keys):
        """
        This is not especially elegant, but I wanted to be able to:

         * subclass Scraper and set config options as subclass fields
         * alternatively, directly instantiate Scraper, setting config options as Scraper(**config)
         * not have to define every class' config options in one big list
         * not have to define default values more than once

        I tried a few 'clever' implementations, which did reduce typing, but meant you actually had to study the config system in
        order to use it. I ended up concluding this was overkill, and hence this little blemish.
        """
        compiled_kwargs = {}
        missing = object()
        for key in keys:
            value = init_kwargs.pop(key, getattr(cls, key, missing))
            if value is not missing:
                compiled_kwargs[key] = value
        return compiled_kwargs

#----------------------------------------------------------------------------------------------------------------------------------
