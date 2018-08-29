#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

__version__ = '0.1.3'

# alcazar
from .catalogparser import CatalogParser, CatalogResultList
from .crawler import Crawler
from .datastructures import GET, Page, POST, Query, Request
from .exceptions import AlcazarException, HttpError, HttpRedirect, ScraperError, SkipThisPage
from .fetcher import Fetcher
from .http import HttpClient
from .husker import Husker, HuskerError, HuskerMismatch, HuskerMultipleSpecMatch, HuskerNotUnique, husk
from .scraper import Scraper
from .tally import Tally
from .utils import compatibility
from .utils.urls import join_urls

#----------------------------------------------------------------------------------------------------------------------------------
