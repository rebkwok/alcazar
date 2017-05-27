#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# alcazar
from alcazar.husker import ElementHusker
from alcazar.utils.compatibility import text_type

# tests
from .plumbing import AlcazarTest, HtmlFixture

#----------------------------------------------------------------------------------------------------------------------------------

class HtmlHuskerTest(HtmlFixture):

    def setUp(self):
        super(HtmlHuskerTest, self).setUp()
        self.husker = ElementHusker(None, self.html)

#----------------------------------------------------------------------------------------------------------------------------------

class SinaiPeninsulaTest(HtmlHuskerTest, AlcazarTest):

    fixture_file = "wikipedia_sinai_peninsula.html"
    fixture_encoding = 'UTF-8'

    def test_title(self):
        self.assertEqual(
            text_type(self.husker.one('//title')),
            'Sinai Peninsula - Wikipedia',
        )

    def test_title_text(self):
        self.assertEqual(
            text_type(self.husker.one('//title').text),
            'Sinai Peninsula - Wikipedia',
        )

    def test_title_value(self):
        self.assertEqual(
            self.husker.one('//title').text.value,
            'Sinai Peninsula - Wikipedia',
        )

    def test_title_text_xpath(self):
        self.assertEqual(
            text_type(self.husker.one('//title/text()').text),
            'Sinai Peninsula - Wikipedia',
        )

    def test_title_text_xpath_value(self):
        self.assertEqual(
            self.husker.one('//title/text()').value,
            'Sinai Peninsula - Wikipedia',
        )

    def test_language_names(self):
        language_names = {
            text_type(language.get('lang')): text_type(language.text)
            for language in (
                item.one('a')
                for item in self.husker.one('#p-lang').all('li.interlanguage-link')
            )
        }
        self.assertEqual(language_names['el'], 'Ελληνικά')
        self.assertEqual(language_names['ko'], '한국어')
        self.assertEqual(language_names['ru'], 'Русский')

#----------------------------------------------------------------------------------------------------------------------------------

class SinaiPeninsulaBgTest(HtmlHuskerTest, AlcazarTest):

    fixture_file = "wikipedia_sinai_peninsula_bg.html"
    fixture_encoding = 'UTF-8'

    def test_title(self):
        self.assertEqual(
            text_type(self.husker.one('//title')),
            'Синайски полуостров – Уикипедия',
        )

#----------------------------------------------------------------------------------------------------------------------------------
