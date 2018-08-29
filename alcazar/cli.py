#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import logging
from os import path
from sys import argv, stdout

# this library
from alcazar.http.cache import DiskCache

#----------------------------------------------------------------------------------------------------------------------------------

class AlcazarCli(object):

    def request(self, cache_file_path):
        response = self._lookup_response(cache_file_path)
        if response is not None:
            request = response.request
            print("%s %s" % (request.method, request.url))
            for item in sorted(request.headers.items()):
                print("%s: %s" % item)
            print()
            if request.body:
                stdout.write(request.body)

    def response(self, cache_file_path):
        response = self._lookup_response(cache_file_path)
        if response is not None:
            print("HTTP %s" % (response.status_code,))
            for item in sorted(response.headers.items()):
                print("%s: %s" % item)

    def _lookup_response(self, cache_file_path):
        cache = self._load_cache(cache_file_path)
        cache_key = self._cache_key(cache_file_path)
        cache_entry = cache.index.lookup(cache_key, min_timestamp=0)
        if cache_entry is None:
            logging.error("%r not in cache", cache_key)
            return None
        else:
            return cache_entry.response

    @staticmethod
    def _load_cache(cache_file_path):
        cache_root_path = path.dirname(path.dirname(cache_file_path))
        return DiskCache.build(cache_root_path)

    @staticmethod
    def _cache_key(cache_file_path):
        return (
            path.basename(path.dirname(cache_file_path)),
            path.splitext(path.basename(cache_file_path))[0],
        )

#----------------------------------------------------------------------------------------------------------------------------------

def main():
    logging.basicConfig(level='DEBUG')
    cli = AlcazarCli()
    if len(argv) >= 2:
        command_name = argv[1]
        command_args = argv[2:]
        method = getattr(cli, command_name, None)
    else:
        command_name = command_args = method = None
    if method is None:
        print("usage: %s <command> [args...]" % argv[0])
        print("Available commands:")
        for command in sorted(dir(cli)):
            if not command.startswith('_'):
                print("    %s" % command)
        exit(2)
    else:
        method(*command_args)

if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
