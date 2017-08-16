#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# alcazar
from .husker import Husker
from .utils.compatibility import bytes_type, text_type

#----------------------------------------------------------------------------------------------------------------------------------

class Cleaner(object):
    """
    Turns huskers (i.e. the bits of raw data in an input document that contain the information we're after) into the data that we
    want, in the correct type.
    """

    def clean(self, key, expected_type, unclean):
        if unclean:
            for subkey in (key, self._type_name(expected_type)):
                cleaner = getattr(self, 'clean_%s' % subkey, None)
                if callable(cleaner):
                    return cleaner(unclean)
        if issubclass(expected_type, Husker):
            return unclean
        else:
            return unclean.raw()

    @staticmethod
    def _type_name(cls):
        if cls is text_type:
            return 'text'
        elif cls is bytes_type:
            return 'bytes'
        else:
            return cls.__name__

    def clean_text(self, unclean):
        if callable(getattr(unclean, 'text', None)):
            return unclean.text.raw()
        else:
            return text_type(unclean)

    def clean_int(self, unclean):
        return int(self.clean_text(unclean))

    def clean_float(self, unclean):
        return float(self.clean_text(unclean))

    def clean_Decimal(self, unclean):
        return Decimal(self.clean_text(unclean))

#----------------------------------------------------------------------------------------------------------------------------------
