#!/usr/bin/env python

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
from itertools import chain
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
        self.reset()

    def reset(self):
        self._expected = None
        self._count_by_fate = {}
        self._count_by_request_type = {}

    def set_expected(self, expected):
        if self._expected not in (None, expected):
            raise ValueError("%r != %r" % (expected, self._expected))
        if self._expected is None:
            self.log.debug('Expected result count set to %d', expected)
        self._expected = expected

    def record_request_type(self, request_type, count=1):
        self._count_by_request_type[request_type] = self._count_by_request_type.get(request_type, 0) + count

    def record_payload_fate(self, fate, count=1):
        self._count_by_fate[fate] = self._count_by_fate.get(fate, 0) + count

    def check(self):
        self._log_table()
        total_seen = sum(self._count_by_fate.values())
        if self._expected is not None:
            if total_seen < self._expected * 0.9:
                raise FewerItemsThanExpected("Expected %d results, found %d" % (
                    self._expected,
                    total_seen,
                ))
            elif total_seen < self._expected:
                self.log.info('Expected %d items, found %d, good enough', self._expected, total_seen)
            else:
                self.log.debug('Expected %d items, found %d, hurray', self._expected, total_seen)
        else:
            self.log.info('Expected count not set (seen=%r), tally check not performed', total_seen)

    def _log_table(self):
        total = sum(self._count_by_fate.values())
        table = [
            line.split('|')
            for line in chain(
                self._iter_unpadded_table_lines('Request type', self._count_by_request_type),
                self._iter_unpadded_table_lines('Payload fate', self._count_by_fate),
                [
                    '-- Tally --||',
                    'expected | %s |' % self._expected if self._expected is not None else '?',
                    'total | %d | %s' % (
                        total,
                        '%.02f%%' % (100.0 * total / self._expected) if self._expected else '',
                    ),
                    '-||',
                ],
            )
        ]
        widths = [
            max(len(row[i]) for row in table)
            for i in (0, 1, 2)
        ]
        for row in table:
            pad, sep = '-+' if row[0].startswith('-') else ' |'
            self.log.info('    ' + sep.join(
                cell + pad * (width - len(cell))
                for cell, width in zip(row, widths)
            ))

    def _iter_unpadded_table_lines(self, title, counts):
        total = sum(counts.values())
        yield '-- %s --||' % title
        for request_type, count in sorted(counts.items()):
            yield '%s | %-d | %.02f%%' % (
                request_type,
                count,
                100.0 * count / total if total else '-',
            )

#----------------------------------------------------------------------------------------------------------------------------------
