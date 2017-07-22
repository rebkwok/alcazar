#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

__version__ = '0.1'

# alcazar
from .datastructures import ScraperRequest
from .fetcher import Fetcher
from .http import HttpClient
from .husker import Husker
from .scraper import Scraper
from .searchresults import SearchResultsScraper
from .listdriven import ListDrivenScraper

#----------------------------------------------------------------------------------------------------------------------------------
