#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import logging

# alcazar
from .datastructures import Request
from .husker import husk
from .utils.compatibility import urlencode
from .utils.urls import join_urls

#----------------------------------------------------------------------------------------------------------------------------------

class Form(object):

    def __init__(self, base_url, husker):
        self.base_url = base_url
        self.husker = husker

    def compile_request(self, clicked_input=None, extra_fields={}, fields_to_remove=()):
        method = self._parse_method()
        url = self._parse_url()
        key_value_pairs = list(self._extract_key_value_pairs(clicked_input, extra_fields, fields_to_remove))
        body = urlencode(key_value_pairs) if key_value_pairs else None
        if method in ('GET', 'HEAD'):
            url = url + ('&' if '?' in url else '?') + body
            body = None
        return Request(
            url,
            method=method,
            data=body,
        )

    def _parse_method(self):
        return (self.husker.attrib('method').str or 'GET').upper()

    def _parse_url(self):
        action_url = self.husker.attrib('action').str
        if action_url:
            if self.base_url:
                return join_urls(self.base_url, action_url)
            else:
                return action_url
        else:
            return self.base_url

    def _extract_key_value_pairs(self, clicked_input, extra_fields, fields_to_remove):
        # Try hard to preserve order
        if isinstance(extra_fields, dict):
            extra_fields_seq = extra_fields.items()
            extra_fields_dict = extra_fields
        else:
            extra_fields_seq = tuple(extra_fields)
            extra_fields_dict = dict(extra_fields)
        fields_to_remove = set(fields_to_remove)
        for node, input_type in self._iter_input_nodes():
            input_name = node.attrib('name')
            if input_name and input_name not in fields_to_remove:
                input_value = self._parse_node_value(node, input_type, input_name, clicked_input)
                if input_value is not None:
                    yield input_name, extra_fields_dict.pop(input_name, input_value)
        for name, value in extra_fields_seq:
            if name in extra_fields_dict:
                yield name, value

    def _parse_node_value(self, node, input_type, input_name, clicked_input):
        attrib = lambda key, default=None: node.attrib(key, husk(default)).str
        if input_type in ('text', 'password', 'hidden'):
            return attrib('value') or ''
        if input_type in ('radio', 'checkbox'):
            return attrib('value', 'on') if attrib('checked') else None
        if input_type in ('submit', 'image'):
            if clicked_input == input_name:
                return attrib('value') or ''
            else:
                return None
        if input_type == 'select':
            option = node.any_of(
                './/option[@selected]',
                './/option',
            )
            if option:
                return option.attrib('value').str or ''
            else:
                return None
        if input_type == 'button':
            return None
        logging.warning("Don't know how to handle form input type %r", input_type)
        return None

    def _iter_input_nodes(self):
        for node in self.husker.descendants():
            if node.tag == 'input':
                yield node, (node.attrib('type').str or 'text').lower()
            elif node.tag == 'select':
                yield node, 'select'

#----------------------------------------------------------------------------------------------------------------------------------
