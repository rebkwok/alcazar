#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

__version__ = '0.1'

# alcazar
from .catalogcrawler import CatalogCrawler
from .crawler import Crawler
from .fetcher import Fetcher
from .http import HttpClient
from .husker import Husker
from .scraper import Scraper

#----------------------------------------------------------------------------------------------------------------------------------
