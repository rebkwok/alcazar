#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This was copies and then derived from the Readability JavaScript bookmarklet, from arc90labs. The original code is at
# http://code.google.com/p/arc90labs-readability/, and pretty much all credit should go there.

# Functionality that the original offers and we don't:
#
#  * Fetching all pages from multipage articles
#  * Handle framesets, i.e. find the main frame and apply yourself onto it
#  * They keep videos from YouTube and Vimeo, we don't.
#  * I probably introduced a bug or two

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from copy import deepcopy
from math import floor
from optparse import OptionParser # i'll upgrade to argparse tomorrow, pylint: disable=deprecated-module
import re

# 3rd party libs
import lxml.etree as ET

# alcazar
from .etree_parser import parse_html_etree
from .utils.compatibility import bytes_type, stdin_buffer, stdout_buffer, text_type
from .utils.etree import detach_node, extract_multiline_text, walk_subtree_allowing_edits
from .utils.text import normalize_spaces

#----------------------------------------------------------------------------------------------------------------------------------
# globals, constants

RE_UNLIKELY_CANDIDATES = re.compile(
    r'''
        combx|comment|community|disqus|extra|foot|header|menu|remark|rss|shoutbox|sidebar|sponsor|ad-break|agegate|pagination
        |pager|popup|tweet|twitter
    ''',
    re.I|re.X,
)

RE_OK_MAYBE_ITS_A_CANDIDATE = re.compile(
    r'and|article|body|column|main|shadow',
    re.I,
)

RE_POSITIVE_CSS_CLASS_NAMES = re.compile(
    r'article|body|content|entry|hentry|main|page|pagination|post|text|blog|story',
    re.I,
)

RE_NEGATIVE_CSS_CLASS_NAMES = re.compile(
    r'''
        combx|comment|com-|contact|foot|footer|footnote|masthead|media|meta|outbrain|promo|related|scroll|shoutbox|sidebar|sponsor
        |shopping|tags|tool|widget
    ''',
    re.I,
)

RE_REPLACE_BRS = re.compile(
    r'(<br[^>]*>[ \n\r\t]*){2,}',
    re.I
)

RE_REPLACE_FONTS = re.compile(
    r'<(\/?)font[^>]*>',
    re.I,
)

DIV_TO_P_ELEMENTS = frozenset(['a', 'blockquote', 'dl', 'div', 'img', 'ol', 'p', 'pre', 'table', 'ul'])

BASE_CONTENT_SCORE = {
    # This is adapted from method `initializeNode' in the original
    'address': -3,
    'blockquote': 3,
    'dd': -3,
    'div': 5,
    'dl': -3,
    'dt': -3,
    'form': -3,
    'h1': -5,
    'h2': -5,
    'h3': -5,
    'h4': -5,
    'h5': -5,
    'h6': -5,
    'li': -3,
    'ol': -3,
    'pre': 3,
    'td': 3,
    'th': -5,
    'ul': -3,
}

#----------------------------------------------------------------------------------------------------------------------------------
# data structures

class Article(object):

    def __init__(self, title, body_node):
        self.title = title
        self.body_node = body_node

    @property
    def body_text(self):
        return self.body_node and extract_multiline_text(self.body_node)

#----------------------------------------------------------------------------------------------------------------------------------

class ArticleParser(object):

    def parse_article(self, article_html, **kwargs):
        self._clean_html_before_parsing(article_html)
        return Article(
            title=self._grab_title(article_html),
            body_node=self._grab_article(article_html, **kwargs),
        )

    def _clean_html_before_parsing(self, article_html):
        for script in article_html.xpath('//script'):
            detach_node(script)
        for style_node in article_html.xpath('//style'):
            detach_node(style_node)
        return ET.HTML(
            RE_REPLACE_FONTS.sub(
                lambda m: '<%sspan>' % m.group(1),
                RE_REPLACE_BRS.sub('</p><p>', ET.tostring(article_html, encoding=text_type))
            )
        )

    def _grab_title(self, html_doc):
        match = html_doc.xpath('//title')
        if not match:
            return None
        title_str = self._get_inner_text(match[0])
        orig_str = title_str

        # Try to remove website name, etc.
        if re.search(r' [\|\-] ', title_str):
            title_str = re.sub(r' [\|\-] .*', '', title_str)
            if title_str.count(' ') < 2:
                title_str = re.sub(r'[^\|\-]*[\|\-]', '', orig_str)
        elif ': ' in title_str:
            title_str = re.sub(r'.*:', '', title_str)
            if title_str.count(' ') < 2:
                title_str = re.sub(r'[^:]*[:]', '', orig_str)
        elif len(title_str) < 15 or len(title_str) > 150:
            all_h1_els = html_doc.xpath('//h1')
            if len(all_h1_els) == 1:
                title_str = self._get_inner_text(all_h1_els[0])

        # Cleanup whitespace, check that title has likely length
        title_str = title_str.strip()
        if title_str.count(' ') <= 3:
            title_str = orig_str

        return title_str

    def _grab_article(self, html_doc, strip_unlikelys=True, weight_classes=True, do_clean_conditionally=True):
        # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        original_html_doc = deepcopy(html_doc)

        # Comment from arc90labs: First, node prepping. Trash nodes that look cruddy (like ones with the class name "comment", etc),
        # and turn divs into P tags where they have been used inappropriately (as in, where they contain no other block level
        # elements.)
        nodes_to_score = []

        for node in walk_subtree_allowing_edits(html_doc, include_root=False):

            if strip_unlikelys:
                unlikely_match_str = (node.get('class') or '') + (node.get('id') or '')
                if node.tag != 'body' \
                      and RE_UNLIKELY_CANDIDATES.search(unlikely_match_str) \
                      and not RE_OK_MAYBE_ITS_A_CANDIDATE.search(unlikely_match_str):
                    detach_node(node)
                    continue

            if node.tag in ('p', 'td', 'pre', 'inline_p'):
                nodes_to_score.append(node)

            # Comment from arc90labs: Turn all divs that don't have children block level elements into p's
            if node.tag == 'div':
                if not any(d.tag in DIV_TO_P_ELEMENTS for d in node.iterdescendants()):
                    node.tag = 'p'
                    nodes_to_score.append(node)

                else:
                    # Comment from arc90labs: EXPERIMENTAL
                    #
                    # NB - 2011-05-16 - the original JS code creates <p> tags here and sets their dislpay to 'inline'. We would
                    # like to create <p> tags too, because that's meaningful to the algorithms that follow, but our rendering
                    # function does not honour CSS, and so inserting p's here inserts line breaks in our output. So we insert the
                    # dummy `inline_p' tag, and adjust the algorithm below to take that into account. This is rather silly, but
                    # should be OK because the algorithm won't evolve (being a copy of an external JS file)

                    if node.text:
                        text = node.text
                        node.text = ''
                        new_node = ET.Element('inline_p')
                        new_node.text = text
                        node.insert(0, new_node)
                    for child_node in list(node):
                        if child_node.tail:
                            tail = child_node.tail
                            child_node.tail = None
                            new_node = ET.Element('inline_p')
                            new_node.text = tail
                            child_node.addnext(new_node)

        # Comment from arc90labs: Loop through all paragraphs, and assign a score to them based on how content-y they look. Then
        # add their score to their parent node.
        #
        # A score is determined by things like number of commas, class names, etc. Maybe eventually link density.
        all_candidates = []
        content_score_per_node = {}
        for node in nodes_to_score:

            parent_node = node.getparent()
            grandparent_node = parent_node.getparent() if parent_node is not None else None
            inner_text = self._get_inner_text(node)
            if parent_node is None:
                continue

            # Comment from arc90labs: If this paragraph is less than 25 characters, don't even count it.
            if len(inner_text) < 25:
                continue

            if parent_node not in content_score_per_node:
                content_score_per_node[parent_node] = self._init_content_score(parent_node, weight_classes)
                all_candidates.append(parent_node)
            if grandparent_node is not None and grandparent_node not in content_score_per_node:
                content_score_per_node[grandparent_node] = self._init_content_score(grandparent_node, weight_classes)
                all_candidates.append(grandparent_node)

            content_score = 0

            # Comment from arc90labs: Add a point for the paragraph itself as a base.
            content_score += 1

            # Comment from arc90labs: Add points for any commas within this paragraph
            content_score += inner_text.count(',') + 1

            # Comment from arc90labs: For every 100 characters in this paragraph, add another point. Up to 3 points.
            content_score += min(len(inner_text)/100, 3)

            # Comment from arc90labs: Add the score to the parent. The grandparent gets half.
            content_score_per_node[parent_node] += content_score
            if grandparent_node is not None:
                content_score_per_node[grandparent_node] += content_score/2.0

        # Comment from arc90labs: scale the final candidates score based on link density. Good content should have a relatively
        # small link density (5% or less) and be mostly unaffected by this operation.
        for candidate in all_candidates:
            content_score_per_node[candidate] *= 1 - self._get_link_density(candidate)

        # Comment from arc90labs: after we've calculated scores, loop through all of the possible candidate nodes we found and find
        # the
        # one with the highest score.
        if all_candidates:
            top_candidate = max(all_candidates, key=content_score_per_node.get)
        else:
            # Comment from arc90labs: If we still have no top candidate, just use the body as a last resort.
            matches = html_doc.xpath('//body')
            if not matches:
                return None
            top_candidate = matches[0]
            if top_candidate not in content_score_per_node:
                content_score_per_node[top_candidate] = self._init_content_score(top_candidate, weight_classes)

        # Comment from arc90labs: Now that we have the top candidate, look through its siblings for content that might also be
        # related.
        # Things like preambles, content split by ads that we removed, etc.
        article_body_el = html_doc.makeelement('div')
        sibling_score_threshold = max(10, content_score_per_node[top_candidate] * 0.2)
        for sibling_node in (top_candidate.getparent() if top_candidate.getparent() is not None else ()):
            append = False

            if sibling_node == top_candidate:
                append = True

            # Comment from arc90labs: Give a bonus if sibling nodes and top candidates have the example same classname
            content_bonus = 0
            if top_candidate.get('class', '') and sibling_node.get('class') == top_candidate.get('class'):
                content_bonus += content_score_per_node[top_candidate] * 0.2

            if sibling_node in content_score_per_node \
                    and content_score_per_node[sibling_node] + content_bonus > sibling_score_threshold:
                append = True

            if sibling_node.tag in ('p', 'inline_p'):
                sibling_text = self._get_inner_text(sibling_node)
                ld = self._get_link_density(sibling_node)
                text_length = len(sibling_text)
                if text_length > 80 and ld < 0.25:
                    append = True
                elif text_length <= 80 and ld == 0 and re.match(r'\.( |$)', sibling_text):
                    append = True

            if append:
                if sibling_node.tag not in ('div', 'p', 'inline_p'):
                    sibling_node.tag = 'div'
                article_body_el.append(sibling_node)

        # Comment from arc90labs: so we have all of the content that we need. Now we clean it up for presentation.
        article_body_el = self._prep_article(article_body_el, weight_classes, do_clean_conditionally, content_score_per_node)

        # Comment from arc90labs: Now that we've gone through the full algorithm, check to see if we got any meaningful content. If
        # we didn't, we may need to re-run grabArticle with different flags set. This gives us a higher likelihood of finding the
        # content, and the sieve approach gives us a higher likelihood of finding the -right- content.
        if len(self._get_inner_text(article_body_el, do_normalize_spaces=False)) < 250:
            if strip_unlikelys:
                return self._grab_article(
                    original_html_doc,
                    strip_unlikelys=False,
                    weight_classes=weight_classes,
                    do_clean_conditionally=do_clean_conditionally,
                )
            elif weight_classes:
                return self._grab_article(
                    original_html_doc,
                    strip_unlikelys=False,
                    weight_classes=False,
                    do_clean_conditionally=do_clean_conditionally,
                )
            elif do_clean_conditionally:
                return self._grab_article(
                    original_html_doc,
                    strip_unlikelys=False,
                    weight_classes=False,
                    do_clean_conditionally=False,
                )
            else:
                return None
        else:
            return article_body_el

    def _prep_article(self, article_body_el, weight_classes, do_clean_conditionally, content_score_per_node):

        if do_clean_conditionally:
            self._clean_conditionally(article_body_el, "form", content_score_per_node, weight_classes)
        self._clean(article_body_el, "object")
        self._clean(article_body_el, "h1")

        # Comment from arc90labs: if there is only one h2, they are probably using it as a header and not a subheader, so remove it
        # since we already have a header.
        if len(article_body_el.xpath('.//h2')) == 1:
            self._clean(article_body_el, 'h2')
        self._clean(article_body_el, 'iframe')

        for header_tag in ('h1', 'h2'):
            for header_node in article_body_el.xpath('.//%s' % header_tag):
                weight = self._get_class_weight(header_node) if weight_classes else 0
                if weight < 0 or self._get_link_density(header_node) > 0.33:
                    detach_node(header_node)

        # Comment from arc90labs: do these last as the previous stuff may have removed junk that will affect these
        if do_clean_conditionally:
            self._clean_conditionally(article_body_el, "table", content_score_per_node, weight_classes)
            self._clean_conditionally(article_body_el, "ul", content_score_per_node, weight_classes)
            self._clean_conditionally(article_body_el, "div", content_score_per_node, weight_classes)

        return ET.HTML(
            re.sub(
                r'(?:<br[^>]*>\s*)+(?=<p\b)',
                '',
                ET.tostring(article_body_el, encoding=text_type)
                )
            )

    def _init_content_score(self, node, weight_classes):
        content_score = BASE_CONTENT_SCORE.get(node.tag, 0)
        if weight_classes:
            content_score += self._get_class_weight(node)
        return content_score

    def _get_class_weight(self, node):
        weight = 0
        for attr in ('class', 'id'):
            val = node.get(attr)
            if val:
                if RE_POSITIVE_CSS_CLASS_NAMES.search(val):
                    weight += 25
                if RE_NEGATIVE_CSS_CLASS_NAMES.search(val):
                    weight -= 25
        return weight

    def _get_link_density(self, node):
        text_length = len(self._get_inner_text(node))
        if text_length:
            link_length = sum(
                len(self._get_inner_text(link_el))
                for link_el in node.xpath('.//a')
                )
            return link_length * 1.0 / text_length
        else:
            return 0

    def _clean(self, node, tag_to_remove):
        for node_to_remove in node.xpath('.//%s' % tag_to_remove):
            detach_node(node_to_remove)

    def _get_inner_text(self, node, do_normalize_spaces=True):
        text = ''.join(node.itertext())
        if do_normalize_spaces:
            text = normalize_spaces(text)
        # NB strip regardless of what `do_normalize_spaces' is set to
        return text.strip()

    def _clean_conditionally(self, node, tag_to_remove, content_score_per_node, weight_classes):
        # pylint: disable=too-many-locals
        for node_to_remove in node.xpath('.//%s' % tag_to_remove):
            weight = self._get_class_weight(node) if weight_classes else 0
            content_score = content_score_per_node.get(node_to_remove, 0)

            if weight + content_score < 0:
                detach_node(node_to_remove)
            else:
                node_to_remove_text = self._get_inner_text(node_to_remove)
                if node_to_remove_text.count(',') < 10:
                    # Comment from arc90labs: if there are not very many commas, and the number of non-paragraph elements is more
                    # than paragraphs or other ominous signs, remove the element.
                    p = len(node_to_remove.xpath('.//p'))
                    img = len(node_to_remove.xpath('.//img'))
                    li = len(node_to_remove.xpath('.//li')) - 100
                    input = len(node_to_remove.xpath('.//input'))
                    embed = len(node_to_remove.xpath('.//embed'))

                    link_density = self._get_link_density(node_to_remove)
                    content_length = len(node_to_remove_text)

                    # sorry, pylint: disable=too-many-boolean-expressions
                    if (
                        img > p
                        or (li > p and node_to_remove.tag not in ('ul', 'ol'))
                        or (input > floor(p / 3.0))
                        or (content_length < 25 and (img == 0 or img > 2))
                        or (weight < 25 and link_density > 0.2)
                        or (weight >= 25 and link_density > 0.5)
                        or ((embed == 1 and content_length < 75) or embed > 1)
                        ):
                        detach_node(node_to_remove)

#----------------------------------------------------------------------------------------------------------------------------------
# convenience

def parse_article(source):
    if isinstance(source, bytes_type):
        raise TypeError("You must decode those bytes before we can parse them")
    if isinstance(source, text_type):
        article_html = parse_html_etree(source)
    else:
        # it better be an etree element or something compatible
        article_html = source
    parser = ArticleParser()
    return parser.parse_article(article_html)


def parse_body_text(source):
    return parse_article(source).body_text

#----------------------------------------------------------------------------------------------------------------------------------
# cmd line interface

def main():
    cmdline = OptionParser()
    cmdline.add_option('-i', '--input-file', dest='input_filename')
    cmdline.add_option('--input-encoding', dest='input_encoding', default='UTF-8', metavar='ENCODING')
    cmdline.add_option('-o', '--output-file', dest='output_filename')
    cmdline.add_option('--output-encoding', dest='output_encoding', default='UTF-8', metavar='ENCODING')
    cmdline_opt, _args_unused = cmdline.parse_args()

    input_fh = open(cmdline_opt.input_filename, 'rb') if cmdline_opt.input_filename else stdin_buffer
    input_html_str = input_fh.read().decode(cmdline_opt.input_encoding)
    input_fh.close()

    article = parse_article(input_html_str)

    output_fh = open(cmdline_opt.output_filename, 'wb') if cmdline_opt.output_filename else stdout_buffer
    if article.title:
        output_fh.write(article.title.encode(cmdline_opt.output_encoding))
        output_fh.write(b'\n\n')
    if article.body_node is not None:
        output_fh.write(article.body_text.encode(cmdline_opt.output_encoding))
        output_fh.write(b'\n')
    output_fh.close()


if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
