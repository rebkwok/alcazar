#!/usr/bin/env python
# -*- coding: utf-8 -*-

# We have a few methods in here whose exact signature varies from class to class -- pylint: disable=arguments-differ

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# 3rd parties
import jmespath

# alcazar
from ..utils.compatibility import native_string, text_type
from ..utils.jsonutils import lenient_json_loads
from .base import Husker, ListHusker, NULL_HUSKER, ScalarHusker
from .text import TextHusker

#----------------------------------------------------------------------------------------------------------------------------------
# Here we play with JmesPathHusker's internals so that we have a way of distinguishing between lists that JmesPath creates (such as
# projections and filters, e.g. "locations[?state == 'WA']") vs lists that are from the source.
#
# A better way to do this would be to modify the JmesPath implementation itself so that its `Options` class accepts a `list_cls`,
# similar to how it already has a `dict_cls`. Maybe consider a PR.

class ProjectedList(list):

    @classmethod
    def build(cls, value):
        if value is None:
            return None
        assert isinstance(value, list), repr(value)
        return cls(value)


class CustomJmesPathTreeInterpreter(jmespath.visitor.TreeInterpreter):

    def __wrap(method_name): # pylint: disable=no-self-argument
        def visit(self, node, value):
            original_method = getattr(
                super(CustomJmesPathTreeInterpreter, self),
                native_string(method_name),
            )
            original_value = original_method(node, value)
            return ProjectedList.build(original_value)
        visit.__name__ = native_string(method_name)
        return visit

    visit_filter_projection = __wrap('visit_filter_projection')
    visit_slice = __wrap('visit_slice')
    visit_multi_select_list = __wrap('visit_multi_select_list')
    visit_projection = __wrap('visit_projection')
    visit_value_projection = __wrap('visit_value_projection')


class CustomJmesPathFunctions(jmespath.functions.Functions):

    def _type_check_single(self, current, types, function_name):
        if isinstance(current, ProjectedList):
            current = list(current)
        return super(CustomJmesPathFunctions, self) \
            ._type_check_single(current, types, function_name)

    def __wrap(func_name): # pylint: disable=no-self-argument
        original_func = getattr(jmespath.functions.Functions, '_func_%s' % func_name)
        def new_func(self, *args, **kwargs):
            return ProjectedList.build(original_func(self, *args, **kwargs))
        new_func.__name__ = original_func.__name__
        new_func.signature = original_func.signature
        return new_func

    _func_to_array = __wrap('to_array')
    _func_reverse = __wrap('reverse')
    _func_map = __wrap('map')
    _func_sort = __wrap('sort')
    _func_keys = __wrap('keys')
    _func_values = __wrap('values')
    _func_sort_by = __wrap('sort_by')

#----------------------------------------------------------------------------------------------------------------------------------

class JmesPathHusker(Husker):

    visitor = CustomJmesPathTreeInterpreter(jmespath.visitor.Options(
        custom_functions=CustomJmesPathFunctions(),
    ))

    parser = jmespath.parser.Parser()

    def selection(self, path):
        selected = self.visitor.visit(
            self.parser.parse(path).parsed,
            self._value,
        )
        if isinstance(selected, ProjectedList):
            return ListHusker(map(_husk, selected))
        else:
            return _husk([selected])

    def __getitem__(self, item):
        return self.one(item)

#----------------------------------------------------------------------------------------------------------------------------------
# utils

def _husk(value):
    if value is None:
        return NULL_HUSKER
    elif isinstance(value, text_type):
        return TextHusker(value)
    elif isinstance(value, (int, float, bool)):
        return ScalarHusker(value)
    elif isinstance(value, list):
        return ListHusker(map(_husk, value))
    else:
        return JmesPathHusker(value)

#----------------------------------------------------------------------------------------------------------------------------------
# Monkey-patching

Husker.json = lambda self: JmesPathHusker(lenient_json_loads(self.str))

#----------------------------------------------------------------------------------------------------------------------------------
