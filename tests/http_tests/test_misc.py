#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from unittest import TestCase

# alcazar
from alcazar import HttpClient

# tests
from .plumbing import FetcherFixture, ClientFixture, compile_test_case_classes

#----------------------------------------------------------------------------------------------------------------------------------

class TestMisc(TestCase):

    def test_http_client_unknown_constructor_kwargs(self):
        with self.assertRaises(TypeError):
            HttpClient(unknown='kwarg')

#----------------------------------------------------------------------------------------------------------------------------------

class TestMiscWithFetcher(object):

    __fixtures__ = [
        FetcherFixture.__subclasses__(),
        [ClientFixture],
    ]

    def test_http_client_unknown_method_kwargs(self):
        with self.assertRaises(TypeError):
            self.fetch(unknown='kwarg')

#----------------------------------------------------------------------------------------------------------------------------------

compile_test_case_classes(globals())

#----------------------------------------------------------------------------------------------------------------------------------
