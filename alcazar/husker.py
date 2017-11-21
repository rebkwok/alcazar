#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from datetime import datetime
from functools import reduce
import operator
import re
from types import GeneratorType

# 3rd parties
import lxml.etree as ET
try:
    from lxml.cssselect import CSSSelector
except ImportError:
    CSSSelector = NotImplemented

# alcazar
from .exceptions import ScraperError
from .utils.compatibility import PY2, bytes_type, text_type
from .utils.etree import detach_node
from .utils.jsonutils import lenient_json_loads, strip_js_comments
from .utils.text import normalize_spaces

#----------------------------------------------------------------------------------------------------------------------------------
# globals

_builtin_int = int

#----------------------------------------------------------------------------------------------------------------------------------
# exceptions

class HuskerError(ScraperError):
    pass

class HuskerMismatch(HuskerError):
    pass

class HuskerNotUnique(HuskerError):
    pass

class HuskerMultipleSpecMatch(HuskerNotUnique):
    pass

#----------------------------------------------------------------------------------------------------------------------------------

class Selector(object):
    # This could as well be part of `Husker`, it's separated only for readability and an aesthetic separation of concerns

    @property
    def id(self):
        return self.__class__.__name__

    def __call__(self, *args, **kwargs):
        return self.one(*args, **kwargs)

    def selection(self, *spec):
        """
        Runs a search for the given spec, and returns the results, as a ListHusker
        """
        raise NotImplementedError

    def parts(self, **fields):
        for key, husker in fields.items():
            if not isinstance(husker, Husker):
                husker = self.one(husker)
            yield key, husker

    def one(self, *spec):
        selected = self.selection(*spec)
        if len(selected) == 0:
            raise HuskerMismatch('%s found no matches for %s in %s' % (self.id, self.repr_spec(*spec), self.repr_value()))
        elif len(selected) > 1:
            raise HuskerNotUnique('%s expected 1 match for %s, found %d' % (self.id, self.repr_spec(*spec), len(selected)))
        else:
            return selected[0]

    def some(self, *spec):
        selected = self.selection(*spec)
        if len(selected) == 0:
            return NULL_HUSKER
        elif len(selected) > 1:
            raise HuskerNotUnique('%s expected 1 match for %s, found %d' % (self.id, self.repr_spec(*spec), len(selected)))
        else:
            return selected[0]

    def first(self, *spec):
        selected = self.selection(*spec)
        if len(selected) == 0:
            raise HuskerMismatch('%s found no matches for %s' % (self.id, self.repr_spec(*spec)))
        else:
            return selected[0]

    def last(self, *spec):
        selected = self.selection(*spec)
        if len(selected) == 0:
            raise HuskerMismatch('%s found no matches for %s' % (self.id, self.repr_spec(*spec)))
        else:
            return selected[-1]

    def any(self, *spec):
        selected = self.selection(*spec)
        if len(selected) == 0:
            return NULL_HUSKER
        else:
            return selected[0]

    def all(self, *spec):
        selected = self.selection(*spec)
        if not selected:
            raise HuskerMismatch('%s found no matches for %s' % (self.id, self.repr_spec(*spec)))
        return selected

    def one_of(self, *all_specs):
        match = self.some_of(*all_specs)
        if not match:
            raise HuskerMismatch("%s: none of the specified specs matched %r: %s" % (
                self.id,
                self.value,
                ', '.join('"%s"' % spec for spec in all_specs),
            ))
        return match

    def some_of(self, *all_specs):
        match = matching_spec = None
        for spec in all_specs:
            if not isinstance(spec, (list, tuple)):
                spec = [spec]
            selected = self.some(*spec)
            if selected:
                if matching_spec is None:
                    match, matching_spec = selected, spec
                else:
                    raise HuskerMultipleSpecMatch('%s: both %s and %s matched' % (
                        self.id,
                        self.repr_spec(*matching_spec),
                        self.repr_spec(*spec),
                    ))
        return match

    def first_of(self, *all_specs):
        for spec in all_specs:
            if not isinstance(spec, (list, tuple)):
                spec = [spec]
            selected = self.any(*spec)
            if selected:
                return selected
        raise HuskerMismatch("%s: none of the specified specs matched: %s" % (
            self.id,
            ', '.join('"%s"' % spec for spec in all_specs),
        ))

    def any_of(self, *all_specs):
        for spec in all_specs:
            if not isinstance(spec, (list, tuple)):
                spec = [spec]
            selected = self.any(*spec)
            if selected:
                return selected
        return NULL_HUSKER

    def all_of(self, *all_specs):
        return ListHusker(
            element
            for spec in all_specs
            for element in self.all(spec)
        )

    def selection_of(self, *all_specs):
        return ListHusker(
            element
            for spec in all_specs
            for element in self.selection(spec)
        )

#----------------------------------------------------------------------------------------------------------------------------------
# utils

def _forward_to_value(method_name, return_type):
    def method(self, *args, **kwargs):
        if return_type is text_type:
            convert = TextHusker
        elif return_type is list:
            convert = lambda values: ListHusker(map(TextHusker, values))
        else:
            convert = return_type
        wrapped = getattr(self.value, method_name, None)
        if callable(wrapped):
            return convert(wrapped(*args, **kwargs))
        else:
            raise NotImplementedError((self.value.__class__.__name__, method_name))
    return method

#----------------------------------------------------------------------------------------------------------------------------------

class Husker(Selector):
    """
    A Husker is used to extract from a raw document those bits of data that are of relevance to our scraper. It does not concern
    itself with cleaning or converting that data -- that's for the `Cleaner` to do. A Husker is just about locating the document
    node, or the text substring, that we're looking for.
    """

    def __init__(self, value):
        self.value = value

    @property
    def text(self):
        """
        Returns a TextHusker, whose value is this husker's text contents. The definition of what constitutes "this husker's text
        contents" is up to the implementing subclass.
        """
        raise NotImplementedError(repr(self))

    @property
    def multiline(self):
        """ Same as `text`, but preserves line breaks """
        raise NotImplementedError(repr(self))

    def json(self):
        return lenient_json_loads(self.str)

    @property
    def str(self):
        return self.text.value

    @property
    def int(self):
        return int(self.str)

    @property
    def float(self):
        return float(self.str)

    def datetime(self, fmt):
        return datetime.strptime(self.str, fmt)

    def map(self, function):
        return function(self.raw)

    def map_const(self, value):
        return value

    def then(self, function):
        return function(self)

    def filter(self, function):
        if function(self):
            return self
        else:
            return NULL_HUSKER

    @property
    def raw(self):
        # In the default case, return .value, but some subclasses override this
        return self.value

    def __bool__(self):
        """
        A husker evaluates as truthy iff it holds a value at all, irrespective of what that value's truthiness is.
        """
        return self.value is not None        

    if PY2:
        # NB don't just say `__nonzero__ = __bool__` because `__bool__` is overriden in some subclasses
        def __nonzero__(self):
            return self.__bool__()

    def repr_spec(self, *spec):
        if len(spec) == 1:
            return repr(spec[0])
        else:
            return repr(spec)

    def repr_value(self):
        return repr(self.text.value)

    def __str__(self):
        return self.text.value

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.value)

    __hash__ = _forward_to_value('__hash__', _builtin_int)
    __eq__ = _forward_to_value('__eq__', bool)
    __lt__ = _forward_to_value('__lt__', bool)
    __le__ = _forward_to_value('__le__', bool)
    __gt__ = _forward_to_value('__gt__', bool)
    __ge__ = _forward_to_value('__ge__', bool)

#----------------------------------------------------------------------------------------------------------------------------------

class NullHusker(Husker):

    def __init__(self):
        super(NullHusker, self).__init__(None)

    def selection(self, *spec_ignored):
        return EMPTY_LIST_HUSKER

    @property
    def text(self):
        return NULL_HUSKER

    @property
    def multiline(self):
        return NULL_HUSKER

    def map(self, function):
        return None

    def map_const(self, value):
        return None

    def then(self, function):
        return None

    def __str__(self):
        return '<Null>'

NULL_HUSKER = NullHusker()

#----------------------------------------------------------------------------------------------------------------------------------

class ElementHusker(Husker):

    def __init__(self, value, is_full_document=False):
        assert value is not None
        super(ElementHusker, self).__init__(value)
        self.is_full_document = is_full_document

    def __iter__(self):
        return iter(self.value)

    def __len__(self):
        return len(self.value)

    def __getitem__(self, item):
        value = self.value.attrib[item] # will raise KeyError
        return TextHusker(self._ensure_decoded(value))

    def attrib(self, item, default=NULL_HUSKER):
        try:
            return self[item]
        except KeyError:
            return default

    @property
    def children(self):
        return ListHusker(map(ElementHusker, self.value))

    def selection(self, path):
        xpath = self._compile_xpath(path)
        selected = ET.XPath(
            xpath,
            # you can use regexes in your paths, e.g. '//a[re:test(text(),"reg(?:ular)?","i")]'
            namespaces = {'re':'http://exslt.org/regular-expressions'},
        )(self.value)
        return ListHusker(
            husk(self._ensure_decoded(v))
            for v in selected
        )

    def _compile_xpath(self, path):
        if re.search(r'(?:^\.(?=/)|/|@|^\w+$)', path):
            return re.sub(
                r'^(\.?)(/{,2})',
                lambda m: '%s%s' % (
                    m.group(1) if self.is_full_document else '.',
                    m.group(2) or '//',
                ),
                path
            )
        else:
            return self._css_path_to_xpath(path)

    @staticmethod
    def _ensure_decoded(value):
        # lxml returns bytes when the data is ASCII, even when the input was text, which feels wrong but hey
        if isinstance(value, bytes_type):
            value = value.decode('us-ascii')
        return value

    @property
    def text(self):
        return TextHusker(normalize_spaces(''.join(self.value.itertext())))

    @property
    def multiline(self):
        return TextHusker(self._multiline_text())

    def _multiline_text(self):
        def visit(node, inside_pre=False):
            if node.tag == 'pre':
                inside_pre = True
            if node.tag == 'br':
                yield "\n"
            elif node.tag in self._PARAGRAPH_BREAKING_TAGS:
                yield "\n\n"
            if node.tag not in self._NON_TEXT_TAGS and not isinstance(node, ET._Comment):
                if node.text:
                    yield node.text if inside_pre else normalize_spaces(node.text)
                for child in node:
                    for value in visit(child, inside_pre):
                        yield value
            if node.tag in self._PARAGRAPH_BREAKING_TAGS:
                yield "\n\n"
            if node.tail:
                yield node.tail if inside_pre else normalize_spaces(node.tail)
        return TextHusker(re.sub(
            r'\s+',
            lambda m: "\n\n" if "\n\n" in m.group() else "\n" if "\n" in m.group() else " ",
            ''.join(visit(self.value)),
        ))

    def js(self, strip_comments=True):
        js = "\n".join(
            re.sub('^\s*<!--', '', re.sub('-->\s*$', '', js_text))
            for js_text in self.value.xpath('.//script/text()')
        )
        if strip_comments:
            js = strip_js_comments(js)
        return TextHusker(js)

    def detach(self, reattach_tail=True):
        detach_node(self.value, reattach_tail=reattach_tail)

    def repr_spec(self, path):
        xpath = self._compile_xpath(path)
        if path == xpath:
            return "'%s'" % path
        else:
            return "'%s' (compiled to '%s')" % (path, xpath)

    def repr_value(self):
        return 'etree:\n' + self.html_source()

    def html_source(self):
        return ET.tostring(
            self.value,
            pretty_print=True,
            method='HTML',
            encoding=text_type,
        )

    @staticmethod
    def _css_path_to_xpath(path):
        if CSSSelector is NotImplemented:
            raise NotImplementedError("lxml.cssselect module not found")
        return CSSSelector(path).path

    _PARAGRAPH_BREAKING_TAGS = frozenset((
        'address', 'applet', 'blockquote', 'body', 'center', 'cite', 'dd', 'div', 'dl', 'dt', 'fieldset', 'form', 'frame', 'frameset',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'head', 'hr', 'iframe', 'li', 'noscript', 'object', 'ol', 'p', 'table', 'tbody', 'td',
        'textarea', 'tfoot', 'th', 'thead', 'title', 'tr', 'ul',
    ))

    _NON_TEXT_TAGS = frozenset((
        'script', 'style',
    ))

#----------------------------------------------------------------------------------------------------------------------------------

class TextHusker(Husker):

    def __init__(self, value):
        assert value is not None
        super(TextHusker, self).__init__(value)

    def selection(self, regex, flags=''):
        regex = self._compile(regex, flags)
        selected = regex.finditer(self.value)
        if regex.groups < 2:
            return ListHusker(
                TextHusker(m.group(regex.groups))
                for m in selected
            )
        else:
            return ListHusker(
                ListHusker(TextHusker(g) for g in m.groups())
                for m in selected
            )

    def sub(self, regex, replacement, flags=''):
        return TextHusker(
            self._compile(regex, flags).sub(
                replacement,
                self.value,
            )
        )

    @property
    def text(self):
        return self

    @property
    def multiline(self):
        return self

    def repr_spec(self, regex, flags=''):
        return "%s%s" % (
            re.sub(r'^u?[\'\"](.*)[\'\"]$', r'/\1/', regex),
            flags,
        )

    def __add__(self, other):
        return TextHusker(self.value + other.value)

    def __bool__(self):
        return bool(self.value)

    def __str__(self):
        return self.value

    @staticmethod
    def _compile(regex, flags):
        if isinstance(regex, text_type):
            return re.compile(
                regex,
                reduce(
                    operator.or_,
                    (getattr(re, f.upper()) for f in flags),
                    0,
                ),
            )
        elif flags == '':
            return regex
        else:
            raise ValueError((regex, flags))

#----------------------------------------------------------------------------------------------------------------------------------

class ListHusker(Husker):

    def __init__(self, value):
        assert value is not None
        if not callable(getattr(value, '__len__', None)):
            value = list(value)
        super(ListHusker, self).__init__(value)

    def __iter__(self):
        return iter(self.value)

    def __len__(self):
        return len(self.value)

    def __getitem__(self, item):
        return self.value[item]

    def __bool__(self):
        return bool(self.value)

    def __add__(self, other):
        return ListHusker(self.value + other.value)

    def selection(self, test=None):
        if test is not None and not callable(test):
            spec = test
            test = lambda child: child.selection(spec)
        return ListHusker(
            child
            for child in self.value
            if test is None or test(child)
        )

    def dedup(self, key=None):
        seen = set()
        deduped = []
        for child in self.value:
            keyed = child if key is None else key(child)
            if keyed not in seen:
                seen.add(keyed)
                deduped.append(child)
        return ListHusker(deduped)

    def _mapped_property(name, cls=None):
        return property(lambda self: (cls or self.__class__)(
            getattr(child, name)
            for child in self.value
        ))

    def _mapped_operation(name, cls=None):
        def operation(self, *args, **kwargs):
            list_cls = cls or self.__class__
            return list_cls(
                getattr(child, name)(*args, **kwargs)
                for child in self.value
            )
        return operation

    text = _mapped_property('text')
    js = _mapped_operation('js')
    json = _mapped_operation('json')
    sub = _mapped_operation('sub')
    attrib = _mapped_operation('attrib')
    raw = _mapped_property('raw', cls=list)

    def map(self, function):
        return [function(element.raw) for element in self]

    def map_const(self, value):
        return value

    def then(self, function):
        return [function(element) for element in self]

    def filter(self, function):
        return ListHusker(
            element
            for element in self
            if function(element)
        )

    @property
    def raw(self):
        return [element.raw for element in self.value]

    def __str__(self):
        return repr(self.value)

EMPTY_LIST_HUSKER = ListHusker([])

#----------------------------------------------------------------------------------------------------------------------------------
# public utils

def husk(value):
    if isinstance(value, text_type):
        # NB this includes _ElementStringResult objects that lxml returns when your xpath ends in "/text()"
        return TextHusker(value)
    elif callable(getattr(value, 'xpath', None)):
        return ElementHusker(value)
    elif isinstance(value, (tuple, list, GeneratorType)):
        return ListHusker(value)
    elif value is None:
        return NULL_HUSKER
    else:
        # NB this includes undecoded bytes
        raise ValueError(repr(value))

#----------------------------------------------------------------------------------------------------------------------------------
