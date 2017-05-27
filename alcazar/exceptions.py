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

class ScraperError(Exception):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

def retry_upon_scraper_error(function):
    """
    This function decorator should be applied to functions that make one HTTP request and extract everything out of it. If the
    extraction fails at any stage (fetching, HTML parsing, husking, cleaning, building the data structure), the request will be
    resent, and the whole extraction process repeated. This makes the scrapers resilient against transient website hiccups.
    """
    num_retries = 5
    @wraps(function)
    def wrapper(*original_args, **original_kwargs):
        for attempt_i in range(num_retries):
            kwargs = dict(original_kwargs)
            if attempt_i > 0:
                kwargs.update(
                    force_cache_stale = True,
                    courtesy_delay = 0,
                )
            try:
                payload = function(*original_args, **kwargs)
                if isinstance(payload, GeneratorType):
                    # consume the generator here so that we can catch any exceptions it might raise
                    payload = tuple(payload)
                return payload
            except ScraperError as error:
                if attempt_i+1 < num_retries:
                    delay = 5 ** attempt_i
                    logging.warning(format_exc())
                    logging.warning("sleeping %d sec%s", delay, '' if delay == 1 else 's')
                    sleep(delay)
                else:
                    raise
    return wrapper

#----------------------------------------------------------------------------------------------------------------------------------
