#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from difflib import unified_diff
import gzip
import json
from os import path
import re
from sys import argv, stderr
from textwrap import wrap

# alcazar
from alcazar import ArticleParser
from alcazar.etree_parser import parse_html_etree
from alcazar.skeleton import Skeleton, align_skeletons

#----------------------------------------------------------------------------------------------------------------------------------

# NB this is also called from add_specimen.py

def run(html_file_path, skel_file_path, silent=False):
    file_name = path.basename(html_file_path)
    reference_skeleton = load_reference_skeleton(skel_file_path)
    extracted_skeleton = load_extracted_skeleton(html_file_path)
    alignment_steps = align_skeletons(reference_skeleton, extracted_skeleton)
    is_same = True
    output_lines = []
    for step in alignment_steps:
        if not step.is_match:
            is_same = False
        if not silent:
            if step.is_match:
                sign, item = (' ', step.item1)
            elif step.item1:
                sign, item = ('-', step.item1)
            else:
                sign, item = ('+', step.item2)
            output_lines.append('%s %s' % (sign, item.tag))
            output_lines.extend(
                '%s     %s' % (sign, line)
                for line in wrap(item.text, 120)
            )
    if is_same and not silent:
        output_lines.append('Extracted skeleton exactly matches reference')
    if output_lines:
        for line in output_lines:
            print(line)
    return is_same


def load_extracted_skeleton(html_file_path):
    with gzip.open(html_file_path, 'rb') as file_in:
        html_text = file_in.read().decode('UTF-8')
    return ArticleParser() \
        .parse_article(parse_html_etree(html_text)) \
        .skeleton


def load_reference_skeleton(skel_file_path):
    opener = gzip.open if '.gz' in skel_file_path else open
    with opener(skel_file_path, 'rb') as file_in:
        return Skeleton.load_from_lines(
            line.decode('UTF-8')
            for line in file_in
        )


def find_skel_file(html_file_path):
    skel_file_path = html_file_path.replace('.html.gz', '') + '.skel'
    print(skel_file_path)
    if path.isfile(skel_file_path):
        return skel_file_path
    else:
        return skel_file_path + '.gz'


if __name__ == '__main__':
    if 2 <= len(argv) <= 3:
        run(
            html_file_path=argv[1],
            skel_file_path=argv[2] if len(argv) > 2 else find_skel_file(argv[1]),
        )
    else:
        print("usage: %s <specimen.html.gz>" % argv[0], file=stderr)
        exit(2)

#----------------------------------------------------------------------------------------------------------------------------------
