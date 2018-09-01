#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import unittest

# alcazar
from alcazar import Request

#----------------------------------------------------------------------------------------------------------------------------------

class RequestTests(unittest.TestCase):

    def test_default_method_is_get(self):
        request = Request('http://example.com/')
        self.assertEqual(request.method, 'GET')

    def test_can_set_method_manually(self):
        request = Request('http://example.com/', method='DELETE')
        self.assertEqual(request.method, 'DELETE')

    def test_post_by_default_when_data(self):
        request = Request('http://example.com/', data=b'payload')
        self.assertEqual(request.method, 'POST')

    def test_post_by_default_when_json(self):
        request = Request('http://example.com/', json={'key': 'value'})
        self.assertEqual(request.method, 'POST')

#----------------------------------------------------------------------------------------------------------------------------------
