#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# alcazar
from .utils.compatibility import bytes_type, text_type

#----------------------------------------------------------------------------------------------------------------------------------

class Cleaner(object):

    def clean(self, key, expected_type, value):
        for subkey in (key, self._type_name(expected_type)):
            if value is not None:
                cleaner = getattr(self, 'clean_%s' % subkey, None)
                if callable(cleaner):
                    value = cleaner(value)
        return value

    @staticmethod
    def _type_name(cls):
        if cls is text_type:
            return 'text'
        elif cls is bytes_type:
            return 'bytes'
        else:
            return cls.__name__

    def clean_text(self, value, encoding='us-ascii'):
        if isinstance(value, bytes_type):
            value = value.decode(encoding)
        return value

    def clean_bytes(self, value, encoding='us-ascii'):
        if isinstance(value, text_type):
            value = value.encode(encoding)
        return value

    def clean_int(self, value):
        return int(self.clean_text(value))

#----------------------------------------------------------------------------------------------------------------------------------
