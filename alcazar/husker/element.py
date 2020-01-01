#!/usr/bin/env python
# -*- coding: utf-8 -*-

# We have a few methods in here whose exact signature varies from class to class -- pylint: disable=arguments-differ

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import re

# 3rd parties
import lxml.etree as ET
try:
    import cssselect
    from lxml.cssselect import CSSSelector # pylint: disable=ungrouped-imports
except ImportError:
    CSSSelector = NotImplemented # pylint: disable=invalid-name

# alcazar
from ..forms import Form
from ..utils.compatibility import bytes_type, text_type, unescape_html
from ..utils.etree import detach_node, extract_multiline_text, extract_single_line_text
from ..utils.jsonutils import strip_js_comments
from .base import Husker, ListHusker, NULL_HUSKER, TextHusker
from .exceptions import HuskerAttributeNotFound

#----------------------------------------------------------------------------------------------------------------------------------
# globals

_unspecified = object() # pylint: disable=invalid-name

#----------------------------------------------------------------------------------------------------------------------------------

class ElementHusker(Husker):

    def __init__(self, value, is_full_document=False):
        assert value is not None
        super(ElementHusker, self).__init__(value)
        self.is_full_document = is_full_document

    def __iter__(self):
        for child in self._value:
            yield ElementHusker(child)

    def __len__(self):
        return len(self._value)

    def __getitem__(self, item):
        value = self._value.attrib.get(item, _unspecified)
        if value is _unspecified:
            raise HuskerAttributeNotFound(repr(item))
        return TextHusker(unescape_html(self._ensure_decoded(value)))

    def attrib(self, item, default=NULL_HUSKER):
        value = self._value.attrib.get(item, _unspecified)
        if value is _unspecified:
            return default
        return TextHusker(unescape_html(self._ensure_decoded(value)))

    @property
    def children(self):
        return ListHusker(map(ElementHusker, self._value))

    def child(self, index):
        return ElementHusker(self._value[index])

    def descendants(self):
        for descendant in self._value.iter():
            yield ElementHusker(descendant)

    def selection(self, path):
        xpath = self._compile_xpath(path)
        selected = ET.XPath(
            xpath,
            # you can use regexes in your paths, e.g. '//a[re:test(text(),"reg(?:ular)?","i")]'
            namespaces={'re':'http://exslt.org/regular-expressions'},
        )(self._value)
        return ListHusker(
            _husk(self._ensure_decoded(v))
            for v in selected
        )

    def _compile_xpath(self, path):
        if re.search(r'(?:^\.(?=/)|/|@|^\w+$)', path):
            return re.sub(
                r'^(\.?)(/{,2})',
                lambda m: '%s%s' % (
                    m.group(1) if self.is_full_document else '.',
                    m.group(2) or '//',
                ),
                path
            )
        else:
            return self._css_path_to_xpath(path)

    @staticmethod
    def _ensure_decoded(value):
        # lxml returns bytes when the data is ASCII, even when the input was text, which feels wrong but hey
        if isinstance(value, bytes_type):
            value = value.decode('us-ascii')
        return value

    @property
    def str(self):
        return extract_single_line_text(self._value)

    @property
    def multiline(self):
        return TextHusker(extract_multiline_text(self._value))

    @property
    def head(self):
        return _husk(self._ensure_decoded(self._value.text))

    @property
    def tail(self):
        return _husk(self._ensure_decoded(self._value.tail))

    @property
    def next(self):
        return _husk(self._value.getnext())

    @property
    def previous(self):
        return _husk(self._value.getprevious())

    @property
    def parent(self):
        return _husk(self._value.getparent())

    @property
    def tag(self):
        return TextHusker(self._ensure_decoded(self._value.tag))

    def form(self):
        return Form(self)

    def js(self, strip_comments=True):
        js = "\n".join(
            re.sub(r'^\s*<!--', '', re.sub(r'-->\s*$', '', js_text))
            for js_text in self._value.xpath('.//script/text()')
        )
        if strip_comments:
            js = strip_js_comments(js)
        return TextHusker(js)

    def detach(self, reattach_tail=True):
        detach_node(self._value, reattach_tail=reattach_tail)
        return self

    def repr_spec(self, path):
        return "'%s'" % path

    def repr_value(self, max_width=200, max_lines=100, min_trim=10):
        source_text = self.html_source()
        source_text = re.sub(r'(?<=.{%d}).+' % max_width, u'\u2026', source_text)
        lines = source_text.split('\n')
        if len(lines) >= max_lines + min_trim:
            lines = lines[:max_lines//2] \
                + ['', u'    [\u2026 %d lines snipped \u2026]' % (len(lines) - max_lines), ''] \
                + lines[-max_lines//2:]
            source_text = '\n'.join(lines)
        return 'etree:\n\n%s\n%s\n%s\n' % (
            '-' * max_width,
            source_text.strip(),
            '-' * max_width,
        )

    def html_source(self):
        return ET.tostring(
            self._value,
            pretty_print=True,
            method='HTML',
            encoding=text_type,
        )

    @staticmethod
    def _css_path_to_xpath(path):
        if CSSSelector is NotImplemented:
            raise NotImplementedError("lxml.cssselect module not found")
        try:
            return CSSSelector(path).path
        except cssselect.parser.SelectorSyntaxError:
            raise ValueError("%r is not a valid CSS selector" % (path,))

#----------------------------------------------------------------------------------------------------------------------------------
# utils

def _husk(value):
    if isinstance(value, text_type):
        # NB this includes _ElementStringResult objects that lxml returns when your xpath ends in "/text()"
        return TextHusker(value)
    elif callable(getattr(value, 'xpath', None)):
        return ElementHusker(value)
    elif value is None:
        return NULL_HUSKER
    else:
        raise ValueError(repr(value))

#----------------------------------------------------------------------------------------------------------------------------------
