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
from .utils.compatibility import bytes_type, native_string

#----------------------------------------------------------------------------------------------------------------------------------

# In this module, an `HttpRequest` is either a URL (as bytes) or a `requests.Request` object

HttpRequest = ABCMeta(
    native_string('HttpRequest'),
    (object,),
    {}
)

HttpRequest.register(bytes_type)
HttpRequest.register(requests.Request)

#----------------------------------------------------------------------------------------------------------------------------------
