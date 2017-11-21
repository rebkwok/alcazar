#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from functools import wraps
import logging
from time import sleep
from traceback import format_exc
from types import GeneratorType

#----------------------------------------------------------------------------------------------------------------------------------
# exception classes

class AlcazarException(Exception):

class ScraperError(AlcazarException):
    pass

class SkipThisPage(AlcazarException):
    pass

#----------------------------------------------------------------------------------------------------------------------------------
