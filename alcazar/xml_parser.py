#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import re

#----------------------------------------------------------------------------------------------------------------------------------

_RE_XML_DECLARATION = re.compile(
    br' ^\s* <\s*\? [^>]+ \?\s*> \s* ',
    re.X,
)

#----------------------------------------------------------------------------------------------------------------------------------

def strip_xml_declaration(xml_bytes):
    return _RE_XML_DECLARATION.sub(b'', xml_bytes)

def strip_xml_namespaces(xml_bytes):
    def handle_tag(match):
        group = match.groupdict()
        return (
            group['bracket']
            + group['tag_name']
            + re.sub(
                br'''
                    (?P<space>      \s+ )
                    (?P<namespace>  [\w\-]+: (?=\w) )?
                    (?P<attr_name>  [\w\-]* )
                    (?P<attr_value> [^\s\'\"]* (?: \"(?:[^\\\"]|\\.)*\"
                                                 | \'(?:[^\\\']|\\.)*\' )? )
                ''',
                handle_tag_attributes,
                group['tag_attr'],
                flags=re.X,
            )
        )
    def handle_tag_attributes(match):
        group = match.groupdict()
        if group['namespace'] == b'xmlns:' or (not group['namespace'] and group['attr_name'] == b'xmlns'):
            return b''
        else:
            return group['space'] + group['attr_name'] + group['attr_value']
    return re.sub(
        br'''
            (?P<bracket>   < [\?/]? \s* )
            (?P<namespace> [\w\-]+ : )?
            (?P<tag_name>  [\w\-\.]+ ) (?=[>\s/])
            (?P<tag_attr>  [^>]*)
        ''',
        handle_tag,
        xml_bytes,
        flags=re.X
    )

#----------------------------------------------------------------------------------------------------------------------------------
