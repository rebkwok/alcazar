#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# alcazar
from .utils.compatibility import native_string

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


class HttpRedirect(HttpError):
    pass


for _status_code in range(100, 600):
    _superclass = HttpRedirect if 300 <= _status_code < 400 else HttpError
    setattr(
        HttpError,
        native_string('Http%d') % _status_code,
        type(
            native_string('Http%d') % _status_code,
            (_superclass,),
            {native_string('status_code'): _status_code},
        ),
    )


class SkipThisPage(AlcazarException):
    pass

#----------------------------------------------------------------------------------------------------------------------------------
