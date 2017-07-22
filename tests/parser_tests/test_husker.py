#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# alcazar
from alcazar.husker import ElementHusker, HuskerMismatch, HuskerMultipleSpecMatch, HuskerNotUnique, TextHusker
from alcazar.utils.compatibility import PY2, text_type

# tests
from .plumbing import AlcazarTest, HtmlFixture

#----------------------------------------------------------------------------------------------------------------------------------

class HtmlHuskerTest(HtmlFixture):

    def setUp(self):
        super(HtmlHuskerTest, self).setUp()
        self.husker = ElementHusker(self.html)

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
            self.husker.one('//title').text(),
            'Sinai Peninsula - Wikipedia',
        )

    def test_title_value(self):
        self.assertEqual(
            self.husker.one('//title').text(),
            'Sinai Peninsula - Wikipedia',
        )

    def test_title_text_xpath(self):
        self.assertEqual(
            self.husker.one('//title/text()'),
            'Sinai Peninsula - Wikipedia',
        )

    def test_title_text_xpath_text(self):
        self.assertEqual(
            self.husker.one('//title/text()').text(),
            'Sinai Peninsula - Wikipedia',
        )

    def test_language_names(self):
        language_names = {
            language.get('lang'): language.text()
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
            self.husker.one('//title').text(),
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
        empty = self.husker.one('p#empty').text()
        self.assertEqual(empty, "")
        self.assertTrue(empty)


    def test_find_on_valued_elem(self):
        root = self.husker.one('section#discourse')
        self.assertEqual(
            list(map(text_type, root.find('./p'))),
            ["It begins.", "It runs.", "It ends."],
        )
        self.assertFalse(root.find('./missing'))

    def test_find_on_null_elem(self):
        root = self.husker.any('missing')
        self.assertFalse(root.find('./*'))

    def test_find_on_valued_getted_attrib(self):
        root = self.husker.one('section').get('id')
        self.assertEqual(
            ''.join(map(text_type, root.find(r'[^aeiou]'))),
            'dscrs',
        )

    def test_find_on_null_getted_attrib(self):
        root = self.husker.one('section').get('missing')
        self.assertEqual(
            ''.join(root.find(r'[^aeiou]')),
            '',
        )

    def test_find_on_valued_text(self):
        root = self.husker.one('p#one').text()
        self.assertEqual(
            ''.join(map(text_type, root.find(r'[^aeiou]', flags='i'))),
            't bgns.',
        )

    def test_find_on_null_text(self):
        root = self.husker.some('p#missing').text()
        self.assertEqual(
            ''.join(root.find(r'.')),
            '',
        )

    def test_find_on_list(self):
        root = self.husker.all('p')
        self.assertEqual(
            '+'.join(text_type(p['id']) for p in root.find(lambda p: p['id'].startswith('t'))),
            'two+three',
        )

    def test_find_on_empty_list(self):
        root = self.husker.find('missing')
        self.assertEqual(
            len(root.find('./*')),
            0,
        )


    def test_one_on_valued_elem(self):
        root = self.husker.one('section#discourse')
        self.assertEqual(
            root.one('p#one').text(),
            "It begins.",
        )
        with self.assertRaises(HuskerMismatch):
            root.one('./missing')

    def test_one_on_null_elem(self):
        root = self.husker.any('missing')
        with self.assertRaises(HuskerMismatch):
            root.one('./*')

    def test_one_on_valued_getted_attrib(self):
        root = self.husker.one('section').get('id')
        self.assertEqual(
            root.one(r'^.'),
            'd',
        )

    def test_one_on_null_getted_attrib(self):
        root = self.husker.one('section').get('missing')
        with self.assertRaises(HuskerMismatch):
            root.one(r'.')

    def test_one_on_valued_text(self):
        root = self.husker.one('p#one').text()
        self.assertEqual(
            root.one(r' (\w+)'),
            'begins',
        )

    def test_one_on_null_text(self):
        root = self.husker.some('p#missing').text()
        with self.assertRaises(HuskerMismatch):
            root.one(r'.')

    def test_one_on_list(self):
        root = self.husker.all('p')
        self.assertEqual(
            root.one(lambda p: p['id'] == 'two').text(),
            'It runs.',
        )

    def test_one_without_args_on_list(self):
        root = self.husker.all('p#one')
        self.assertEqual(
            root.one().text(),
            'It begins.',
        )

    def test_one_on_empty_list(self):
        root = self.husker.find('missing')
        with self.assertRaises(HuskerMismatch):
            root.one(lambda p: True)


    def test_some_match(self):
        root = self.husker.some('p#one')
        self.assertEqual(
            root.text(),
            'It begins.',
        )

    def test_some_mismatch(self):
        root = self.husker.some('p#missing')
        self.assertFalse(root)

    def test_some_not_unique(self):
        with self.assertRaises(HuskerNotUnique):
            root = self.husker.some('p')


    def test_first_match(self):
        root = self.husker.first('section p')
        self.assertEqual(
            root.text(),
            'It begins.',
        )

    def test_first_mismatch(self):
        with self.assertRaises(HuskerMismatch):
            self.husker.first('p#missing')


    def test_last_match(self):
        root = self.husker.last('section p')
        self.assertEqual(
            root.text(),
            'It ends.',
        )

    def test_last_mismatch(self):
        with self.assertRaises(HuskerMismatch):
            self.husker.last('p#missing')


    def test_any_match(self):
        root = self.husker.any('p#two')
        self.assertEqual(
            root.text(),
            'It runs.',
        )

    def test_any_not_unique(self):
        root = self.husker.any('section p')
        self.assertEqual(
            root.text(),
            'It begins.',
        )

    def test_any_mismatch(self):
        root = self.husker.any('p#missing')
        self.assertFalse(root)


    def test_all_match_many(self):
        root = self.husker.all('section p')
        self.assertEqual(
            list(map(text_type, root)),
            ["It begins.", "It runs.", "It ends."],
        )

    def test_all_match_one(self):
        root = self.husker.all('section p#two')
        self.assertEqual(
            list(map(text_type, root)),
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
            root.text(),
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
            root.text(),
            'It begins.',
        )

    def test_one_of_list_spec_on_text(self):
        root = self.husker.one('p#one').text()
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
            root.text(),
            'It runs.',
        )

    def test_first_of_many_matches_one_path(self):
        root = self.husker.first_of(
            'p#zero',
            'p.discourse',
            'p#four',
        )
        self.assertEqual(
            root.text(),
            'It begins.',
        )

    def test_first_of_many_paths_match(self):
        root = self.husker.first_of(
            'p#zero',
            'p#one',
            'p#two',
        )
        self.assertEqual(
            root.text(),
            'It begins.',
        )

    def test_first_of_many_paths_match_paths_in_diff_order_from_document(self):
        root = self.husker.first_of(
            'p#zero',
            'p#two',
            'p#one',
        )
        self.assertEqual(
            root.text(),
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
            root.text(),
            'It runs.',
        )

    def test_any_of_many_matches_one_path(self):
        root = self.husker.any_of(
            'p#zero',
            'p.discourse',
            'p#four',
        )
        self.assertEqual(
            root.text(),
            'It begins.',
        )

    def test_any_of_many_paths_match(self):
        root = self.husker.any_of(
            'p#zero',
            'p#one',
            'p#two',
        )
        self.assertEqual(
            root.text(),
            'It begins.',
        )

    def test_any_of_many_paths_match_paths_in_diff_order_from_document(self):
        root = self.husker.any_of(
            'p#zero',
            'p#two',
            'p#one',
        )
        self.assertEqual(
            root.text(),
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
            list(map(text_type, root)),
            ['It begins.', 'It runs.', 'It ends.'],
        )

    def test_all_of_many_matches_per_path(self):
        root = self.husker.all_of(
            'p#one',
            'p.greater-than-one',
        )
        self.assertEqual(
            list(map(text_type, root)),
            ['It begins.', 'It runs.', 'It ends.'],
        )

    def test_all_of_overlapping_matches(self):
        root = self.husker.all_of(
            'p#one',
            'p.discourse',
        )
        self.assertEqual(
            list(map(text_type, root)),
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
            list(map(text_type, root)),
            ['It runs.', 'It begins.', 'It ends.'],
        )

    def test_all_of_mismatch(self):
        with self.assertRaises(HuskerMismatch):
            root = self.husker.all_of(
                'p#four',
                'p#five',
                'p#six',
            )


    def test_text_on_valued_element(self):
        self.assertEqual(
            self.husker.one('tr#first-row').text(),
            'One Uno',
        )

    def test_text_on_null_element(self):
        self.assertFalse(self.husker.some('#missing').text())

    def test_text_on_valued_getted_attrib(self):
        root = self.husker.one('section').get('id')
        self.assertEqual(
            root,
            'discourse',
        )

    def test_text_on_null_getted_attrib(self):
        root = self.husker.one('section').get('missing')
        self.assertFalse(root)

#----------------------------------------------------------------------------------------------------------------------------------

class TextHuskerStringMethodsTest(AlcazarTest):

    def assertTextEqual(self, husker, reference_text):
        self.assertIsInstance(husker, TextHusker)
        self.assertEqual(husker.value, reference_text)
        self.assertEqual(husker, reference_text)

    def assertIntEqual(self, value, reference_value):
        self.assertIsInstance(value, int)
        self.assertEqual(value, reference_value)

    def test_capitalize(self):
        self.assertTextEqual(TextHusker('hello').capitalize(), 'Hello')

    if not PY2:
        def test_casefold(self):
            self.assertTextEqual(TextHusker('HELLO').casefold(), 'hello')

    def test_center(self):
        self.assertTextEqual(TextHusker('hello').center(9), '  hello  ')

    def test_count(self):
        self.assertIntEqual(TextHusker('hello').count('l'), 2)

    def test_endswith(self):
        self.assertTrue(TextHusker('hello').endswith('lo'))

    def test_format(self):
        self.assertTextEqual(TextHusker('hello {}').format('world!'), 'hello world!')

    def test_index(self):
        self.assertIntEqual(TextHusker('hello').index('l'), 2)

    def test_isalnum(self):
        self.assertTrue(TextHusker('h').isalnum())
        self.assertTrue(TextHusker('0').isalnum())
        self.assertFalse(TextHusker(' ').isalnum())

    def test_isalpha(self):
        self.assertTrue(TextHusker('h').isalpha())
        self.assertFalse(TextHusker('0').isalpha())
        self.assertFalse(TextHusker(' ').isalpha())

    def test_isdecimal(self):
        self.assertFalse(TextHusker('h').isdecimal())
        self.assertTrue(TextHusker('0').isdecimal())
        self.assertFalse(TextHusker(' ').isdecimal())

    def test_isdigit(self):
        self.assertFalse(TextHusker('h').isdigit())
        self.assertTrue(TextHusker('0').isdigit())
        self.assertFalse(TextHusker(' ').isdigit())

    if not PY2:
        def test_isidentifier(self):
            self.assertTrue(TextHusker('h').isidentifier())
            self.assertFalse(TextHusker('0').isidentifier())
            self.assertTrue(TextHusker('_').isidentifier())

    def test_islower(self):
        self.assertTrue(TextHusker('hello').islower())
        self.assertFalse(TextHusker('hEllo').islower())

    def test_isnumeric(self):
        self.assertFalse(TextHusker('h').isdigit())
        self.assertTrue(TextHusker('0').isdigit())
        self.assertFalse(TextHusker(' ').isdigit())

    if not PY2:
        def test_isprintable(self):
            self.assertTrue(TextHusker('hello').isprintable())

    def test_isspace(self):
        self.assertTrue(TextHusker(' ').isspace())
        self.assertFalse(TextHusker('_').isspace())

    def test_istitle(self):
        self.assertTrue(TextHusker('Hello World').istitle())

    def test_isupper(self):
        self.assertTrue(TextHusker('HELLO').isupper())
        self.assertFalse(TextHusker('hEllo').isupper())

    def test_join(self):
        self.assertTextEqual(TextHusker('+').join(['a','b','c']), 'a+b+c')

    def test_ljust(self):
        self.assertTextEqual(TextHusker('hello').ljust(10), 'hello     ')

    def test_lower(self):
        self.assertTextEqual(TextHusker('hEllo').lower(), 'hello')

    def test_lstrip(self):
        self.assertTextEqual(TextHusker(' hello').lstrip(), 'hello')

    def test_replace(self):
        self.assertTextEqual(TextHusker('hello').replace('o', '!'), 'hell!')

    # TODO rfind

    def test_rindex(self):
        self.assertIntEqual(TextHusker('hello').rindex('l'), 3)

    def test_rjust(self):
        self.assertTextEqual(TextHusker('hello').rjust(10), '     hello')

    # def test_rsplit(self):
    #     self.assertEqual(TextHusker('hello').rsplit('l'), ['hel', 'o'])

    def test_rstrip(self):
        self.assertTextEqual(TextHusker(' hello ').rstrip(), ' hello')

    # def test_split(self):
    #     self.assertEqual(TextHusker('hello').split(), 'hello')

    # def test_splitlines(self):
    #     self.assertEqual(TextHusker('hello').splitlines(), 'hello')

    def test_startswith(self):
        self.assertTrue(TextHusker('hello').startswith('hell'))

    def test_strip(self):
        self.assertTextEqual(TextHusker(' hello ').strip(), 'hello')

    def test_swapcase(self):
        self.assertTextEqual(TextHusker('hEllo').swapcase(), 'HeLLO')

    def test_title(self):
        self.assertTextEqual(TextHusker('hello world').title(), 'Hello World')

    def test_translate(self):
        self.assertTextEqual(
            TextHusker('hello').translate({ord('h'):'z', ord('l'):'p'}),
            'zeppo',
        )

    def test_upper(self):
        self.assertTextEqual(TextHusker('hello').upper(), 'HELLO')

    def test_zfill(self):
        self.assertTextEqual(TextHusker('hello').zfill(10), '00000hello')

#----------------------------------------------------------------------------------------------------------------------------------
