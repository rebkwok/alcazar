#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from datetime import date, datetime
from decimal import Decimal
import re

# alcazar
from alcazar.husker import ElementHusker, HuskerMismatch, HuskerMultipleSpecMatch, HuskerNotUnique, HuskerValueError
from alcazar.utils.compatibility import PY2, text_type

# tests
from .plumbing import AlcazarTest, HtmlFixture, with_inline_html

#----------------------------------------------------------------------------------------------------------------------------------

class HtmlHuskerTest(HtmlFixture):

    def setUp(self):
        super(HtmlHuskerTest, self).setUp()
        self.husker = ElementHusker(self.html, is_full_document=True)

#----------------------------------------------------------------------------------------------------------------------------------

class SinaiPeninsulaTest(HtmlHuskerTest, AlcazarTest):

    fixture_file = "wikipedia_sinai_peninsula.html"
    fixture_encoding = 'UTF-8'

    # def test_title(self):
    #     self.assertEqual(
    #         text_type(self.husker.one('//title')),
    #         'Sinai Peninsula - Wikipedia',
    #     )

    def test_title_text(self):
        self.assertEqual(
            self.husker.one('//title').text,
            'Sinai Peninsula - Wikipedia',
        )

    def test_title_value(self):
        self.assertEqual(
            self.husker.one('//title').text,
            'Sinai Peninsula - Wikipedia',
        )

    def test_title_text_xpath(self):
        self.assertEqual(
            self.husker.one('//title/text()'),
            'Sinai Peninsula - Wikipedia',
        )

    def test_title_text_xpath_text(self):
        self.assertEqual(
            self.husker.one('//title/text()').text,
            'Sinai Peninsula - Wikipedia',
        )

    def test_language_names(self):
        language_names = {
            language.attrib('lang'): language.str
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
            self.husker.one('//title').text,
            'Синайски полуостров – Уикипедия',
        )

#----------------------------------------------------------------------------------------------------------------------------------

class ComprehensiveTest(HtmlHuskerTest, AlcazarTest):

    fixture_file = 'comprehensive.html'
    fixture_encoding = 'UTF-8'

    def test_title(self):
        self.assertEqual(
            self.husker.one('/html/head/title/text()'),
            'Comprehensive Test',
        )

    def test_charset(self):
        self.assertEqual(
            self.husker.one('/html/head/meta/@charset').raw,
            'UTF-8',
        )

    def test_empty_elementhusker_truthy(self):
        empty = self.husker.one('p#empty')
        self.assertEqual(len(empty), 0)
        self.assertEqual(list(empty), [])
        self.assertTrue(empty)

    def test_empty_texthusker_truthy(self):
        empty = self.husker.one('p#empty').text
        self.assertEqual(empty, "")
        self.assertFalse(empty)

    def test_selection_on_valued_elem(self):
        root = self.husker.one('section#discourse')
        self.assertEqual(
            root.selection('./p').text,
            ["It begins.", "It runs.", "It ends."],
        )
        self.assertFalse(root.selection('./missing'))

    def test_selection_on_null_elem(self):
        root = self.husker.any('missing')
        self.assertFalse(root.selection('./*'))

    def test_selection_on_valued_getted_attrib(self):
        root = self.husker.one('section#discourse').attrib('id')
        self.assertEqual(
            ''.join(map(text_type, root.selection(r'[^aeiou]'))),
            'dscrs',
        )

    def test_selection_on_null_getted_attrib(self):
        root = self.husker.one('section#discourse').attrib('missing')
        self.assertFalse(root.selection(r'[^aeiou]'))

    def test_selection_on_valued_text(self):
        root = self.husker.one('p#one').text
        self.assertEqual(
            ''.join(map(text_type, root.selection(r'[^aeiou]', flags='i'))),
            't bgns.',
        )

    def test_selection_on_null_text(self):
        root = self.husker.some('p#missing').text
        self.assertFalse(root.selection(r'.'))

    def test_selection_on_list(self):
        root = self.husker.all('p')
        self.assertEqual(
            '+'.join(text_type(p.attrib('id')) for p in root.selection(lambda p: p.attrib('id').str.startswith('t'))),
            'two+three',
        )

    def test_selection_on_empty_list(self):
        root = self.husker.selection('missing')
        self.assertEqual(
            len(root.selection('./*')),
            0,
        )


    def test_one_on_valued_elem(self):
        root = self.husker.one('section#discourse')
        self.assertEqual(
            root.one('p#one').text,
            "It begins.",
        )
        with self.assertRaises(HuskerMismatch):
            root.one('./missing')

    def test_one_on_null_elem(self):
        root = self.husker.any('missing')
        self.assertFalse(root.one('./*'))

    def test_one_on_valued_getted_attrib(self):
        root = self.husker.one('section#discourse').attrib('id')
        self.assertEqual(
            root.one(r'^.'),
            'd',
        )

    def test_one_on_null_getted_attrib(self):
        root = self.husker.one('section#discourse').attrib('missing')
        self.assertFalse(root.one(r'.'))

    def test_one_on_valued_text(self):
        root = self.husker.one('p#one').text
        self.assertEqual(
            root.one(r' (\w+)'),
            'begins',
        )

    def test_one_on_null_text(self):
        root = self.husker.some('p#missing').text
        self.assertFalse(root.one(r'.'))

    def test_one_on_list(self):
        root = self.husker.all('p')
        self.assertEqual(
            root.one(lambda p: p.attrib('id') == 'two').text,
            'It runs.',
        )

    def test_one_without_args_on_list(self):
        root = self.husker.all('p#one')
        self.assertEqual(
            root.one().text,
            'It begins.',
        )

    def test_one_on_empty_list(self):
        root = self.husker.selection('missing')
        with self.assertRaises(HuskerMismatch):
            root.one(lambda p: True)


    def test_some_match(self):
        root = self.husker.some('p#one')
        self.assertEqual(
            root.text,
            'It begins.',
        )

    def test_some_mismatch(self):
        root = self.husker.some('p#missing')
        self.assertFalse(root)

    def test_some_not_unique(self):
        with self.assertRaises(HuskerNotUnique):
            root = self.husker.some('p')


    def test_first_match(self):
        root = self.husker.first('section#discourse p')
        self.assertEqual(
            root.text,
            'It begins.',
        )

    def test_first_mismatch(self):
        with self.assertRaises(HuskerMismatch):
            self.husker.first('p#missing')


    def test_last_match(self):
        root = self.husker.last('section#discourse p')
        self.assertEqual(
            root.text,
            'It ends.',
        )

    def test_last_mismatch(self):
        with self.assertRaises(HuskerMismatch):
            self.husker.last('p#missing')


    def test_any_match(self):
        root = self.husker.any('p#two')
        self.assertEqual(
            root.text,
            'It runs.',
        )

    def test_any_not_unique(self):
        root = self.husker.any('section#discourse p')
        self.assertEqual(
            root.text,
            'It begins.',
        )

    def test_any_mismatch(self):
        root = self.husker.any('p#missing')
        self.assertFalse(root)


    def test_all_match_many(self):
        root = self.husker.all('section#discourse p')
        self.assertEqual(
            root.text,
            ["It begins.", "It runs.", "It ends."],
        )

    def test_all_match_one(self):
        root = self.husker.all('section#discourse p#two')
        self.assertEqual(
            root.text,
            ["It runs."],
        )

    def test_all_mismatch(self):
        with self.assertRaises(HuskerMismatch):
            root = self.husker.all('p#missing')


    def test_one_of_single_match(self):
        root = self.husker.one_of(
            'p#zero',
            'p#two',
            'p#four',
        )
        self.assertEqual(
            root.text,
            'It runs.',
        )

    def test_one_of_many_matches_one_path(self):
        with self.assertRaises(HuskerNotUnique):
            root = self.husker.one_of(
                'p#zero',
                'p.discourse',
                'p#four',
            )

    def test_one_of_many_paths_match(self):
        with self.assertRaises(HuskerMultipleSpecMatch):
            root = self.husker.one_of(
                'p#zero',
                'p#one',
                'p#two',
            )

    def test_one_of_mismatch(self):
        with self.assertRaises(HuskerMismatch):
            root = self.husker.one_of(
                'p#four',
                'p#five',
                'p#six',
            )


    def test_one_of_list_spec_on_element(self):
        root = self.husker.one_of(
            ['p#zero'],
            ['p#one'],
        )
        self.assertEqual(
            root.text,
            'It begins.',
        )

    def test_one_of_list_spec_on_text(self):
        root = self.husker.one('p#one').text
        self.assertEqual(
            root.one_of(
                [r'b e g i n s', 'x'],
                [r's t a r t s', 'x'],
            ),
            'begins',
        )


    def test_first_of_single_match(self):
        root = self.husker.first_of(
            'p#zero',
            'p#two',
            'p#four',
        )
        self.assertEqual(
            root.text,
            'It runs.',
        )

    def test_first_of_many_matches_one_path(self):
        root = self.husker.first_of(
            'p#zero',
            'p.discourse',
            'p#four',
        )
        self.assertEqual(
            root.text,
            'It begins.',
        )

    def test_first_of_many_paths_match(self):
        root = self.husker.first_of(
            'p#zero',
            'p#one',
            'p#two',
        )
        self.assertEqual(
            root.text,
            'It begins.',
        )

    def test_first_of_many_paths_match_paths_in_diff_order_from_document(self):
        root = self.husker.first_of(
            'p#zero',
            'p#two',
            'p#one',
        )
        self.assertEqual(
            root.text,
            'It runs.',
        )

    def test_first_of_mismatch(self):
        with self.assertRaises(HuskerMismatch):
            root = self.husker.first_of(
                'p#four',
                'p#five',
                'p#six',
            )


    def test_any_of_single_match(self):
        root = self.husker.any_of(
            'p#zero',
            'p#two',
            'p#four',
        )
        self.assertEqual(
            root.text,
            'It runs.',
        )

    def test_any_of_many_matches_one_path(self):
        root = self.husker.any_of(
            'p#zero',
            'p.discourse',
            'p#four',
        )
        self.assertEqual(
            root.text,
            'It begins.',
        )

    def test_any_of_many_paths_match(self):
        root = self.husker.any_of(
            'p#zero',
            'p#one',
            'p#two',
        )
        self.assertEqual(
            root.text,
            'It begins.',
        )

    def test_any_of_many_paths_match_paths_in_diff_order_from_document(self):
        root = self.husker.any_of(
            'p#zero',
            'p#two',
            'p#one',
        )
        self.assertEqual(
            root.text,
            'It runs.',
        )

    def test_any_of_mismatch(self):
        root = self.husker.any_of(
            'p#four',
            'p#five',
            'p#six',
        )
        self.assertFalse(root)


    def test_all_of_single_match_per_path(self):
        root = self.husker.all_of(
            'p#one',
            'p#two',
            'p#three',
        )
        self.assertEqual(
            root.text,
            ['It begins.', 'It runs.', 'It ends.'],
        )

    def test_all_of_many_matches_per_path(self):
        root = self.husker.all_of(
            'p#one',
            'p.greater-than-one',
        )
        self.assertEqual(
            root.text,
            ['It begins.', 'It runs.', 'It ends.'],
        )

    def test_all_of_overlapping_matches(self):
        root = self.husker.all_of(
            'p#one',
            'p.discourse',
        )
        self.assertEqual(
            root.text,
            ['It begins.', 'It begins.', 'It runs.', 'It ends.'],
        )

    def test_all_of_single_path_matches(self):
        with self.assertRaises(HuskerMismatch):
            root = self.husker.all_of(
                'p#zero',
                'p#two',
            )

    def test_all_of_many_paths_match_paths_in_diff_order_from_document(self):
        root = self.husker.all_of(
            'p#two',
            'p#one',
            'p#three',
        )
        self.assertEqual(
            root.text,
            ['It runs.', 'It begins.', 'It ends.'],
        )

    def test_all_of_mismatch(self):
        with self.assertRaises(HuskerMismatch):
            root = self.husker.all_of(
                'p#four',
                'p#five',
                'p#six',
            )


    def test_selection_of_single_match_per_path(self):
        root = self.husker.selection_of(
            'p#one',
            'p#two',
            'p#three',
        )
        self.assertEqual(
            root.text,
            ['It begins.', 'It runs.', 'It ends.'],
        )

    def test_selection_of_many_matches_per_path(self):
        root = self.husker.selection_of(
            'p#one',
            'p.greater-than-one',
        )
        self.assertEqual(
            root.text,
            ['It begins.', 'It runs.', 'It ends.'],
        )

    def test_selection_of_overlapping_matches(self):
        root = self.husker.selection_of(
            'p#one',
            'p.discourse',
        )
        self.assertEqual(
            root.text,
            ['It begins.', 'It begins.', 'It runs.', 'It ends.'],
        )

    def test_selection_of_single_path_matches(self):
        root = self.husker.selection_of(
            'p#zero',
            'p#two',
        )
        self.assertEqual(
            root.text,
            ['It runs.'],
        )

    def test_selection_of_many_paths_match_paths_in_diff_order_from_document(self):
        root = self.husker.selection_of(
            'p#two',
            'p#one',
            'p#three',
        )
        self.assertEqual(
            root.text,
            ['It runs.', 'It begins.', 'It ends.'],
        )

    def test_selection_of_mismatch(self):
        root = self.husker.selection_of(
            'p#four',
            'p#five',
            'p#six',
        )
        # root is now an empty ListHusker
        self.assertEqual(root, [])
        self.assertEqual(list(root), [])
        self.assertFalse(root)

    def test_selection_of_on_null_husker(self):
        root = self.husker.some('#bogus').selection_of(
            'p#four',
            'p#five',
            'p#six',
        )
        # root is now a NullHusker
        self.assertEqual(list(root), [])
        self.assertFalse(root)


    def test_text_on_valued_element(self):
        self.assertEqual(
            self.husker.one('tr#first-row').text,
            'One Uno',
        )

    def test_text_on_null_element(self):
        self.assertFalse(self.husker.some('#missing').text)

    def test_text_on_valued_getted_attrib(self):
        root = self.husker.one('section#discourse').attrib('id')
        self.assertEqual(
            root,
            'discourse',
        )

    def test_text_on_null_getted_attrib(self):
        root = self.husker.one('section#discourse').attrib('missing')
        self.assertFalse(root)

    def test_text_on_valued_text(self):
        root = self.husker.one('#one').text
        self.assertEqual(root.text, 'It begins.')

    def test_text_on_null_text(self):
        root = self.husker.some('#zone').text
        self.assertFalse(root)

    def test_text_on_valued_list(self):
        root = self.husker.all('#discourse p')
        self.assertEqual(
            root.text,
            ['It begins.', 'It runs.', 'It ends.'],
        )

    def test_text_on_empty_list(self):
        root = self.husker.selection('#zone')
        self.assertEqual(root.text, [])
        self.assertFalse(root.text)
        self.assertFalse(root)


    def test_bool_on_valued_element(self):
        self.assertTrue(self.husker.one('#empty'))

    def test_bool_on_null_element(self):
        self.assertFalse(self.husker.some('#missing'))

    def test_bool_on_valued_attribute(self):
        self.assertTrue(self.husker.one('#one').attrib('class'))

    def test_bool_on_null_attribute(self):
        self.assertFalse(self.husker.one('#one').attrib('missing'))

    def test_bool_on_valued_text(self):
        self.assertTrue(self.husker.one('#one').text)

    def test_bool_on_valued_but_empty_text(self):
        self.assertFalse(self.husker.one('#empty').text)

    def test_bool_on_null_text(self):
        self.assertFalse(self.husker.some('#missing').text)

    def test_bool_on_valued_list(self):
        self.assertTrue(self.husker.all('p'))

    def test_bool_on_empty_list(self):
        self.assertFalse(self.husker.selection('missing'))


    def test_str_on_valued_element(self):
        self.assertEqual(self.husker('#int').str, '24')

    def test_str_on_null_element(self):
        self.assertIsNone(self.husker.some('#missing').str)

    def test_str_on_valued_attribute(self):
        self.assertEqual(self.husker('#int')['value'].str, '42')

    def test_str_on_null_attribute(self):
        self.assertIsNone(self.husker.one('#one').attrib('missing').str)

    def test_str_on_valued_text(self):
        self.assertEqual(self.husker.one('#int').text.str, '24')

    def test_str_on_valued_but_empty_text(self):
        self.assertEqual(self.husker.one('#empty').str, '')

    def test_str_on_null_text(self):
        self.assertIsNone(self.husker.some('#missing').text.str)

    def test_str_on_valued_list(self):
        self.assertEqual(self.husker.all('#int').str, ['24'])

    def test_str_on_empty_list(self):
        self.assertEqual(self.husker.selection('missing').str, [])


    def test_json_on_valued_element(self):
        self.assertEqual(self.husker('#json').json(), [24])

    def test_json_on_null_element(self):
        self.assertFalse(self.husker.some('#missing').json())

    def test_json_on_valued_attribute(self):
        self.assertEqual(self.husker('#json')['value'].json(), [42])

    def test_json_on_null_attribute(self):
        self.assertFalse(self.husker.one('#one').attrib('missing').json())

    def test_json_on_valued_text(self):
        self.assertEqual(self.husker.one('#json').text.json(), [24])

    def test_json_on_valued_but_empty_text(self):
        with self.assertRaises(HuskerValueError):
            self.husker.one('#empty').json()

    def test_json_on_null_text(self):
        self.assertFalse(self.husker.some('#missing').text.json())

    def test_json_on_valued_list(self):
        self.assertEqual(self.husker.all('#json').json(), [[24]])

    def test_json_on_empty_list(self):
        self.assertEqual(self.husker.selection('missing').json(), [])


    def test_int_on_valued_element(self):
        self.assertEqual(self.husker('#int').int, 24)

    def test_int_on_non_int_element(self):
        with self.assertRaises(HuskerValueError):
            self.husker('#date').int

    def test_int_on_null_element(self):
        self.assertIsNone(self.husker.some('#missing').int)

    def test_int_on_valued_attribute(self):
        self.assertEqual(self.husker('#int')['value'].int, 42)

    def test_int_on_null_attribute(self):
        self.assertIsNone(self.husker.one('#one').attrib('missing').int)

    def test_int_on_valued_text(self):
        self.assertEqual(self.husker.one('#int').text.int, 24)

    def test_int_on_valued_but_empty_text(self):
        with self.assertRaises(HuskerValueError):
            self.husker.one('#empty').int

    def test_int_on_null_text(self):
        self.assertIsNone(self.husker.some('#missing').text.int)

    def test_int_on_valued_list(self):
        self.assertEqual(self.husker.all('#int').int, [24])

    def test_int_on_empty_list(self):
        self.assertEqual(self.husker.selection('missing').int, [])


    def test_float_on_valued_element(self):
        self.assertEqual(self.husker('#float').float, 2.4)

    def test_float_on_non_float_element(self):
        with self.assertRaises(HuskerValueError):
            self.husker('#date').float

    def test_float_on_null_element(self):
        self.assertIsNone(self.husker.some('#missing').float)

    def test_float_on_valued_attribute(self):
        self.assertEqual(self.husker('#float')['value'].float, 4.2)

    def test_float_on_null_attribute(self):
        self.assertIsNone(self.husker.one('#one').attrib('missing').float)

    def test_float_on_valued_text(self):
        self.assertEqual(self.husker.one('#float').text.float, 2.4)

    def test_float_on_valued_but_empty_text(self):
        with self.assertRaises(HuskerValueError):
            self.husker.one('#empty').float

    def test_float_on_null_text(self):
        self.assertIsNone(self.husker.some('#missing').text.float)

    def test_float_on_valued_list(self):
        self.assertEqual(self.husker.all('#float').float, [2.4])

    def test_float_on_empty_list(self):
        self.assertEqual(self.husker.selection('missing').float, [])


    def test_decimal_on_valued_element(self):
        self.assertEqual(self.husker('#float').decimal, Decimal('2.4'))

    def test_decimal_on_non_decimal_element(self):
        with self.assertRaises(HuskerValueError):
            self.husker('#date').decimal

    def test_decimal_on_null_element(self):
        self.assertIsNone(self.husker.some('#missing').decimal)

    def test_decimal_on_valued_attribute(self):
        self.assertEqual(self.husker('#float')['value'].decimal, Decimal('4.2'))

    def test_decimal_on_null_attribute(self):
        self.assertIsNone(self.husker.one('#one').attrib('missing').decimal)

    def test_decimal_on_valued_text(self):
        self.assertEqual(self.husker.one('#float').text.decimal, Decimal('2.4'))

    def test_decimal_on_valued_but_empty_text(self):
        with self.assertRaises(HuskerValueError):
            self.husker.one('#empty').decimal

    def test_decimal_on_null_text(self):
        self.assertIsNone(self.husker.some('#missing').text.decimal)

    def test_decimal_on_valued_list(self):
        self.assertEqual(self.husker.all('#float').decimal, [Decimal('2.4')])

    def test_decimal_on_empty_list(self):
        self.assertEqual(self.husker.selection('missing').decimal, [])


    def test_date_on_valued_element(self):
        self.assertEqual(self.husker('#date').date('%b %d %Y'), date(1992, 12, 25))

    def test_date_on_non_date_element(self):
        with self.assertRaises(HuskerValueError):
            self.husker('#int').date('%b %d %Y')

    def test_date_on_null_element(self):
        self.assertIsNone(self.husker.some('#missing').date('whatever'))

    def test_date_on_valued_attribute(self):
        self.assertEqual(self.husker('#date')['value'].date('%Y-%m-%d'), date(1992, 12, 25))

    def test_date_on_valued_attribute_with_default_format(self):
        self.assertEqual(self.husker('#date')['value'].date(), date(1992, 12, 25))

    def test_date_on_null_attribute(self):
        self.assertIsNone(self.husker.one('#one').attrib('missing').date('whatever'))

    def test_date_on_valued_text(self):
        self.assertEqual(self.husker.one('#date').date('%b %d %Y'), date(1992, 12, 25))

    def test_date_on_valued_but_empty_text(self):
        self.assertEqual(self.husker('#empty').date(''), date(1900, 1, 1))

    def test_date_on_null_text(self):
        self.assertIsNone(self.husker.some('#missing').text.date('whatever'))

    def test_date_on_valued_list(self):
        self.assertEqual(
            self.husker.all('#date').date('%b %d %Y'),
            [date(1992, 12, 25)],
        )

    def test_date_on_empty_list(self):
        self.assertEqual(self.husker.selection('missing').date('whatever'), [])


    def test_datetime_on_valued_element(self):
        self.assertEqual(self.husker('#datetime').datetime('%b %d %Y %I:%M %p'), datetime(1992, 12, 25, 10, 55, 0))

    def test_datetime_on_non_datetime_element(self):
        with self.assertRaises(HuskerValueError):
            self.husker('#int').datetime('%b %d %Y %I:%M %p')

    def test_datetime_on_null_element(self):
        self.assertIsNone(self.husker.some('#missing').datetime('whatever'))

    def test_datetime_on_valued_attribute(self):
        self.assertEqual(self.husker('#datetime')['value'].datetime('%Y-%m-%dT%H:%M:%S'), datetime(1992, 12, 25, 10, 55, 0))

    def test_datetime_on_valued_attribute_with_default_format(self):
        self.assertEqual(self.husker('#datetime')['value'].datetime(), datetime(1992, 12, 25, 10, 55, 0))

    def test_datetime_on_null_attribute(self):
        self.assertIsNone(self.husker.one('#one').attrib('missing').datetime('whatever'))

    def test_datetime_on_valued_text(self):
        self.assertEqual(self.husker.one('#datetime').datetime('%b %d %Y %I:%M %p'), datetime(1992, 12, 25, 10, 55, 0))

    def test_datetime_on_valued_but_empty_text(self):
        self.assertEqual(self.husker('#empty').datetime(''), datetime(1900, 1, 1))

    def test_datetime_on_null_text(self):
        self.assertIsNone(self.husker.some('#missing').text.datetime('whatever'))

    def test_datetime_on_valued_list(self):
        self.assertEqual(
            self.husker.all('#datetime').datetime('%b %d %Y %I:%M %p'),
            [datetime(1992, 12, 25, 10, 55, 0)],
        )

    def test_datetime_on_empty_list(self):
        self.assertEqual(self.husker.selection('missing').datetime('whatever'), [])


    def test_element_head_text(self):
        story = self.husker('#story')
        self.assertEqual(
            story.head.normalized.str,
            'It starts like this. Then it gets',
        )

    def test_element_tail_text(self):
        italics = self.husker('#story i')
        self.assertEqual(
            italics.tail.normalized.str,
            'but then it\'s all fine.',
        )


    # def test_iter_on_valued_list(self):
    #     self.assertEqual(
    #         '/'.join(elem.text for elem in self.husker.all

    def test_absolute_xpath_on_root(self):
        self.assertEqual(self.husker.one('/html/head/title/text()'), 'Comprehensive Test')

    def unprefixed_xpath_on_root(self):
        self.assertEqual(self.husker.one('title/text()'), 'Comprehensive Test')

    def test_absolute_xpath_on_internal_node(self):
        node = self.husker.one('section#discourse')
        self.assertEqual(node.one('/p[@id="one"]/@class'), 'discourse')

    def test_double_slash_xpath_on_internal_node(self):
        node = self.husker.one('tr[@id="first-row"]')
        self.assertEqual(node.one('//th/text()'), 'One')

    def test_unprefixed_xpath_on_internal_node(self):
        node = self.husker.one('tr[@id="first-row"]')
        self.assertEqual(node.one('th/text()'), 'One')

    def test_absolute_xpath_cant_break_out_of_subtree(self):
        node = self.husker.one('table')
        self.assertFalse(node.some('//section'))

    def test_css_path_starting_with_dot(self):
        node = self.husker.one('section#discourse')
        self.assertEqual(3, len(node.all('.discourse')))

    def test_element_iter_returns_huskers_too(self):
        node = self.husker.one('section#discourse')
        text = [child.text.str for child in node]
        self.assertEqual(
            text,
            ['It begins.', 'It runs.', 'It ends.'],
        )


    def test_str_equality(self):
        husker = self.husker.one('#one').text # but not .str
        self.assertEqual(husker, 'It begins.')
        self.assertNotEqual(None, husker)
        self.assertNotEqual(husker, None)

    def test_str_equality_when_null(self):
        self.assertEqual(
            self.husker.some('#thiswontmatch').text, # but not .str
            None,
        )

#----------------------------------------------------------------------------------------------------------------------------------

class WhitespaceHandlingTest(HtmlHuskerTest, AlcazarTest):

    fixture_file = "whitespace.html"
    fixture_encoding = 'UTF-8'

    def test_one_singleline(self):
        self.assertEqual(
            self.husker('#one').text,
            "One line, some double spaces, some newlines. Whitespace at the end.",
        )

    def test_one_multiline(self):
        self.assertEqual(
            self.husker('#one').multiline,
            "One line, some double spaces, some newlines. Whitespace at the end.",
        )

    def test_two_singleline(self):
        self.assertEqual(
            self.husker('#two').text,
            "A tag just after a word.",
        )

    def test_two_multiline(self):
        self.assertEqual(
            self.husker('#two').multiline,
            "A tag just after a word.",
        )

    def test_three_singleline(self):
        self.assertEqual(
            self.husker('#three').text,
            "A tag inside white space.",
        )

    def test_three_multiline(self):
        self.assertEqual(
            self.husker('#three').multiline,
            "A tag inside white space.",
        )

    def test_four_singleline(self):
        self.assertEqual(
            self.husker('#four').text,
            "A tagwith no space around it.",
        )

    def test_four_multiline(self):
        self.assertEqual(
            self.husker('#four').multiline,
            "A tagwith no space around it.",
        )

    def test_five_singleline(self):
        self.assertEqual(
            self.husker('#five').text,
            "A br tag with no space.",
        )

    def test_five_multiline(self):
        self.assertEqual(
            self.husker('#five').multiline,
            "A br\ntag with no space.",
        )

    def test_six_singleline(self):
        self.assertEqual(
            self.husker('#six').text,
            "A br tag with a space after.",
        )

    def test_six_multiline(self):
        self.assertEqual(
            self.husker('#six').multiline,
            "A br\ntag with a space after.",
        )

    def test_seven_singleline(self):
        self.assertEqual(
            self.husker('#seven').text,
            "A br tag with a space before.",
        )

    def test_seven_multiline(self):
        self.assertEqual(
            self.husker('#seven').multiline,
            "A br\ntag with a space before.",
        )

    def test_eight_singleline(self):
        self.assertEqual(
            self.husker('#eight').text,
            "Three br tags in a row.",
        )

    def test_eight_multiline(self):
        self.assertEqual(
            self.husker('#eight').multiline,
            "Three br tags\n\nin a row.",
        )

    def test_nine_singleline(self):
        self.assertEqual(
            self.husker('#nine').text,
            "A header, then a paragraph, then a div and then a list item.",
        )

    def test_nine_multiline(self):
        self.assertEqual(
            self.husker('#nine').multiline,
            "A header,\n\n"
            + "then\n\n"
            + "a paragraph,\n\n"
            + "then\n\n"
            + "a div\n\n"
            + "and then\n\n"
            + "a list item."
        )

#----------------------------------------------------------------------------------------------------------------------------------

class InlineScriptsTest(HtmlHuskerTest, AlcazarTest):

    fixture_file = "inline-scripts.html"
    fixture_encoding = 'UTF-8'

    def test_simple_text_with_inline_scripts(self):
        self.assertEqual(
            self.husker('body').text,
            "Start text. "
            + "Tail text. "
            + "More text. "
            + "More tail text. "
            + "Noscript text. "
            + "Noscript tail text. "
            + "Third text. "
            + "Before style text. After style text. "
            + "End text."
        )

    def test_multiline_text_with_inline_scripts(self):
        self.assertEqual(
            self.husker('body').multiline,
            "Start text.\n\n"
            + "Tail text.\n\n"
            + "More text.\n\n"
            + "More tail text.\n\n"
            + "Noscript text.\n\n"
            + "Noscript tail text.\n\n"
            + "Third text.\n\n"
            + "Before style text. After style text.\n\n"
            + "End text."
        )

#----------------------------------------------------------------------------------------------------------------------------------

class PreTagHandlingTest(AlcazarTest):

    @with_inline_html('''
        <p>In a  normal   paragraph   spaces  don't count.</p>
        <p><pre>In a  pre   tag   they  do though.</pre></p>
        <p><p>In a  normal   paragraph   spaces  don't count.</p></p>
    ''')
    def test_named_quote_in_attribute(self):
        husker = ElementHusker(self.html)
        self.assertEqual(
            husker.multiline,
            "In a normal paragraph spaces don't count.\n\n"
            + "In a  pre   tag   they  do though.\n\n"
            + "In a normal paragraph spaces don't count."
        )

    # TODO: tail text on a pre tag is not pre-formatted

#----------------------------------------------------------------------------------------------------------------------------------
