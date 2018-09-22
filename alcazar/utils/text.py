#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import re

#----------------------------------------------------------------------------------------------------------------------------------
# constants

_SPACES = r'\s\uFEFF\u200B\u2028'

RE_SPACES = re.compile(r'[%s]+' % _SPACES, re.UNICODE)

RE_NON_SPACE = re.compile(r'[^%s]' % _SPACES, re.UNICODE)

#----------------------------------------------------------------------------------------------------------------------------------

def normalize_spaces(text, do_strip=True):
    text = RE_SPACES.sub(' ', text)
    if do_strip:
        text = text.strip()
    return text

#----------------------------------------------------------------------------------------------------------------------------------
