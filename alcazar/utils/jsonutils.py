#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import json
import re

#----------------------------------------------------------------------------------------------------------------------------------

JSON_FIXES = (
    ( # First of all, don't touch anything inside double quotes
        r'\" (?:\\.|[^\\\"])* \"',
        lambda s: s,
    ),
    ( # Replace single quotes with double quotes
        r'\' (?:\\.|[^\\\'])* \'',
        lambda s: '"%s"' % re.sub(
            r'(?:\\.|\")',
            lambda m: {
                '"': '\\"',
                "\\'": "'", # for some reason the json parser gets confused by a backslashed ' inside a " string
            }.get(m.group(), m.group()),
            s[1:-1]
        ),
    ),
    ( # Ensure that all hash property names are quoted
        r'(?<=[\{\,]) \s*\w+\s* (?=:)',
        lambda s: json.dumps(s.strip()),
    ),
    ( # [,,1] becomes [null,null,1]
        r'(?<=[\[\,]) (?=,)',
        lambda s: 'null',
    ),
    ( # Remove commas before closing brackets
        r'(?:,\s*)+ (?= \s*[\]\}])',
        lambda s: '',
    ),
)

RE_JSON_FIXES = re.compile(
    r'|'.join('(%s)' % f[0] for f in JSON_FIXES),
    re.X,
)

#----------------------------------------------------------------------------------------------------------------------------------

def lenient_json_loads(json_text):
    """
    Simply calls the standard library's json.loads, but applies a few simple fixes to the JSON code first, because the standard
    json module is stricter than I like it. In particular, this should be able to take a JavaScript Object literal and parse it
    like the JSON it almost is.

    Escape mania! You need to escape this docstring, which contains an a string passed to `parse_json', which contains an
    escaped strings of Javascript.
    >>> len('\\\\')
    1
    >>> lenient_json_loads("{a: 'a\\\\\\\\a'}")
    {'a': 'a\\\\a'}
    """
    json_text = strip_js_comments(json_text)
    json_text = re.sub(
        r'(?:\\[^x]|\\x([0-9a-fA-F]{2}))',
        lambda m: chr(int(m.group(1),16)) if m.group(1) else m.group(),
        json_text
    )
    json_text = RE_JSON_FIXES.sub(
        lambda m: next(
            f[1](g)
            for f,g in zip(JSON_FIXES, m.groups())
            if g is not None
        ),
        json_text
    )
    return json.loads(json_text)


def strip_js_comments(js):
    """
    Takes a string of JavaScript source code and returns the same code, with comments removed. Tries to be careful not to remove
    stuff that looks like comments but is inside a string literal

    >>> strip_js_comments ('var x = 10;')
    'var x = 10;'
    >>> strip_js_comments ('var x = /* 10 */ 20;')
    'var x =  20;'
    >>> strip_js_comments ('var x = 11; //10;')
    'var x = 11; '
    >>> strip_js_comments ('var x = "http//not-a-comment.com/despite-the-double-slash"; // a comment')
    'var x = "http//not-a-comment.com/despite-the-double-slash"; '
    >>> strip_js_comments ('var x = "/* This isnt a comment, it is a string literal */";')
    'var x = "/* This isnt a comment, it is a string literal */";'
    >>> strip_js_comments ('''var x = "A single apostrophe: '"; /* a comment */ var y = "Another apostrophe: '";''')
    'var x = "A single apostrophe: \\'";  var y = "Another apostrophe: \\'";'
    """

    # FIXME we don't do regex literals (couldn't figure out a complete regex for that). Hopefully shouldn't be a problem, because
    # it's hard to imagine how // or /* */ could fit in a regular expression (esp. since JS programmers must be aware of the case
    # where a regex contains */)

    return re.sub(re.compile('(?:%s)' % "|".join((
        r'(\" (?:\\.|[^\\\"])* \")', # matches and captures double-quoted strings
        r'(\' (?:\\.|[^\\\'])* \')', # matches and captures single-quoted strings
        r' // [^\n]*',               # matches (and does not capture) // comments
        r' /\* .*? \*/',             # matches (and does not capture) /* */ comments
    )), re.S|re.X), lambda m: m.group(1) or m.group(2) or '', js)

#----------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    import doctest
    doctest.testmod()

#----------------------------------------------------------------------------------------------------------------------------------
