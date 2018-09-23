#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# 3rd parties
import lxml.etree as ET

# alcazar
from .text import RE_NON_SPACE, normalize_spaces

#----------------------------------------------------------------------------------------------------------------------------------

LINE_BREAKING_TAGS = frozenset((
    'br',
))

PARAGRAPH_BREAKING_TAGS = frozenset((
    'address', 'applet', 'article', 'aside', 'blockquote', 'body', 'canvas', 'center', 'cite', 'dd', 'div', 'dl', 'dt', 'fieldset',
    'figcaption', 'figure', 'footer', 'form', 'frame', 'frameset', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'head', 'header', 'hr',
    'iframe', 'li', 'main', 'nav', 'noscript', 'object', 'ol', 'output', 'p', 'pre', 'section', 'table', 'tbody', 'td', 'textarea',
    'tfoot', 'th', 'thead', 'title', 'tr', 'ul', 'video',
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

class NodeWalk:

    def walk(self, node):
        if node.tag not in NON_TEXT_TAGS and not isinstance(node, ET._Comment): # pylint: disable=protected-access
            baton = self.open(node) # it's polymorphic, pylint: disable=assignment-from-no-return
            if node.text:
                self.text(node.text)
            for child in node:
                self.walk(child)
                if child.tail:
                    self.text(child.tail)
            self.close(node, baton)

    def open(self, node):
        pass

    def close(self, node, baton):
        pass

    def text(self, text):
        pass

    def finish(self):
        return None

    def __call__(self, node):
        self.walk(node)
        return self.finish()


class SingleLineTextExtractor(NodeWalk):

    def __init__(self):
        self.parts = []

    def open(self, node):
        insertion = ' ' if node.tag in LINE_BREAKING_TAGS or node.tag in PARAGRAPH_BREAKING_TAGS else None
        if insertion:
            self.parts.append(insertion)
        return insertion

    def close(self, node, insertion): # pylint: disable=arguments-differ
        if insertion:
            self.parts.append(insertion)

    def text(self, text):
        self.parts.append(text)

    def finish(self):
        return normalize_spaces(''.join(self.parts))


def extract_single_line_text(node):
    return SingleLineTextExtractor()(node)


class MultiLineTextExtractor(NodeWalk):

    def __init__(self):
        self.parts = ['']
        self.buffer = ''
        self.newlines = 0
        self.in_pre = 0

    def open(self, node):
        if node.tag in LINE_BREAKING_TAGS:
            self.newlines += 1
            newlines_after = 0
        elif node.tag in PARAGRAPH_BREAKING_TAGS:
            self.newlines += 2
            newlines_after = 2
            if node.tag == 'pre':
                self._flush()
                self.in_pre += 1
        else:
            newlines_after = 0
        return newlines_after

    def close(self, node, newlines_after): # pylint: disable=arguments-differ
        self.newlines += newlines_after
        if node.tag == 'pre':
            self._flush()
            self.in_pre -= 1

    def text(self, text):
        if self.newlines == 0:
            self.buffer += text
        elif RE_NON_SPACE.search(text) or self.in_pre:
            self._flush()
            self.buffer = text
        else:
            pass # drop spaces after newlines

    def _flush(self):
        self.parts[-1] += self.buffer if self.in_pre else normalize_spaces(self.buffer)
        if self.newlines == 1:
            self.parts[-1] += "\n"
        elif self.newlines > 1 and self.parts[-1]:
            self.parts.append('')
        self.newlines = 0
        self.buffer = ''

    def finish(self):
        self.newlines = 0
        self._flush()
        while self.parts and not self.parts[-1]:
            self.parts.pop()
        return '\n\n'.join(self.parts)


def extract_multiline_text(node):
    return MultiLineTextExtractor()(node)

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
