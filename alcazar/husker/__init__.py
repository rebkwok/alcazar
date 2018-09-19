#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from types import GeneratorType

# alcazar
from ..utils.compatibility import text_type
from .base import Husker, ListHusker, NULL_HUSKER, NullHusker
from .element import ElementHusker
from .exceptions import (
    HuskerError, HuskerAttributeNotFound, HuskerMismatch, HuskerNotUnique, HuskerMultipleSpecMatch, HuskerLookupError,
)
from .jmespath import JmesPathHusker
from .text import TextHusker

#----------------------------------------------------------------------------------------------------------------------------------

def husk(value):
    if isinstance(value, text_type):
        return TextHusker(value)
    elif callable(getattr(value, 'xpath', None)):
        return ElementHusker(value)
    elif isinstance(value, (tuple, list, GeneratorType)):
        return ListHusker(value)
    elif value is None:
        return NULL_HUSKER
    else:
        # NB this includes undecoded bytes
        raise ValueError(repr(value))

#----------------------------------------------------------------------------------------------------------------------------------
