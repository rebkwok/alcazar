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

    def __init__(self, message=None, reason=None):
        super(AlcazarException, self).__init__(message)
        self.reason = reason # a chain link to a further exception, where applicable

class ScraperError(AlcazarException):
    pass

class HttpError(ScraperError):
    pass

class SkipThisPage(AlcazarException):
    pass

#----------------------------------------------------------------------------------------------------------------------------------
