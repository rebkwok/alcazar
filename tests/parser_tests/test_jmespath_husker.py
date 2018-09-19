#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import json
from os import path

# alcazar
from alcazar.husker import HuskerNotUnique, JmesPathHusker, ListHusker, ScalarHusker, TextHusker

# tests
from .plumbing import AlcazarTest

#----------------------------------------------------------------------------------------------------------------------------------

class JmesPathHuskerTest(AlcazarTest):

    def setUp(self):
        with open(path.join(path.dirname(__file__), 'fixtures', 'comprehensive.json'), 'rb') as file_in:
            self.data = json.loads(file_in.read().decode('UTF-8'))
        self.husker = JmesPathHusker(self.data)

#----------------------------------------------------------------------------------------------------------------------------------

class ComprehensiveJmesPathTests(JmesPathHuskerTest):

    def test_simple_string(self):
        self.assertEqual(
            self.husker.one("string"),
            "oon",
        )

    def test_simple_int(self):
        self.assertEqual(
            self.husker.one("int"),
            1,
        )

    def test_simple_boolean(self):
        self.assertFalse(
            self.husker.one("boolean"),
        )

    ### list_of_ints

    def test_list_of_ints(self):
        result = self.husker.one("list_of_ints")
        self.assertIsInstance(result, ListHusker)
        self.assertEqual(result, [1, 2, 3])

    def test_list_of_ints_element(self):
        result = self.husker.one("list_of_ints[0]")
        self.assertIsInstance(result, ScalarHusker)
        self.assertEqual(result, 1)

    def test_list_of_ints_getitem_external(self):
        result = self.husker.one("list_of_ints")[0]
        self.assertIsInstance(result, ScalarHusker)
        self.assertEqual(result, 1)

    def test_list_of_ints_one_star(self):
        with self.assertRaises(HuskerNotUnique):
            self.husker.one("list_of_ints[*]")

    def test_list_of_ints_all_star(self):
        self.assertEqual(
            self.husker.all("list_of_ints[*]"),
            [1, 2, 3]
        )

    ### list_of_strings

    def test_list_of_strings(self):
        result = self.husker.one("list_of_strings")
        self.assertIsInstance(result, ListHusker)
        self.assertEqual(result, ["one", "too", "tree"])

    def test_list_of_strings_element(self):
        result = self.husker.one("list_of_strings[0]")
        self.assertIsInstance(result, TextHusker)
        self.assertEqual(result, "one")

    def test_list_of_strings_getitem_external(self):
        result = self.husker.one("list_of_strings")[0]
        self.assertIsInstance(result, TextHusker)
        self.assertEqual(result, "one")

    def test_list_of_strings_one_star(self):
        with self.assertRaises(HuskerNotUnique):
            self.husker.one("list_of_strings[*]")

    def test_list_of_strings_all_star(self):
        self.assertEqual(
            self.husker.all("list_of_strings[*]"),
            ["one", "too", "tree"]
        )

    ### list_of_bools

    def test_list_of_bools(self):
        result = self.husker.one("list_of_bools")
        self.assertIsInstance(result, ListHusker)
        self.assertEqual(result, [True, False, True])

    def test_list_of_bools_element(self):
        result = self.husker.one("list_of_bools[1]")
        self.assertIsInstance(result, ScalarHusker)
        self.assertFalse(result)

    def test_list_of_bools_getitem_external(self):
        result = self.husker.one("list_of_bools")[1]
        self.assertIsInstance(result, ScalarHusker)
        self.assertFalse(result)

    def test_list_of_bools_one_star(self):
        with self.assertRaises(HuskerNotUnique):
            self.husker.one("list_of_bools[*]")

    def test_list_of_bools_all_star(self):
        self.assertEqual(
            self.husker.all("list_of_bools[*]"),
            [True, False, True]
        )

    ### list_of_lists_of_ints

    def test_list_of_lists_of_ints(self):
        result = self.husker.one("list_of_lists_of_ints")
        self.assertIsInstance(result, ListHusker)
        self.assertEqual(result, [[1, 2, 3], [4, 5, 6], [7, 8, 9]])

    def test_list_of_lists_of_ints_element(self):
        result = self.husker.one("list_of_lists_of_ints[1]")
        self.assertIsInstance(result, ListHusker)
        self.assertEqual(result, [4, 5, 6])

    def test_list_of_lists_of_ints_getitem_external(self):
        result = self.husker.one("list_of_lists_of_ints")[1]
        self.assertIsInstance(result, ListHusker)
        self.assertEqual(result, [4, 5, 6])

    def test_list_of_lists_one_star(self):
        with self.assertRaises(HuskerNotUnique):
            self.husker.one("list_of_lists_of_ints[*]")

    def test_list_of_lists_all_star(self):
        self.assertEqual(
            self.husker.all("list_of_lists_of_ints[*]"),
            [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
        )

    ### list_of_dicts_of_ints

    def test_list_of_dicts_of_ints(self):
        result = self.husker.one("list_of_dicts_of_ints")
        self.assertIsInstance(result, ListHusker)
        self.assertEqual(result, [
            {"a": 1, "b": 2},
            {"b": 2, "c": 3},
            {"c": 3, "d": 4}
        ])

    def test_list_of_dicts_of_ints_element(self):
        result = self.husker.one("list_of_dicts_of_ints[1]")
        self.assertIsInstance(result, JmesPathHusker)
        self.assertEqual(result, {"b": 2, "c": 3})

    def test_list_of_dicts_of_ints_getitem_external(self):
        result = self.husker.one("list_of_dicts_of_ints")[1]
        self.assertIsInstance(result, JmesPathHusker)
        self.assertEqual(result, {"b": 2, "c": 3})

    def test_list_of_dicts_one_star(self):
        with self.assertRaises(HuskerNotUnique):
            self.husker.one("list_of_dicts_of_ints[*]")

    def test_list_of_dicts_all_star(self):
        self.assertEqual(
            self.husker.all("list_of_dicts_of_ints[*]"),
            [
                {"a": 1, "b": 2},
                {"b": 2, "c": 3},
                {"c": 3, "d": 4}
            ],
        )

    def test_list_of_dicts_of_ints_element_property(self):
        result = self.husker.one("list_of_dicts_of_ints[1].b")
        self.assertIsInstance(result, ScalarHusker)
        self.assertEqual(result, 2)

    def test_list_of_dicts_of_ints_one_star_property(self):
        result = self.husker.one("list_of_dicts_of_ints[*].d")
        self.assertIsInstance(result, ScalarHusker)
        self.assertEqual(result, 4)

    def test_list_of_dicts_of_ints_all_star_property(self):
        # NB requires `all`, returns 2 matches
        result = self.husker.all("list_of_dicts_of_ints[*].b")
        self.assertIsInstance(result, ListHusker)
        self.assertEqual(result, [2, 2])

    ### dict_of_ints

    def test_dict_of_ints_keys(self):
        result = self.husker.all("dict_of_ints | keys(@)")
        self.assertIsInstance(result, ListHusker)
        self.assertEqual(sorted(result.raw), ["one", "too", "tree"])

    def test_dict_of_ints_values(self):
        result = self.husker.all("dict_of_ints | values(@)")
        self.assertIsInstance(result, ListHusker)
        self.assertEqual(sorted(result.raw), [1, 2, 3])

    def test_dict_of_ints_to_array(self):
        result = self.husker.all("dict_of_ints | values(@) | to_array(@)")
        self.assertIsInstance(result, ListHusker)
        self.assertEqual(sorted(result.raw), [1, 2, 3])

    def test_dict_of_ints_sort(self):
        result = self.husker.all("dict_of_ints | values(@) | sort(@)")
        self.assertIsInstance(result, ListHusker)
        self.assertEqual(sorted(result.raw), [1, 2, 3])

    # def test_simple_string_funny_chars(self):
    #     self.assertEqual(
    #         self.husker.one("`funny chars in key: '\\\"\\`!#$%^&*()_=-+[{}];:\\|/?,<>.`"),
    #         "boom",
    #     )

#----------------------------------------------------------------------------------------------------------------------------------
