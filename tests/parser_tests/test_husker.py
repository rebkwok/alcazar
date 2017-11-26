#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from datetime import datetime

# alcazar
from alcazar.husker import ElementHusker, HuskerMismatch, HuskerMultipleSpecMatch, HuskerNotUnique, TextHusker
from alcazar.utils.compatibility import PY2, text_type

# tests
from .plumbing import AlcazarTest, HtmlFixture

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
            self.husker.one('/html/head/meta/@charset').value,
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
        self.assertEqual(
            ''.join(root.selection(r'[^aeiou]')),
            '',
        )

    def test_selection_on_valued_text(self):
        root = self.husker.one('p#one').text
        self.assertEqual(
            ''.join(map(text_type, root.selection(r'[^aeiou]', flags='i'))),
            't bgns.',
        )

    def test_selection_on_null_text(self):
        root = self.husker.some('p#missing').text
        self.assertEqual(
            ''.join(root.selection(r'.')),
            '',
        )

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
        with self.assertRaises(HuskerMismatch):
            root.one('./*')

    def test_one_on_valued_getted_attrib(self):
        root = self.husker.one('section#discourse').attrib('id')
        self.assertEqual(
            root.one(r'^.'),
            'd',
        )

    def test_one_on_null_getted_attrib(self):
        root = self.husker.one('section#discourse').attrib('missing')
        with self.assertRaises(HuskerMismatch):
            root.one(r'.')

    def test_one_on_valued_text(self):
        root = self.husker.one('p#one').text
        self.assertEqual(
            root.one(r' (\w+)'),
            'begins',
        )

    def test_one_on_null_text(self):
        root = self.husker.some('p#missing').text
        with self.assertRaises(HuskerMismatch):
            root.one(r'.')

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
        self.assertEqual(root, [])
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
        self.assertIsNone(self.husker.some('#missing').json())

    def test_json_on_valued_attribute(self):
        self.assertEqual(self.husker('#json')['value'].json(), [42])

    def test_json_on_null_attribute(self):
        self.assertIsNone(self.husker.one('#one').attrib('missing').json())

    def test_json_on_valued_text(self):
        self.assertEqual(self.husker.one('#json').text.json(), [24])

    def test_json_on_valued_but_empty_text(self):
        with self.assertRaises(ValueError):
            self.husker.one('#empty').json()

    def test_json_on_null_text(self):
        self.assertIsNone(self.husker.some('#missing').text.json())

    def test_json_on_valued_list(self):
        self.assertEqual(self.husker.all('#json').json(), [[24]])

    def test_json_on_empty_list(self):
        self.assertEqual(self.husker.selection('missing').json(), [])


    def test_int_on_valued_element(self):
        self.assertEqual(self.husker('#int').int, 24)

    def test_int_on_null_element(self):
        self.assertIsNone(self.husker.some('#missing').int)

    def test_int_on_valued_attribute(self):
        self.assertEqual(self.husker('#int')['value'].int, 42)

    def test_int_on_null_attribute(self):
        self.assertIsNone(self.husker.one('#one').attrib('missing').int)

    def test_int_on_valued_text(self):
        self.assertEqual(self.husker.one('#int').text.int, 24)

    def test_int_on_valued_but_empty_text(self):
        with self.assertRaises(ValueError):
            self.husker.one('#empty').int

    def test_int_on_null_text(self):
        self.assertIsNone(self.husker.some('#missing').text.int)

    def test_int_on_valued_list(self):
        self.assertEqual(self.husker.all('#int').int, [24])

    def test_int_on_empty_list(self):
        self.assertEqual(self.husker.selection('missing').int, [])


    def test_float_on_valued_element(self):
        self.assertEqual(self.husker('#float').float, 2.4)

    def test_float_on_null_element(self):
        self.assertIsNone(self.husker.some('#missing').float)

    def test_float_on_valued_attribute(self):
        self.assertEqual(self.husker('#float')['value'].float, 4.2)

    def test_float_on_null_attribute(self):
        self.assertIsNone(self.husker.one('#one').attrib('missing').float)

    def test_float_on_valued_text(self):
        self.assertEqual(self.husker.one('#float').text.float, 2.4)

    def test_float_on_valued_but_empty_text(self):
        with self.assertRaises(ValueError):
            self.husker.one('#empty').float

    def test_float_on_null_text(self):
        self.assertIsNone(self.husker.some('#missing').text.float)

    def test_float_on_valued_list(self):
        self.assertEqual(self.husker.all('#float').float, [2.4])

    def test_float_on_empty_list(self):
        self.assertEqual(self.husker.selection('missing').float, [])


    def test_datetime_on_valued_element(self):
        self.assertEqual(self.husker('#datetime').datetime('%b %d %Y'), datetime(1992, 12, 25))

    def test_datetime_on_null_element(self):
        self.assertIsNone(self.husker.some('#missing').datetime('whatever'))

    def test_datetime_on_valued_attribute(self):
        self.assertEqual(self.husker('#datetime')['value'].datetime('%Y-%m-%d'), datetime(1992, 12, 25))

    def test_datetime_on_null_attribute(self):
        self.assertIsNone(self.husker.one('#one').attrib('missing').datetime('whatever'))

    def test_datetime_on_valued_text(self):
        self.assertEqual(self.husker.one('#datetime').datetime('%b %d %Y'), datetime(1992, 12, 25))

    def test_datetime_on_valued_but_empty_text(self):
        self.assertEqual(self.husker('#empty').datetime(''), datetime(1900, 1, 1))

    def test_datetime_on_null_text(self):
        self.assertIsNone(self.husker.some('#missing').text.datetime('whatever'))

    def test_datetime_on_valued_list(self):
        self.assertEqual(
            self.husker.all('#datetime').datetime('%b %d %Y'),
            [datetime(1992, 12, 25)],
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

#----------------------------------------------------------------------------------------------------------------------------------

class TextHuskerTest(AlcazarTest):

    def test_normalized(self):
        text_str = """
            This is my text.
            There are many like it but this one is mine.
        """
        text_husker = TextHusker(text_str)
        self.assertEqual(
            text_husker.value,
            text_str,
        )
        self.assertEqual(
            text_husker.normalized.value,
            "This is my text. There are many like it but this one is mine.",
        )

#----------------------------------------------------------------------------------------------------------------------------------
