#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from sys import version_info

#----------------------------------------------------------------------------------------------------------------------------------
# globals

PY2 = (version_info[0] == 2)

if PY2:
    text_type = unicode
    bytes_type = str
    string_types = (str, unicode)
    integer_types = (int, long)

    import anydbm as dbm
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    import cPickle as pickle
    from urlparse import urljoin

else:
    text_type = str
    bytes_type = bytes
    string_types = (bytes, str)
    integer_types = (int,)

    import dbm
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import pickle
    from urllib.parse import urljoin

native_string = str

#----------------------------------------------------------------------------------------------------------------------------------
