#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import unittest

# alcazar
from alcazar import Form, Page, Query, Request, husk
from alcazar.etree_parser import parse_html_etree
from alcazar.utils.urls import join_urls

#----------------------------------------------------------------------------------------------------------------------------------

class TestFormParser(unittest.TestCase):

    base_url = 'http://example.com/test/'

    def _parse_form(self, html_str, **kwargs):
        html = parse_html_etree(html_str)
        husker = husk(html).one('form')
        page = Page(
            query=Query(
                Request(self.base_url),
                methods={},
                extras={}
            ),
            response=None,
            husker=husker,
        )
        return Form(page, husker).compile_request(**kwargs)

    def test_put_method(self):
        request = self._parse_form('''
           <form method="PUT">
              <input name="input">
           </form>
        ''')
        self.assertEqual(request.method, 'PUT')

    def test_default_method(self):
        request = self._parse_form('''
           <form>
              <input name="input">
           </form>
        ''')
        self.assertEqual(request.method, 'GET')

    def test_get_method(self):
        request = self._parse_form('''
           <form method="GET">
              <input name="input" value="value">
           </form>
        ''')
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.url, self.base_url + '?input=value')
        self.assertIsNone(request.data)

    def test_action(self):
        request = self._parse_form('''
           <form action="action">
              <input name="input" value="value">
           </form>
        ''')
        self.assertEqual(
            request.url,
            'action?input=value',
        )

    def test_default_action(self):
        request = self._parse_form('''
           <form>
              <input name="input">
           </form>
        ''')
        self.assertEqual(request.url, self.base_url + '?input=')

    def test_text_value(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" type="text" value="value">
           </form>
        ''')
        self.assertEqual(request.data, 'input=value')

    def test_untyped_value(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" value="value">
           </form>
        ''')
        self.assertEqual(request.data, 'input=value')

    def test_empty_text_value(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" type="text">
           </form>
        ''')
        self.assertEqual(request.data, 'input=')

    def test_password_value(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" type="password" value="value">
           </form>
        ''')
        self.assertEqual(request.data, 'input=value')

    def test_hidden_value(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" type="hidden" value="value">
           </form>
        ''')
        self.assertEqual(request.data, 'input=value')

    def test_radio_value(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" type="radio" value="value" checked="yes">
              <input name="input" type="radio" value="notthis">
           </form>
        ''')
        self.assertEqual(request.data, 'input=value')

    def test_radio_value_none_checked(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" type="radio" value="neitherthis">
              <input name="input" type="radio" value="notthat">
           </form>
        ''')
        self.assertIsNone(request.data)

    def test_radio_default_value(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" type="radio" checked="yes">
              <input name="input" type="radio" value="notthis">
           </form>
        ''')
        self.assertEqual(request.data, 'input=on')

    def test_checkbox_value(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" type="checkbox" value="value" checked="yes">
           </form>
        ''')
        self.assertEqual(request.data, 'input=value')

    def test_checkbox_value_unchecked(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" type="checkbox" value="notthis">
           </form>
        ''')
        self.assertIsNone(request.data)

    def test_checkbox_default_value(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" type="checkbox" checked="yes">
           </form>
        ''')
        self.assertEqual(request.data, 'input=on')

    def test_submit_value_default(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" type="text" value="value">
              <input name="submit" type="submit">
           </form>
        ''')
        self.assertEqual(request.data, 'input=value')

    def test_select(self):
        request = self._parse_form('''
           <form method="POST">
              <select name="selector">
                 <option value="1">
                 <option value="2" selected>
              </select>
           </form>
        ''')
        self.assertEqual(request.data, 'selector=2')

    def test_select_none_preselected(self):
        request = self._parse_form('''
           <form method="POST">
              <select name="selector">
                 <option value="1">
                 <option value="2">
              </select>
           </form>
        ''')
        self.assertEqual(request.data, 'selector=1')

    def test_override_add_fields(self):
        request = self._parse_form(
            '''
            <form method="POST">
              <input name="input" value="value">
            </form>
            ''',
            override={
                'bob': 'uncle',
            },
        )
        self.assertEqual(request.data, 'input=value&bob=uncle')

    def test_override_change_fields(self):
        request = self._parse_form(
            '''
            <form method="POST">
              <input name="input" value="value">
            </form>
            ''',
            override={
                'input': 'othervalue',
                'bob': 'uncle',
            },
        )
        self.assertEqual(request.data, 'input=othervalue&bob=uncle')

    def test_override_add_fields_from_pairs(self):
        request = self._parse_form(
            '''
            <form method="POST">
              <input name="input" value="value">
            </form>
            ''',
            override=[
                ('bob', 'uncle'),
                ('jane', 'aunt'),
            ],
        )
        self.assertEqual(request.data, 'input=value&bob=uncle&jane=aunt')

    def test_override_remove_fields(self):
        request = self._parse_form(
            '''
            <form method="POST">
              <input name="input" value="value">
              <input name="junk" value="junk">
            </form>
            ''',
            override={
                'junk': None,
                'bob': 'uncle',
            },
        )
        self.assertEqual(request.data, 'input=value&bob=uncle')

    def test_override_clicked_input(self):
        request = self._parse_form(
            '''
            <form method="POST">
              <input name="input" type="text" value="value">
              <input name="button" type="submit" value='clicky'>
            </form>
            ''',
            override={'button': Form.CLICK},
        )
        self.assertEqual(request.data, 'input=value&button=clicky')

    def test_clicked_input_no_value(self):
        request = self._parse_form(
            '''
            <form method="POST">
              <input name="input" type="text" value="value">
              <input name="button" type="submit">
            </form>
            ''',
            override={'button': Form.CLICK},
        )
        self.assertEqual(request.data, 'input=value&button=')

    def test_unknown_input_types(self):
        request = self._parse_form('''
           <form method="POST">
              <input name="input" type="youdontknowme" value="value">
           </form>
        ''')
        self.assertEqual(request.data, 'input=value')

#----------------------------------------------------------------------------------------------------------------------------------
