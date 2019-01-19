#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# alcazar
from alcazar.etree_parser import strip_xml_namespaces

# tests
from .plumbing import AlcazarTest

#----------------------------------------------------------------------------------------------------------------------------------

class XmlLoaderTests(AlcazarTest):

    def test_strip_xml_namespaces(self):
        for prefix in ("bookreview", "getcapabilities", "soap", "soap2"):
            with self.open_fixture(prefix + "_with_namespaces.xml") as fh:
                xml_bytes_with_namespaces = fh.read()
            with self.open_fixture(prefix + "_without_namespaces.xml") as fh:
                xml_bytes_without_namespaces = fh.read()
            self.assertEqual(
                strip_xml_namespaces(xml_bytes_with_namespaces),
                xml_bytes_without_namespaces,
            )

#----------------------------------------------------------------------------------------------------------------------------------
