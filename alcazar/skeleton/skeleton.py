#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from collections import OrderedDict, namedtuple
from itertools import chain
import re
from textwrap import wrap

#----------------------------------------------------------------------------------------------------------------------------------
# constants

HEADER_TAGS = frozenset((
    'retrieved',
    'title',
    'url',
))

BODY_TAGS = frozenset((
    'caption',
    'figure',
    'footer',
    'heading', # i.e. <h1> etc
    'lede',
    'listitem',
    'meta', # e.g. author, date
    'paragraph',
    'quote',
    'rule', # i.e. <hr>
))

NO_CONTENT = frozenset((
    'rule',
))

AMBIGUOUS = object()

def _compile_tag_abbreviations():
    abbreviations = {}
    for full_tag in chain(HEADER_TAGS, BODY_TAGS):
        for n in range(1, len(full_tag)):
            prefix = full_tag[:n]
            if prefix in abbreviations:
                abbreviations[prefix] = AMBIGUOUS
            else:
                abbreviations[prefix] = full_tag
    return abbreviations

TAG_ABBREVIATIONS = _compile_tag_abbreviations()

#----------------------------------------------------------------------------------------------------------------------------------
# data struc

SkeletonItem = namedtuple('SkeletonItem', (
    'tag',
    'text',
))

#----------------------------------------------------------------------------------------------------------------------------------

class Skeleton(object):

    def __init__(self, head, body):
        self.head = head
        self.body = body

    def __iter__(self):
        for item in self.head.values():
            yield item
        for item in self.body:
            yield item

    def validate(self):
        for item in self.head.values():
            if item.tag not in HEADER_TAGS:
                raise ValueError("Invalid header tag: %r" % (item.tag,))
        for item in self.body:
            if item.tag in HEADER_TAGS:
                if item.tag in self.head:
                    raise ValueError("Duplicated header tag %r" % (item.tag,))
                else:
                    raise ValueError("Header tag in body: %r" % (item.tag,))
            elif item.tag not in BODY_TAGS:
                raise ValueError("Unknown tag: %r" % (item.tag,))
            if item.tag not in NO_CONTENT and not item.text:
                raise ValueError("Empty item: %r" % (item,))
            if item.tag in NO_CONTENT and item.text:
                raise ValueError("Item shouldn't have content: %r" % (item,))

    @classmethod
    def build(cls, iter_items):
        available_header_tags = set(HEADER_TAGS)
        head = OrderedDict()
        iter_items = iter(iter_items)
        body = []
        for item in iter_items:
            if item.tag in available_header_tags:
                available_header_tags.remove(item.tag)
                head[item.tag] = item
            else:
                body.append(item)
                break
        body.extend(iter_items)
        return cls(head, tuple(body))

    def dump_to_lines(self):
        for item in self.head.values():
            yield '%s %s' % item
        for item in self.body:
            yield item.tag
            for line in wrap(item.text, break_on_hyphens=False):
                yield '    %s' % line

    @classmethod
    def load_from_lines(cls, iter_lines):
        items = []
        tag = text = None
        for line in chain(iter_lines, ['eof']):
            if line[0].isspace():
                assert tag, (tag, text, line)
                line = line.strip()
                if line:
                    text += (' ' if text else '') + line
            else:
                match = re.search(r'^(\w+)\s*(.*)', line)
                assert match, repr(line)
                if tag and match:
                    items.append(SkeletonItem(tag.lower(), text))
                tag = TAG_ABBREVIATIONS.get(match.group(1), match.group(1))
                if tag is AMBIGUOUS:
                    raise ValueError("Tag %r is ambiguous" % match.group(1))
                text = match.group(2) or ''
        return cls.build(items)

#----------------------------------------------------------------------------------------------------------------------------------
