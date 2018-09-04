#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import re

# 3rd parties
#
# NB this file should be the only place where we explicitly specify the etree library we use, so that we have a shot at perhaps one
# day swapping them.
#
import lxml.etree as ET

# alcazar
from .utils.compatibility import text_type

#----------------------------------------------------------------------------------------------------------------------------------
# parse HTML

def parse_html_etree(html_string, remove_comments=True):
    """
    Takes a string (not bytes) of HTML and parses it into an ETree document, which it returns. Uses a handful of heuristics to
    ensure that the document is parsed as a browser would parse it.
    """
    if not isinstance(html_string, text_type):
        # We don't handle decoding here
        raise ValueError(repr(html_string))
    html_string = _repair_html_before_parse(html_string)
    return ET.HTML(
        html_string,
        ET.HTMLParser(
            remove_comments=remove_comments,
        ),
    )

def _repair_html_before_parse(html_string):
    html_string = _repair_self_closing_html_tag(html_string)
    html_string = _repair_html_entities_to_mimic_browser_behavior(html_string)
    return html_string

#----------------------------------------------------------------------------------------------------------------------------------
# 2011-12-08 - Standard browsers (e.g. Firefox) render &#151; as &mdash;. This is technically incorrect, but this usage seems well
# entrenched, and high-profile websites rely on it, so a good scraper must follow popular usage lest it misinterpret these
# websites' data.
#
# As per the HTML standards, numerical entities are supposed to use Unicode codepoints. So for instance "&#151;" should render as
# Unicode character 151, "end of guarded area" (whatever that is). The proper numerical entity for the em dash is "&#8212;".
#
# But major browsers depart from the HTML standard, and, presumably for historical reasons, interpret numerical entities between
# 128 and 160 as Windows-1252 codepoints.
#
# This aims to copy that behaviour.

_HTML_ENTITIES_SPECIAL_CASES = {
    source_entity: '&#x%x;' % target_codepoint
    for source_codepoint, target_codepoint in {
        131: 402, 132: 8222, 133: 8230, 134: 8224, 135: 8225, 136: 710, 137: 8240, 138: 352, 139: 8249, 140: 338, 145: 8216,
        146: 8217, 147: 8220, 148: 8221, 149: 8226, 150: 8211, 151: 8212, 152: 732, 153: 8482, 154: 353, 155: 8250, 156: 339,
        159: 376,
    }.items()
    for source_entity in (
        '&#%d;' % source_codepoint,
        '&#%02d;' % source_codepoint,
        '&#%03d;' % source_codepoint,
        '&#%04d;' % source_codepoint,
        '&#x%x;' % source_codepoint,
        '&#x%02x;' % source_codepoint,
        '&#x%03x;' % source_codepoint,
        '&#x%04x;' % source_codepoint,
    )
}

_RE_HTML_ENTITY_SPECIAL_CASES = re.compile(
    r'(?:%s)' % '|'.join(_HTML_ENTITIES_SPECIAL_CASES),
    flags=re.I,
)

def _repair_html_entities_to_mimic_browser_behavior(html_string):
    return _RE_HTML_ENTITY_SPECIAL_CASES.sub(
        lambda match: _HTML_ENTITIES_SPECIAL_CASES[match.group(0).lower()],
        html_string,
    )

#----------------------------------------------------------------------------------------------------------------------------------

def _repair_self_closing_html_tag(html_string):
    """
    If the opening <html> tag is self-closing, lxml sees en empty document, boo.
    """
    return re.sub(
        r'^ ( \s* (?: <![^>]+> \s* )? <html [^>]* ) / (?= > )',
        r'\1',
        html_string,
        flags=re.I|re.X
    )

#----------------------------------------------------------------------------------------------------------------------------------

def strip_xml_namespaces(xml_bytes):
    return re.sub(
        br'(<[\?/]?\s*)(?:[\w\-]+:)?([\w\-\.]+)(?=[>\s/])([^>]*)',
        lambda m1: (
            m1.group(1)
            + m1.group(2)
            + re.sub(
                # noice
                br'(\s+)(?:[\w\-]+:(?=\w))?([\w\-]*)([^\s\'\"]*(?:\"(?:[^\\\"]|\\.)*\"|\'(?:[^\\\']|\\.)*\')?)',
                lambda m2: b'' if m2.group(2) == b'xmlns' else (m2.group(1) + m2.group(2) + m2.group(3)),
                m1.group(3),
            )
        ),
        xml_bytes,
    )

def parse_xml_etree(xml_bytes, strip_namespaces=False):
    if strip_namespaces:
        xml_bytes = strip_xml_namespaces(xml_bytes)
    return ET.XML(xml_bytes)

#----------------------------------------------------------------------------------------------------------------------------------
