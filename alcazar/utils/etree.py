#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import re

# 3rd parties
import lxml.etree as ET

# alcazar
from .text import normalize_spaces

#----------------------------------------------------------------------------------------------------------------------------------

PARAGRAPH_BREAKING_TAGS = frozenset((
    'address', 'applet', 'blockquote', 'body', 'center', 'cite', 'dd', 'div', 'dl', 'dt', 'fieldset', 'form', 'frame', 'frameset',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'head', 'hr', 'iframe', 'li', 'noscript', 'object', 'ol', 'p', 'table', 'tbody', 'td',
    'textarea', 'tfoot', 'th', 'thead', 'title', 'tr', 'ul',
))

NON_TEXT_TAGS = frozenset((
    'script', 'style',
))

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

def extract_multiline_text(node):
    return re.sub(
        r'\s+',
        lambda m: "\n\n" if "\n\n" in m.group() else "\n" if "\n" in m.group() else " ",
        ''.join(_multiline_parts(node)),
    ).strip()

def _multiline_parts(node, inside_pre=False):
    if node.tag == 'pre':
        inside_pre = True
    if node.tag == 'br':
        yield "\n"
    elif node.tag in PARAGRAPH_BREAKING_TAGS:
        yield "\n\n"
    if node.tag not in NON_TEXT_TAGS and not isinstance(node, ET._Comment): # pylint: disable=protected-access
        if node.text:
            yield node.text if inside_pre else normalize_spaces(node.text)
        for child in node:
            for value in _multiline_parts(child, inside_pre):
                yield value
    if node.tag in PARAGRAPH_BREAKING_TAGS:
        yield "\n\n"
    if node.tail:
        yield node.tail if inside_pre else normalize_spaces(node.tail)

#----------------------------------------------------------------------------------------------------------------------------------

def walk_subtree_allowing_edits(root, include_root=True):
    """
    Like the standard ET._Element.iter() or iterdescendants(), this function iterates on the given node's subtree, optionally
    including the node itself.

    Unlike the etree methods, however, and more like JavaScript's getElementsByTagName, this tree walker tolerates the tree being
    modified while you're walking it. In particular, if you remove from the tree any of the nodes it yields, that node's subtree
    won't be explored.

    >>> import lxml.etree as ET
    >>> doc = lambda: ET.HTML ('''
    ...    <html>
    ...      <head><title/></head>
    ...      <body>
    ...        <table>
    ...          <tr1><td1/></tr1>
    ...          <tr2><td2/></tr2>
    ...          <tr3><td3/></tr3>
    ...        </table>
    ...        <div><p><b/></p></div>
    ...      </body>
    ...    </html>
    ... ''')
    >>> head = lambda: doc().xpath('/html/head')[0]
    >>> body = lambda: doc().xpath('/html/body')[0]
    >>> tags = lambda iter_nodes: ','.join (n.tag for n in iter_nodes)

    >>> tags (walk_subtree_allowing_edits (doc()))
    'html,head,title,body,table,tr1,td1,tr2,td2,tr3,td3,div,p,b'
    >>> tags (walk_subtree_allowing_edits (doc(), include_root=False))
    'head,title,body,table,tr1,td1,tr2,td2,tr3,td3,div,p,b'
    >>> tags (walk_subtree_allowing_edits (head()))
    'head,title'
    >>> tags (walk_subtree_allowing_edits (head(), include_root=False))
    'title'

    >>> def t ():
    ...   for node in walk_subtree_allowing_edits (body()):
    ...     yield node
    ...     if node.tag == 'table':
    ...       node.getparent().remove (node)
    >>> tags (t())
    'body,table,div,p,b'

    >>> def t ():
    ...   for node in walk_subtree_allowing_edits (body()):
    ...     yield node
    ...     if node.tag == 'tr2':
    ...       node.getparent().remove (node)
    >>> tags (t())
    'body,table,tr1,td1,tr2,tr3,td3,div,p,b'

    >>> def t ():
    ...   for node in walk_subtree_allowing_edits (body()):
    ...     yield node
    ...     if node.tag == 'tr2':
    ...       node.getparent().remove (node.getnext())
    >>> tags (t())
    'body,table,tr1,td1,tr2,td2,div,p,b'
    """

    stack = [root.getparent(), root]
    while len(stack) > 1:
        node = stack[-1]

        explore_children = True
        if len(stack) > 2 or include_root:
            # When a node is removed from the tree, its next() link is nulled, so we need to make a copy ahead of giving the caller
            # the chance to remove the node
            next_sibling = node.getnext()
            yield node
            if node.getparent() != stack[-2]:
                explore_children = False
        else:
            next_sibling = None

        if explore_children and len(node) > 0:
            stack.append(node[0])
        else:
            while len(stack) > 2:
                if next_sibling is not None:
                    stack[-1] = next_sibling
                    break
                else:
                    stack.pop()
                    next_sibling = stack[-1].getnext()
            else:
                # don't explore the root's siblings
                break

#----------------------------------------------------------------------------------------------------------------------------------
