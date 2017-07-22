#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from abc import ABCMeta

# 3rd parties
import requests

# alcazar
from .utils.compatibility import bytes_type, native_string, text_type

#----------------------------------------------------------------------------------------------------------------------------------

# A `ScraperRequest` is either a URL (as bytes) or a `requests.Request` object

ScraperRequest = ABCMeta(
    native_string('ScraperRequest'),
    (object,),
    {}
)

ScraperRequest.register(bytes_type)
ScraperRequest.register(text_type)
ScraperRequest.register(requests.Request)

#----------------------------------------------------------------------------------------------------------------------------------
