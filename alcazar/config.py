#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from collections import namedtuple

# alcazar
from . import __version__

#----------------------------------------------------------------------------------------------------------------------------------

_DEFAULT_VALUES = {
    'auto_raise_for_status': True,
    'auto_raise_for_redirect': False,
    'courtesy_seconds': 5,
    'encoding': None,
    'encoding_errors': 'strict',
    'num_attempts_per_scrape': 5,
    'strip_namespaces': True,
    'timeout': 30,
    'user_agent': 'Alcazar/%s' % __version__,
}

#----------------------------------------------------------------------------------------------------------------------------------

ScraperConfig = namedtuple( # it's a class, pylint: disable=invalid-name
    'ScraperConfig',
    sorted(_DEFAULT_VALUES.keys()),
)

DEFAULT_CONFIG = ScraperConfig(**_DEFAULT_VALUES)

def _from_kwargs(cls, kwargs, defaults=DEFAULT_CONFIG, consume_all_kwargs_for=None):
    config = {
        key: kwargs.pop(key, getattr(defaults, key, fallback))
        for key, fallback in _DEFAULT_VALUES.items()
    }
    if consume_all_kwargs_for and kwargs:
        raise TypeError("Unknown kwargs for %r: %s" % (
            consume_all_kwargs_for,
            ', '.join(sorted(kwargs)),
        ))
    return cls(**config)

ScraperConfig.from_kwargs = classmethod(_from_kwargs)

#----------------------------------------------------------------------------------------------------------------------------------
