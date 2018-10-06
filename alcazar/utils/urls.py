#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import re

# alcazar
from .compatibility import string_types, text_type, UrlParseResult, urljoin, urlparse

#----------------------------------------------------------------------------------------------------------------------------------

def join_urls(base, url):
    if not base:
        return url
    if not url:
        return base
    if not isinstance(url, string_types):
        url = text_type(url)
    url = re.sub(r'#.*', '', url)
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
