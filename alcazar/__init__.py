#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# alcazar
from .bodytext import ArticleParser, parse_article, parse_body_text
from .catalogparser import CatalogParser, CatalogResultList
from .crawler import Crawler
from .datastructures import GET, Page, POST, Query, Request
from .exceptions import AlcazarException, HttpError, HttpRedirect, ScraperError, SkipThisPage
from .fetcher import Fetcher
from .forms import Form
from .http import HttpClient
from .husker import Husker, HuskerError, HuskerMismatch, HuskerMultipleSpecMatch, HuskerNotUnique, husk
from .scraper import Scraper
from .skeleton import Skeleton, SkeletonItem
from .version import alcazar_version
from .tally import Tally
from .utils import compatibility
from .utils.etree import MultiLineTextExtractor, SingleLineTextExtractor, extract_multiline_text, extract_single_line_text
from .utils.urls import join_urls

#----------------------------------------------------------------------------------------------------------------------------------
