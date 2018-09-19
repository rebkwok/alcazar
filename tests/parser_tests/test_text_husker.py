#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import re

# alcazar
from alcazar.husker import TextHusker

# tests
from .plumbing import AlcazarTest

#----------------------------------------------------------------------------------------------------------------------------------

class TextHuskerTest(AlcazarTest):

    text_str = """
        This is my text.
        There are many like it but this one is mine.
    """

    def test_normalized(self):
        text_husker = TextHusker(self.text_str)
        self.assertEqual(
            text_husker.raw,
            self.text_str,
        )
        self.assertEqual(
            text_husker.normalized.raw,
            "This is my text. There are many like it but this one is mine.",
        )

    def test_regex_as_str(self):
        self.assertEqual(
            TextHusker(self.text_str).one('This is my (\w+)'),
            'text',
        )

    def test_regex_as_compiled(self):
        self.assertEqual(
            TextHusker(self.text_str).one(re.compile('This is my (\w+)')),
            'text',
        )

#----------------------------------------------------------------------------------------------------------------------------------
