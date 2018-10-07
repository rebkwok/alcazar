#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from sys import stderr
from time import time

#----------------------------------------------------------------------------------------------------------------------------------

class LogEntry(object):

    all_sections = (
        (
            'cache_key',
            lambda cache_key: '[{}] '.format('/'.join(cache_key)),
        ), (
            'cache_or_courtesy',
            lambda value: '{:^8} '.format('[{}]'.format(value) if value else ''),
        ), (
            'is_redirect',
            lambda is_redirect: '-> ' if is_redirect else '',
        ), (
            'prepared_request',
            lambda prepared_request: (
                prepared_request.url
                + '' if prepared_request.body is None else ' [{} {} bytes]'.format(
                    prepared_request.method,
                    len(prepared_request.body) if callable(getattr(prepared_request.body, '__len__', None)) else '??',
                )
            ),
        ), (
            'elapsed',
            ' [{0:.2f}s]'.format,
        ),
    )

    all_section_keys = frozenset(key for key, _ in all_sections)

    def __init__(self, **parts):
        self.parts = parts

    def __setitem__(self, key, value):
        if key not in self.all_section_keys:
            raise KeyError(repr(key))
        self.parts[key] = value

    def pop(self, key, default):
        if key not in self.all_section_keys:
            raise KeyError(repr(key))
        return self.parts.pop(key, default)

    def clear(self):
        self.parts.clear()

#----------------------------------------------------------------------------------------------------------------------------------

class Logger(object):

    def flush(self, entry, end=''):
        raise NotImplementedError


class NullLogger(Logger):

    def flush(self, entry, end=''):
        entry.clear()


class DefaultLogger(Logger):

    def flush(self, entry, end=''):
        line = []
        for key, format in LogEntry.all_sections:
            value = entry.pop(key, None)
            if value is not None:
                line.append(format(value))
        print("".join(line), end=end, file=stderr)

#----------------------------------------------------------------------------------------------------------------------------------

class LoggingAdapterMixin(object):

    def __init__(self, base_config, **kwargs):
        self.logger = kwargs.pop('logger', DefaultLogger()) or NullLogger()
        super(LoggingAdapterMixin, self).__init__(base_config, **kwargs)

    def send(self, prepared_request, config, log, **kwargs):
        log['prepared_request'] = prepared_request
        self.logger.flush(log)
        time_before = time()
        try:
            return super(LoggingAdapterMixin, self).send(prepared_request, config, **kwargs)
        finally:
            log['elapsed'] = time() - time_before
            self.logger.flush(log, end='\n')

#----------------------------------------------------------------------------------------------------------------------------------
