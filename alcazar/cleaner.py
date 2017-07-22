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
    """
    Turns huskers (i.e. the bits of raw data in an input document that contain the information we're after) into the data that we
    want, in the correct type.
    """

    def clean(self, key, expected_type, husker):
        if husker:
            for subkey in (key, self._type_name(expected_type)):
                cleaner = getattr(self, 'clean_%s' % subkey, None)
                if callable(cleaner):
                    return cleaner(husker)
        return husker.raw()

    @staticmethod
    def _type_name(cls):
        if cls is text_type:
            return 'text'
        elif cls is bytes_type:
            return 'bytes'
        else:
            return cls.__name__

    def clean_text(self, husker, multiline=False):
        return husker.text(multiline=multiline).raw()

    def clean_bytes(self, husker):
        return self.clean_text(husker).encode('UTF-8')

    def clean_int(self, husker):
        return int(self.clean_text(husker))

    def clean_float(self, husker):
        return float(self.clean_text(husker))

    def clean_Decimal(self, husker):
        return Decimal(self.clean_text(husker))

#----------------------------------------------------------------------------------------------------------------------------------
