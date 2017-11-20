#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import re

# alcazar
from .compatibility import UrlParseResult, urljoin, urlparse

#----------------------------------------------------------------------------------------------------------------------------------

def join_urls(base, url):
    url = urlparse(urljoin(base, url))
    url = UrlParseResult(
        url.scheme,
        url.netloc,

        # Leading /../'s in the path are removed, empty paths are replaced by '/'
        re.sub(r'^(?:/\.\.(?![^/]))+', '', url.path) or '/',

        url.params,
        url.query,
        url.fragment,
    )
    return url.geturl()

#----------------------------------------------------------------------------------------------------------------------------------
