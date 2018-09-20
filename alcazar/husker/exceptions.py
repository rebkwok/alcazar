#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# alcazar
from ..exceptions import ScraperError

#----------------------------------------------------------------------------------------------------------------------------------

class HuskerError(ScraperError):
    pass

class HuskerAttributeNotFound(HuskerError):
    pass

class HuskerMismatch(HuskerError):
    pass

class HuskerNotUnique(HuskerError):
    pass

class HuskerMultipleSpecMatch(HuskerNotUnique):
    pass

class HuskerLookupError(HuskerError):
    pass

class HuskerValueError(HuskerError):
    pass

#----------------------------------------------------------------------------------------------------------------------------------
