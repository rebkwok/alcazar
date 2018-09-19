#!/usr/bin/env python
# -*- coding: utf-8 -*-

# We have a few methods in here whose exact signature varies from class to class -- pylint: disable=arguments-differ
# Also we access husker._value all over, the name starts with an underscores but that's ok, pylint: disable=protected-access

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from functools import reduce
import operator
import re

# alcazar
from ..utils.compatibility import string_types, text_type
from ..utils.text import normalize_spaces
from .base import Husker, ListHusker, NULL_HUSKER

#----------------------------------------------------------------------------------------------------------------------------------

class TextHusker(Husker):

    def __init__(self, value):
        assert value is not None
        super(TextHusker, self).__init__(value)

    def selection(self, regex, flags=''):
        regex = self._compile(regex, flags)
        selected = regex.finditer(self._value)
        if regex.groups < 2:
            return ListHusker(map(_husk, (
                m.group(regex.groups)
                for m in selected
            )))
        else:
            return ListHusker(
                ListHusker(map(_husk, m.groups()))
                for m in selected
            )

    def sub(self, regex, replacement, flags=''):
        return TextHusker(
            self._compile(regex, flags).sub(
                replacement,
                self._value,
            )
        )

    @property
    def text(self):
        return self

    @property
    def multiline(self):
        return self

    @property
    def normalized(self):
        return TextHusker(normalize_spaces(self._value))

    def lower(self):
        return TextHusker(self._value.lower())

    def upper(self):
        return TextHusker(self._value.upper())

    def repr_spec(self, regex, flags=''):
        return "%s%s" % (
            re.sub(r'^u?[\'\"](.*)[\'\"]$', r'/\1/', regex),
            flags,
        )

    def __add__(self, other):
        return TextHusker(self._value + other._value)

    def __bool__(self):
        return bool(self._value)

    def __str__(self):
        return self._value

    @staticmethod
    def _compile(regex, flags):
        if isinstance(regex, string_types):
            return re.compile(
                regex,
                reduce(
                    operator.or_,
                    (getattr(re, f.upper()) for f in flags),
                    0,
                ),
            )
        elif flags == '':
            return regex
        else:
            raise ValueError((regex, flags))

#----------------------------------------------------------------------------------------------------------------------------------
# utils

def _husk(value):
    if isinstance(value, text_type):
        return TextHusker(value)
    elif value is None:
        return NULL_HUSKER
    else:
        raise ValueError(repr(value))

#----------------------------------------------------------------------------------------------------------------------------------
