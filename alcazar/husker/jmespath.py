#!/usr/bin/env python
# -*- coding: utf-8 -*-

# We have a few methods in here whose exact signature varies from class to class -- pylint: disable=arguments-differ

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import json

# 3rd parties
import jmespath

# alcazar
from ..utils.jsonutils import lenient_json_loads
from .base import Husker, ListHusker, NULL_HUSKER
from .exceptions import HuskerError
from .text import TextHusker

#----------------------------------------------------------------------------------------------------------------------------------

class JmesPathHusker(Husker):

    @classmethod
    def _child(cls, value):
        if value is None:
            return NULL_HUSKER
        elif isinstance(value, str):
            return TextHusker(value)
        else:
            return JmesPathHusker(value)

    def selection(self, path):
        selected = jmespath.search(path, self._value)
        if '[' not in path:
            selected = [selected]
        return ListHusker(map(self._child, selected))

    @property
    def text(self):
        text = self._value
        if not isinstance(text, str):
            text = json.dumps(text, sort_keys=True)
        return TextHusker(text)

    @property
    def multiline(self):
        text = self._value
        if not isinstance(text, str):
            text = json.dumps(text, indent=4, sort_keys=True)
        return TextHusker(text)

    @property
    def list(self):
        if not isinstance(self._value, list):
            raise HuskerError("value is a %s, not a list" % self._value.__class__.__name__)
        return ListHusker(map(self._child, self._value))

    def __getitem__(self, item):
        return self.one(item)

#----------------------------------------------------------------------------------------------------------------------------------
# Horrible hacks

Husker.json = lambda self: JmesPathHusker(lenient_json_loads(self.str))

#----------------------------------------------------------------------------------------------------------------------------------
