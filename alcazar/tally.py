#!/usr/bin/env python

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
import logging

# alcazar
from .exceptions import AlcazarException

#----------------------------------------------------------------------------------------------------------------------------------

class FewerItemsThanExpected(AlcazarException):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

class Tally(object):

    def __init__(self, log=logging):
        self.log = log
        self._expected = None
        self._seen = None

    def reset(self):
        self._expected = None
        self._seen = None

    def set_expected(self, expected):
        if self._expected not in (None, expected):
            raise ValueError("%r != %r" % (expected, self._expected))
        if self._expected is None:
            self.log.debug('Expected result count set to %d', expected)
        self._expected = expected

    def increment(self, count=1):
        if self._seen is None:
            self._seen = 0
        self._seen += 1

    def check(self):
        if self._expected is not None:
            if self._seen < self._expected * 0.9:
                raise FewerItemsThanExpected("Expected %d results, found %d" % (
                    self._expected,
                    self._seen,
                ))
            elif self._seen != self._expected:
                self.log.info('Expected %d items, found %d, good enough', self._expected, self._seen)
            else:
                self.log.debug('Expected %d items, found %d, hurray', self._expected, self._seen)
        else:
            self.log.info('Expected count not set (seen=%r), tally check not performed', self._seen)

#----------------------------------------------------------------------------------------------------------------------------------
