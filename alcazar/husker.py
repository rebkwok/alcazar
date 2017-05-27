#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from functools import reduce, wraps
import operator
import re
from types import GeneratorType

# 3rd parties
import lxml.etree as ET
try:
    from lxml.cssselect import CSSSelector
except ImportError:
    CSSSelector = NotImplemented

# alcazar
from .exceptions import ScraperError
from .utils.compatibility import bytes_type, native_string, text_type
from .utils.text import normalize_spaces

#----------------------------------------------------------------------------------------------------------------------------------
# excecptions

class HuskerError(ScraperError):
    pass

class HuskerMismatch(HuskerError):
    pass

class HuskerNotUnique(HuskerError):
    pass

class HuskerMultiplePathMatch(HuskerError):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

class Husker(object):
    """
    A Husker is used to extract from a raw document those bits of data that are of relevance to our scraper. It does not concern
    itself with cleaning or converting that data -- that's for the `Cleaner` to do. A Husker is just about locating the document
    node, or the text substring, that we're looking for.
    """

    def __init__(self, http_response, value):
        self.http_response = http_response
        self.value = value

    def __getattr__(self, name):
        if name == 'url':
            # NB http_response.url is a text object, not bytes
            return self.build(self.http_response.url)
        elif name == 'text':
            return self._text()
        else:
            raise AttributeError(name)

    def build(self, value):
        if isinstance(value, text_type):
            # NB this includes _ElementStringResult objects that lxml returns when your xpath ends in "/text()"
            return TextHusker(self.http_response, value)
        elif callable(getattr(value, 'xpath', None)):
            return ElementHusker(self.http_response, value)
        elif isinstance(value, (tuple, list, GeneratorType)):
            return ListHusker(self.http_response, value)
        elif value is None:
            return ConstantHusker(value)
        else:
            # NB this includes undecoded bytes
            raise ValueError((value, value.__class__))

    def _text(self):
        raise NotImplemented

    def __str__(self):
        return text_type(self._text())

#----------------------------------------------------------------------------------------------------------------------------------

class Selector(object):
    # This could as well be part of `Husker`, it's separated only for readability and an aesthetic separation of concerns

    def _find(self, spec):
        """
        Runs a search for the given spec, and returns the results, as a list.
        """
        raise NotImplementedError

    def options_from_kwargs(**reference):
        # Since we target both Python 2 and 3 we don't have keyword-only arguments, so to lighten up the code a bit, rather than
        # manually parsing **kwargs we use this:
        def make_wrapper(function):
            @wraps(function)
            def wrapper(self, *args, **kwargs):
                options = type(native_string('Options'), (object,), {
                    key: kwargs.pop(key, default)
                    for key, default in reference.items()
                })()
                if kwargs:
                    raise TypeError("Unknown kwargs: %s" % ','.join(sorted(kwargs)))
                return function(self, options, *args)
            return wrapper
        return make_wrapper

    def __call__(self, **fields):
        for key, husker in fields.items():
            if not isinstance(husker, Husker):
                husker = self.one(husker)
            yield key, husker

    @options_from_kwargs(must_match=True, unique=True)
    def one(self, options, spec):
        husked = self._find(spec)
        if len(husked) == 0:
            if options.must_match:
                raise HuskerMismatch('No matches found for %s' % spec)
            else:
                return None
        elif options.unique and len(husked) > 1:
            raise HuskerNotUnique('Expected 1 match for %s, found %d' % (spec, len(husked)))
        else:
            return husked[0]

    @options_from_kwargs(must_match=True)
    def all(self, options, spec):
        husked = self._find(spec)
        if options.must_match and not husked:
            raise HuskerMismatch('No matches found for %s' % spec)
        return husked

    @options_from_kwargs(must_match=True, unique=True, each_unique=True)
    def one_of(self, options, *all_specs):
        match = matching_spec = None
        for spec in all_specs:
            husked = self.one(spec, must_match=False, unique=options.each_unique)
            if husked is not None:
                if matching_spec is None:
                    match, matching_spec = husked, spec
                    if not options.unique:
                        break
                else:
                    raise HuskerMultipleSpecMatch('Both %s and %s matched' % (matching_spec, spec))
        if options.must_match and matching_spec is None:
            raise HuskerMismatch("None of the specified specs matched: %s" % ', '.join('"%s"' % spec for spec in all_specs))
        return match

    @options_from_kwargs(must_match=True, each_must_match=True)
    def all_of(self, options, *all_specs):
        all_husked = list(
            husked
            for spec in all_specs
            for husked in self.all(spec, must_match=options.each_must_match)
        )
        if options.must_match and not all_husked:
            raise HuskerMismatch("None of the specified specs matched: %s" % ', '.join('"%s"' % spec for spec in all_specs))
        return all_husked

#----------------------------------------------------------------------------------------------------------------------------------

class ElementHusker(Husker, Selector):

    def get(self, item, default=None):
        return self.build(self._ensure_decoded(self.value.get(item, default)))

    def _find(self, path):
        is_xpath = '/' in path or path == '.'
        xpath = path if is_xpath else self._css_path_to_xpath(path)
        husked = ET.XPath(
            xpath,
            # you can use regexes in your paths, e.g. '//a[re:test(text(),"reg(?:ular)?","i")]'
            namespaces = {'re':'http://exslt.org/regular-expressions'},
        )(self.value)
        return [
            self.build(self._ensure_decoded(v))
            for v in husked
        ]

    @staticmethod
    def _ensure_decoded(value):
        # lxml returns bytes when the data is ASCII, even when the input was text, which feels wrong but hey
        if isinstance(value, bytes_type):
            value = value.decode('us-ascii')
        return value

    def _text(self):
        return self.build(normalize_spaces(''.join(self.value.itertext())))

    def multiline(self):
        """
        Like `text`, but preserves line breaks (<br>, <p>, etc)
        """
        def visit(node, inside_pre=False):
            if node.tag == 'pre':
                inside_pre = True
            if node.tag == 'br':
                yield "\n"
            elif node.tag in _PARAGRAPH_BREAKING_TAGS:
                yield "\n\n"
            if node.tag not in _NON_TEXT_TAGS and not isinstance(node, ET._Comment):
                if node.text:
                    yield node.text if inside_pre else normalize_spaces(node.text)
                for child in node:
                    for value in visit(child, inside_pre):
                        yield value
            if node.tag in _PARAGRAPH_BREAKING_TAGS:
                yield "\n\n"
            if node.tail:
                yield node.tail if inside_pre else normalize_spaces(node.tail)
        return self.build(re.sub(
            r'\s+',
            lambda m: "\n\n" if "\n\n" in m.group() else "\n" if "\n" in m.group() else " ",
            ''.join(visit(self.value)),
        ))

    @property
    def js(self):
        js = "\n".join(
            re.sub('^\s*<!--', '', re.sub('-->\s*$', '', js_text))
            for js_text in self.value.xpath('.//script/text()')
        )
        js = self._strip_js_comments(js)
        return js

    @staticmethod
    def _strip_js_comments(js):
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

    @staticmethod
    def _css_path_to_xpath(path):
        if CSSSelector is NotImplemented:
            raise NotImplementedError("lxml.cssselect module not found")
        return CSSSelector(path).path

#----------------------------------------------------------------------------------------------------------------------------------

class TextHusker(Husker, Selector):

    def _find(self, regex, flags=''):
        regex = self._compile(regex, flags)
        husked = list(regex.finditer(self.value))
        if regex.groups == 1:
            return self.build(
                self.build(m.group(1))
                for m in husked
            )
        else:
            return self.build(
                self.build(TextHusker(g for g in m.groups()))
                for m in husked
            )

    def sub(self, regex, replacement, flags=''):
        return TextElement(re.sub(
            regex,
            replacement,
            self,
            flags = self._compile_flags(flags),
        ))

    def _text(self):
        return self

    def __str__(self):
        return self.value

    @staticmethod
    def _compile(regex, flags):
        if isinstance(regex, text_type):
            return re.compile(
                regex,
                reduce(
                    operator.or_,
                    (getattr(re, f.upper()) for f in flags),
                    0,
                ),
            )
        elif flags == '':
            return regex
        else:
            raise ValueError((regex, flags))

#----------------------------------------------------------------------------------------------------------------------------------

class ListHusker(Husker, Selector):

    def __init__(self, http_response, value):
        super(ListHusker, self).__init__(
            http_response,
            tuple(value),
        )

    def _map_on_children(operation):
        return lambda self: self.build(
            getattr(child, operation)(*args, **kwargs)
            for child in self.value
        )

    one = _map_on_children('one')
    all = _map_on_children('all')
    text = _map_on_children('text')

    def unique(self):
        all_values = {}
        for child in self.value:
            all_values[child.value] = child
        if len(all_values) != 1:
            raise HuskerError(all_values)
        return next(iter(all_values.values()))

#----------------------------------------------------------------------------------------------------------------------------------

class ConstantHusker(Husker):

    pass

#----------------------------------------------------------------------------------------------------------------------------------
# private constants

_PARAGRAPH_BREAKING_TAGS = frozenset((
    'address', 'applet', 'blockquote', 'body', 'center', 'cite', 'dd', 'div', 'dl', 'dt', 'fieldset', 'form', 'frame', 'frameset',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'head', 'hr', 'iframe', 'li', 'noscript', 'object', 'ol', 'p', 'table', 'tbody', 'td',
    'textarea', 'tfoot', 'th', 'thead', 'title', 'tr', 'ul',
))

_NON_TEXT_TAGS = frozenset((
    'script', 'style',
))

#----------------------------------------------------------------------------------------------------------------------------------
