#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=invalid-name, undefined-variable, ungrouped-imports, unused-import

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import re
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
    from urllib import (
        quote as urlquote,
        quote_plus as urlquote_plus,
        urlencode,
    )
    from urlparse import (
        ParseResult as UrlParseResult,
        parse_qsl,
        urljoin,
        urlparse,
    )

    import htmlentitydefs
    def unescape_html(text):
        # Copy-pasted from http://effbot.org/zone/re-sub.htm#unescape-html
        def fixup(m):
            text = m.group(0)
            if text[:2] == "&#":
                # character reference
                try:
                    if text[:3] == "&#x":
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text # leave as is
        return re.sub(r"&#?\w+;", fixup, text)

else:
    text_type = str
    bytes_type = bytes
    string_types = (bytes, str)
    integer_types = (int,)

    import dbm
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import pickle
    from urllib.parse import (
        ParseResult as UrlParseResult,
        parse_qsl,
        quote as urlquote,
        quote_plus as urlquote_plus,
        urlencode,
        urljoin,
        urlparse,
    )

    try:
        from html import unescape as unescape_html
    except ImportError:
        from .html_shim import unescape as unescape_html

native_string = str

#----------------------------------------------------------------------------------------------------------------------------------
