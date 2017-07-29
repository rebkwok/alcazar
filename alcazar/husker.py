#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from functools import reduce
from itertools import chain
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
from .utils.compatibility import PY2, bytes_type, native_string, text_type
from .utils.text import normalize_spaces

#----------------------------------------------------------------------------------------------------------------------------------
# excecptions

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
            raise HuskerMismatch('%s found no matches for %s in %r' % (self.id, self.repr_spec(*spec), str(self)))
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
            raise HuskerMismatch("%s: none of the specified specs matched: %s" % (
                self.id,
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

    def text(self, multiline=False):
        """ Returns a TextHusker with this husker's value, converted to a string. If `multiline` is true, preserve line breaks """
        raise NotImplementedError(repr(self))

    def json(self):
        return lenient_json_loads(self.text().raw())

    def raw(self):
        """
        Returns the underlying value. For ElementHusker instances, this would be an ETree Element; for TextHusker, a string; for
        ListHusker, a list; etc.
        """
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

    def __str__(self):
        return self.text().value

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.value)

    __hash__ = _forward_to_value('__hash__', int)
    __eq__ = _forward_to_value('__eq__', bool)
    __lt__ = _forward_to_value('__lt__', bool)
    __le__ = _forward_to_value('__le__', bool)
    __gt__ = _forward_to_value('__gt__', bool)
    __ge__ = _forward_to_value('__ge__', bool)

#----------------------------------------------------------------------------------------------------------------------------------

class ElementHusker(Husker):

    def __init__(self, value):
        assert value is not None
        super(ElementHusker, self).__init__(value)

    def __iter__(self):
        return iter(self.value)

    def __len__(self):
        return len(self.value)

    def __getitem__(self, item):
        value = self.get(item)
        if value is None:
            raise KeyError(item)
        return value

    def get(self, item, default=None):
        value = self._ensure_decoded(self.value.get(item, default))
        if value is None:
            return NULL_HUSKER
        else:
            return TextHusker(value)

    def selection(self, path):
        is_xpath = '/' in path or path == '.'
        xpath = path if is_xpath else self._css_path_to_xpath(path)
        selected = ET.XPath(
            xpath,
            # you can use regexes in your paths, e.g. '//a[re:test(text(),"reg(?:ular)?","i")]'
            namespaces = {'re':'http://exslt.org/regular-expressions'},
        )(self.value)
        return ListHusker(
            husk(self._ensure_decoded(v))
            for v in selected
        )

    @staticmethod
    def _ensure_decoded(value):
        # lxml returns bytes when the data is ASCII, even when the input was text, which feels wrong but hey
        if isinstance(value, bytes_type):
            value = value.decode('us-ascii')
        return value

    def text(self, multiline=False):
        if multiline:
            return TextHusker(self._multiline_text())
        else:
            return TextHusker(normalize_spaces(''.join(self.value.itertext())))

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

    def repr_spec(self, path):
        return "'%s'" % path

    def __str__(self):
        return '<%s element>' % self.value.tag

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

    def text(self, multiline=False):
        return self

    def repr_spec(self, regex, flags=''):
        return "%s%s" % (
            re.sub(r'^u?[\'\"](.*)[\'\"]$', r'/\1/', regex),
            flags,
        )

    def __add__(self, other):
        return TextHusker(self.value + other.value)

    def __str__(self):
        return self.value

    capitalize = _forward_to_value('capitalize', text_type)
    if not PY2:
        casefold = _forward_to_value('casefold', text_type)
    center = _forward_to_value('center', text_type)
    count = _forward_to_value('count', int)
    endswith = _forward_to_value('endswith', bool)
    find = _forward_to_value('find', int)
    format = _forward_to_value('format', text_type)
    format_map = _forward_to_value('format_map', text_type)
    index = _forward_to_value('index', int)
    isalnum = _forward_to_value('isalnum', bool)
    isalpha = _forward_to_value('isalpha', bool)
    isdecimal = _forward_to_value('isdecimal', bool)
    isdigit = _forward_to_value('isdigit', bool)
    if not PY2:
        isidentifier = _forward_to_value('isidentifier', bool)
    islower = _forward_to_value('islower', bool)
    isnumeric = _forward_to_value('isnumeric', bool)
    if not PY2:
        isprintable = _forward_to_value('isprintable', bool)
    isspace = _forward_to_value('isspace', bool)
    istitle = _forward_to_value('istitle', bool)
    isupper = _forward_to_value('isupper', bool)
    join = _forward_to_value('join', text_type)
    ljust = _forward_to_value('ljust', text_type)
    lower = _forward_to_value('lower', text_type)
    lstrip = _forward_to_value('lstrip', text_type)
    replace = _forward_to_value('replace', text_type)
    rfind = _forward_to_value('rfind', int)
    rindex = _forward_to_value('rindex', int)
    rjust = _forward_to_value('rjust', text_type)
    rsplit = _forward_to_value('rsplit', list)
    rstrip = _forward_to_value('rstrip', text_type)
    split = _forward_to_value('split', list)
    splitlines = _forward_to_value('splitlines', list)
    startswith = _forward_to_value('startswith', bool)
    strip = _forward_to_value('strip', text_type)
    swapcase = _forward_to_value('swapcase', text_type)
    title = _forward_to_value('title', text_type)
    translate = _forward_to_value('translate', text_type)
    upper = _forward_to_value('upper', text_type)
    zfill = _forward_to_value('zfill', text_type)

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

    def _mapped_operation(name, cls=None):
        def operation(self, *args, **kwargs):
            list_cls = cls or self.__class__
            return list_cls(
                getattr(child, name)(*args, **kwargs)
                for child in self.value
            )
        return operation

    text = _mapped_operation('text')
    js = _mapped_operation('js')
    json = _mapped_operation('json')
    sub = _mapped_operation('sub')
    raw = _mapped_operation('raw', cls=list)

EMPTY_LIST_HUSKER = ListHusker([])

#----------------------------------------------------------------------------------------------------------------------------------

class NullHusker(Husker):

    def __init__(self):
        super(NullHusker, self).__init__(None)

    def selection(self, *spec_ignored):
        return EMPTY_LIST_HUSKER

    def text(self, multiline=False):
        return NULL_HUSKER

NULL_HUSKER = NullHusker()

#----------------------------------------------------------------------------------------------------------------------------------
# private utils

JSON_FIXES = (
    ( # First of all, don't touch anything inside double quotes
        r'\" (?:\\.|[^\\\"])* \"',
        lambda s: s,
    ),
    ( # Replace single quotes with double quotes
        r'\' (?:\\.|[^\\\'])* \'',
        lambda s: '"%s"' % re.sub(
            r'(?:\\.|\")',
            lambda m: {
                '"': '\\"',
                "\\'": "'", # for some reason the json parser gets confused by a backslashed ' inside a " string
            }.get(m.group(), m.group()),
            s[1:-1]
        ),
    ),
    ( # Ensure that all hash property names are quoted
        r'(?<=[\{\,]) \s*\w+\s* (?=:)',
        lambda s: json.dumps(s.strip()),
    ),
    ( # [,,1] becomes [null,null,1]
        r'(?<=[\[\,]) (?=,)',
        lambda s: 'null',
    ),
    ( # Remove commas before closing brackets
        r'(?:,\s*)+ (?= \s*[\]\}])',
        lambda s: '',
    ),
)

RE_JSON_FIXES = re.compile(
    r'|'.join('(%s)' % f[0] for f in JSON_FIXES),
    re.X,
)


def lenient_json_loads(json_text):
    """
    Simply calls the standard library's json.loads, but applies a few simple fixes to the JSON code first, because the standard
    json module is stricter than I like it. In particular, this should be able to take a JavaScript Object literal and parse it
    like the JSON it almost is.

    Escape mania! You need to escape this docstring, which contains an a string passed to `parse_json', which contains an
    escaped strings of Javascript.
    >>> len('\\\\')
    1
    >>> lenient_json_loads("{a: 'a\\\\\\\\a'}")
    {u'a': u'a\\\\a'}
    """
    json_text = strip_js_comments(json_text)
    json_text = re.sub(
        r'(?:\\[^x]|\\x([0-9a-fA-F]{2}))',
        lambda m: chr(int(m.group(1),16)) if m.group(1) else m.group(),
        json_text
    )
    json_text = RE_JSON_FIXES.sub(
        lambda m: next(
            f[1](g)
            for f,g in zip(fixes, m.groups())
            if g is not None
        ),
        json_text
    )
    return json.loads(json_text)


def strip_js_comments(js):
    """
    Takes a string of JavaScript source code and returns the same code, with comments removed. Tries to be careful not to remove
    stuff that looks like comments but is inside a string literal

    >>> strip_js_comments ('var x = 10;')
    'var x = 10;'
    >>> strip_js_comments ('var x = /* 10 */ 20;')
    'var x =  20;'
    >>> strip_js_comments ('var x = 11; //10;')
    'var x = 11; '
    >>> strip_js_comments ('var x = "http//not-a-comment.com/despite-the-double-slash"; // a comment')
    'var x = "http//not-a-comment.com/despite-the-double-slash"; '
    >>> strip_js_comments ('var x = "/* This isnt a comment, it is a string literal */";')
    'var x = "/* This isnt a comment, it is a string literal */";'
    >>> strip_js_comments ('''var x = "A single apostrophe: '"; /* a comment */ var y = "Another apostrophe: '";''')
    'var x = "A single apostrophe: \\'";  var y = "Another apostrophe: \\'";'
    """

    # FIXME we don't do regex literals (couldn't figure out a complete regex for that). Hopefully shouldn't be a problem, because
    # it's hard to imagine how // or /* */ could fit in a regular expression (esp. since JS programmers must be aware of the case
    # where a regex contains */)

    return re.sub(re.compile('(?:%s)' % "|".join((
        r'(\" (?:\\.|[^\\\"])* \")', # matches and captures double-quoted strings
        r'(\' (?:\\.|[^\\\'])* \')', # matches and captures single-quoted strings
        r' // [^\n]*',               # matches (and does not capture) // comments
        r' /\* .*? \*/',             # matches (and does not capture) /* */ comments
    )), re.S|re.X), lambda m: m.group(1) or m.group(2) or '', js)

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
