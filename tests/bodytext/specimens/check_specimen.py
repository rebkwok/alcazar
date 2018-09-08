#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from difflib import unified_diff
import gzip
from os import path
import re
from sys import argv

# alcazar
from alcazar import ArticleParser
from alcazar.etree_parser import parse_html_etree

#----------------------------------------------------------------------------------------------------------------------------------

def diff(extracted_text, reference_text, silent=False):
    diff = unified_diff(
        re.split(r'\n\n+', extracted_text),
        re.split(r'\n\n+', reference_text),
    )
    is_same = True
    for line in diff:
        print(line)
        is_same = False
    return is_same

#----------------------------------------------------------------------------------------------------------------------------------

# This this is also called from add_specimen.py

def run(html_file_path, silent=False):
    with gzip.open(html_file_path, 'rb') as file_in:
        html_text = file_in.read().decode('UTF-8')
    text_file_path = html_file_path.replace('.html.gz', '') + '.txt'
    if path.isfile(text_file_path):
        opener = open
    else:
        opener = gzip.open
        text_file_path += '.gz'
    with opener(text_file_path, 'rb') as file_in:
        for line in file_in:
            if line == b'\n':
                break # skip headers
        reference_text = b''.join(file_in).decode('UTF-8').rstrip()
    if reference_text:
        extracted_text = ArticleParser().parse_article(parse_html_etree(html_text)).body_text.rstrip()
        is_same = diff(
            extracted_text,
            reference_text,
            silent=silent,
        )
        if is_same and not silent:
            print("Extracted text matches reference")
        return is_same
    else:
        print("No reference text")
        return False


if __name__ == '__main__':
    if len(argv) == 2:
        run(argv[1])
    else:
        print("usage: %s <specimen.html.gz>" % argv[0], file=stderr)
        exit(2)

#----------------------------------------------------------------------------------------------------------------------------------
