#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# tests
from .plumbing import AlcazarTest, HtmlFixture, with_inline_html

#----------------------------------------------------------------------------------------------------------------------------------

class SelfClosingHtmlTagTest(HtmlFixture, AlcazarTest):

    fixture_file = "self_closing_html_tag.html"
    fixture_encoding = 'us-ascii'

    def test_p_text(self):
        self.assertXPath(
            '//p/text()',
            ['Schokolade'],
        )

#----------------------------------------------------------------------------------------------------------------------------------

class GramotaTest(HtmlFixture, AlcazarTest):
    """
    This HTML file can be tricky because
    * it's in Windows-1251 (declared in the file)
    * it uses an XML declaration at the top
    """

    fixture_file = "gramota.html"
    fixture_encoding = 'Windows-1251'

    def test_title(self):
        self.assertXPath(
            '//title/text()',
            ['ГРАМОТА.РУ – справочно-информационный интернет-портал «Русский язык» | Лента | Новости'],
        )

    def test_site_title(self):
        self.assertXPath(
            '//div[@id="site-title"]/text()',
            ['Справочно-информационный портал ', ' – русский язык для всех'],
        )

#----------------------------------------------------------------------------------------------------------------------------------

class HtmlEntitiesTest(AlcazarTest):

    @with_inline_html(''' <tag value="&quot;"></tag> ''')
    def test_named_quote_in_attribute(self):
        self.assertEqual(
            self.html.xpath('//tag/@value'),
            ['"'],
        )

    @with_inline_html(''' <tag value="&#x22;"></tag> ''')
    def test_hex_quote_in_attribute(self):
        self.assertEqual(
            self.html.xpath('//tag/@value'),
            ['"'],
        )

    @with_inline_html(''' <tag value="&#34;"></tag> ''')
    def test_decimal_quote_in_attribute(self):
        self.assertEqual(
            self.html.xpath('//tag/@value'),
            ['"'],
        )

    @with_inline_html(''' <tag value="&gt;"></tag> ''')
    def test_named_gt_in_attribute(self):
        self.assertEqual(
            self.html.xpath('//tag/@value'),
            ['>'],
        )

    @with_inline_html(''' <tag value="&#x3E;"></tag> ''')
    def test_hex_gt_in_attribute(self):
        self.assertEqual(
            self.html.xpath('//tag/@value'),
            ['>'],
        )

    @with_inline_html(''' <tag value="&#62;"></tag> ''')
    def test_decimal_gt_in_attribute(self):
        self.assertEqual(
            self.html.xpath('//tag/@value'),
            ['>'],
        )

    @with_inline_html(''' <tag>&gt;</tag> ''')
    def test_named_gt_in_text(self):
        self.assertEqual(
            self.html.xpath('//tag/text()'),
            ['>'],
        )

    @with_inline_html(''' <tag>&#x3E;</tag> ''')
    def test_hex_gt_in_text(self):
        self.assertEqual(
            self.html.xpath('//tag/text()'),
            ['>'],
        )

    @with_inline_html(''' <tag>&#62;</tag> ''')
    def test_decimal_gt_in_text(self):
        self.assertEqual(
            self.html.xpath('//tag/text()'),
            ['>'],
        )

    @with_inline_html(''' <tag>&mdash;</tag> ''')
    def test_mdash_name_in_text(self):
        self.assertEqual(
            self.html.xpath('//tag/text()'),
            ['\u2014'],
        )

    @with_inline_html(''' <tag>&#151;</tag> ''')
    def test_mdash_defacto_dec_in_text(self):
        # the point of this test is that browsers use latin-1 tables for low numbers
        self.assertEqual(
            self.html.xpath('//tag/text()'),
            ['\u2014'],
        )

    @with_inline_html(''' <tag>&#0151;</tag> ''')
    def test_mdash_defacto_zero_dec_in_text(self):
        self.assertEqual(
            self.html.xpath('//tag/text()'),
            ['\u2014'],
        )

    @with_inline_html(''' <tag>&#x97;</tag> ''')
    def test_mdash_defacto_hex_in_text(self):
        self.assertEqual(
            self.html.xpath('//tag/text()'),
            ['\u2014'],
        )

    @with_inline_html(''' <tag>&#x0097;</tag> ''')
    def test_mdash_defacto_zero_hex_in_text(self):
        self.assertEqual(
            self.html.xpath('//tag/text()'),
            ['\u2014'],
        )

    @with_inline_html(''' <tag>&eacute;</tag> ''')
    def test_eacute(self):
        self.assertEqual(
            self.html.xpath('//tag/text()'),
            ['\u00E9'],
        )

#----------------------------------------------------------------------------------------------------------------------------------
