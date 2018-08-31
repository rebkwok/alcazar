#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# alcazar
from .datastructures import Request
from .husker import husk
from .utils.compatibility import urlencode

#----------------------------------------------------------------------------------------------------------------------------------

class Form(object):

    CLICK = object()

    def __init__(self, page, husker, encoding=None):
        self.page = page
        self.husker = husker
        self.encoding = encoding

    def compile_fields(self, override={}):
        """
        Parses the HTML form fields, and returns sequence of name/value pairs for the fields in the form.

        `override` specifies fields whose value the caller wishes to change from their default value; it is either a dictionary, or
        a sequence key/value pairs. The order of the fields returned will correspond to the order of appearance in the HTML tree.
        Any overrides not in the tree will be added; if `override` is a sequence of pairs, its order will be preserved.

        If the form contains multiple submit buttons, the caller can specify which button is clicked by passing the button's `name`
        in override, set to `Form.CLICK`.
        """
        override_seq = override.items() if isinstance(override, dict) else tuple(override)
        override_dict = dict(override)
        for node, input_type in self._iter_input_nodes():
            input_name = node.attrib('name').str
            if input_name:
                is_click = have_value = False
                if input_name in override_dict:
                    input_value = override_dict.pop(input_name, None)
                    if input_value is self.CLICK:
                        is_click = True
                    else:
                        have_value = True
                if not have_value:
                    input_value = self._parse_node_value(node, input_type, is_click)
                if input_value is not None:
                    yield input_name, input_value
        for name, value in override_seq:
            if name in override_dict:
                yield name, value

    def compile_request(self, override={}):
        """
        Like `compile_fields`, but the fields are further compiled into a `Request` object. See `compile_fields` for details.
        """
        method = (self.husker.attrib('method').str or 'GET').upper()
        url = self.husker.attrib('action').str or self.page.url
        key_value_pairs = list(self.compile_fields(override))
        # Shouldn't we just pass key/value pairs to Request rather than reimplement compiling?
        body = urlencode(key_value_pairs) if key_value_pairs else None
        headers = {}
        if method in ('GET', 'HEAD'):
            url = url + ('&' if '?' in url else '?') + body
            body = None
            # ... and the URL stays unencoded?
        else:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            if body is not None and self.encoding:
                body = body.encode(self.encoding)
        return Request(
            url,
            method=method,
            data=body,
            headers=headers,
        )

    def _parse_node_value(self, node, input_type, is_click):
        attrib = lambda key, default=None: node.attrib(key, husk(default)).str
        if input_type in ('radio', 'checkbox'):
            input_value = attrib('value', 'on') if attrib('checked') else None
        elif input_type in ('submit', 'image'):
            if is_click:
                input_value = attrib('value') or ''
            else:
                input_value = None
        elif input_type == 'select':
            option = node.any_of(
                './/option[@selected]',
                './/option',
            )
            if option:
                input_value = option.attrib('value').str or ''
            else:
                input_value = None
        elif input_type == 'button':
            # NB if you want to specify which submit button was clicked you have to pass it as an override
            input_value = None
        else:
            # Everything else: "text", "password", "hidden", "search", and any unknown value
            input_value = attrib('value') or ''
        return input_value

    def _iter_input_nodes(self):
        for node in self.husker.descendants():
            if node.tag == 'input':
                yield node, (node.attrib('type').str or 'text').lower()
            elif node.tag == 'select':
                yield node, 'select'

#----------------------------------------------------------------------------------------------------------------------------------
