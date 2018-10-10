#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from collections import namedtuple

# alcazar
from .version import alcazar_version

#----------------------------------------------------------------------------------------------------------------------------------

_DEFAULT_VALUES = {
    'allow_redirects': True,
    'auto_raise_for_redirect': False,
    'auto_raise_for_status': True,
    'cache_key': None,
    'cache_key_salt': None,
    'courtesy_seconds': 5,
    'encoding': None,
    'encoding_errors': 'strict',
    'force_cache_stale': False,
    'max_cache_life': None,
    'num_attempts_per_scrape': 5,
    'ssl_verification': True,
    'stream': False,
    'strip_namespaces': True,
    'timeout': 30,
    'use_cache': True,
    'user_agent': 'Alcazar/%s' % alcazar_version,
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
