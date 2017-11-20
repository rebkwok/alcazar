#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

#----------------------------------------------------------------------------------------------------------------------------------

def detach_node(node, reattach_tail=True):
    """
    Just like calling node.getparent().remove(node), but takes care of reattaching the node's tail text. And it's shorter to type.
    """
    tail_str = node.tail
    parent_el = node.getparent()
    if tail_str and reattach_tail:
        prev_el = node.getprevious()
        if prev_el is not None:
            prev_el.tail = (prev_el.tail or '') + tail_str
        else:
            parent_el.text = (parent_el.text or '') + tail_str
    parent_el.remove(node)
    return node

#----------------------------------------------------------------------------------------------------------------------------------
