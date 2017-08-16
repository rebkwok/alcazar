#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from contextlib import contextmanager
import re

# 3rd parties
import requests

# alcazar
from .husker import Husker, TextHusker
from .scraper import Scraper
from .utils.compatibility import string_types, text_type

#----------------------------------------------------------------------------------------------------------------------------------
# data structures

class Query(object):

    def __init__(self, request, methods, extras):
        self.request = request
        # `methods` is a dict of method pointers, mapping action names (e.g. "parse") to method names (e.g. "parse_details_page").
        # The name must be that of a method of the crawler instance. The values are strings, not callable objects, so that
        # scheduler implementations have the possibility of serialising them, storing them to a DB, distributing them across
        # processes or hosts, etc.
        self.methods = methods
        self.extras = extras

    @property
    def url(self):
        return self.request.url

    def __repr__(self):
        return "Query(%r, %r, %r)" % (
            self.request,
            self.methods,
            self.extras,
        )


class Page(object):

    def __init__(self, query, response, husker):
        self.query = query
        self.response = response
        self.husker = husker

    @property
    def extras(self):
        return self.query.extras

    @property
    def url(self):
        return TextHusker(self.response.url)

    def __getattr__(self, attr):
        try:
            return getattr(self.husker, attr)
        except AttributeError:
            return super(Page, self).__getattr__(attr)

    def __repr__(self):
        return "Page(%r)" % (self.query,)


class SkipThisPage(Exception):
    pass

#----------------------------------------------------------------------------------------------------------------------------------
# scheduler

class Scheduler(object):
    """
    Every crawler uses a Scheduler, which stores and sorts the Query objects to be fetched
    """

    def add(self, query):
        raise NotImplementedError

    def add_all(self, queries):
        for query in queries:
            self.add(query)

    def pop(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    @property
    def empty(self):
        return len(self) == 0


class StackScheduler(Scheduler):
    """
    Very simple in-memory query scheduler. Pages are visited depth-first, i.e. LIFO, and the links extracted from any one given
    page are popped off the stack in the same order that they appear on the page.
    """

    def __init__(self):
        self.stack = []

    def add(self, query):
        self.stack.append(query)

    def add_all(self, queries):
        super(StackScheduler, self).add_all(reversed(queries))

    def pop(self):
        return self.stack.pop()

    def __len__(self):
        return len(self.stack)

#----------------------------------------------------------------------------------------------------------------------------------

class Crawler(Scraper):
    """
    A `Crawler` is a scraper that issues multiple requests, where the list of requests ultimately made depends on the data and
    isn't fully pre-programmed.
    """

    def __init__(self, scheduler=None):
        # NB this class saves some state on `self', so it is not thread-safe. When building a multithreaded crawler, each thread
        # must instantiate its own Crawler, and they can all share the same scheduler (or they can use a Scheduler implementation
        # that reads from a central database).
        self.scheduler = scheduler or StackScheduler()
        self.current_referer = self.current_link_batch = None

    def run(self):
        with self.page_context():
            self.start()
        while not scheduler.empty:
            query = scheduler.pop()
            with self.page_context(query):
                try:
                    # TODO presumably this is where auto-retry would fit
                    for payload in (self.crawl(query) or []):
                        yield payload
                except SkipThisPage as reason:
                    self.log_skipped_page(query, reason)

    @contextmanager
    def page_context(self, referer=None):
        assert self.current_referer is None, repr(self.current_referer)
        assert self.current_link_batch is None, repr(self.current_link_batch)
        self.current_referer = referer
        self.current_link_batch = []
        yield
        self.scheduler.add_all(self.current_link_batch)
        self.current_referer = self.current_link_batch = None

    def follow(self, request, **kwargs):
        forward_extras = kwargs.pop('forward_extras', True)
        request = self.compile_request(request, self.current_referer)
        methods, rest = self.compile_method_pointers(**kwargs)
        self.current_link_batch.append(Query(
            request=request,
            methods=methods,
            extras=self.compile_extras(forward_extras, rest),
        ))

    def compile_method_pointers(self, **kwargs):
        # NB as explained in the `Query` class above, these method "pointers" are just strings that name crawler methods
        methods = {}
        for action in ('crawl', 'fetch', 'parse', 'husk'):
            key = '%s_method' % action
            value = kwargs.pop(key, self.current_referer and self.current_referer.methods.get(key))
            if callable(value):
                # We allow passing in the methods as actual method objects, since that makes the code more explicit. However since
                # the pointer is stored as a name, we need to check that the method object is on `self', else the client code could
                # be misleading.
                name = value.__name__
                if value is not getattr(self.crawler, name, None):
                    raise ValueError("%s: %s is not crawler.%s" % (action, name, name))
                value = name
            if value is not None:
                if not callable(getattr(self.crawler, value, None)):
                    raise ValueError("crawler has no %s method" % (value,))
                methods[action] = value
        return methods, kwargs

    def compile_extras(self, forward_extras, rest):
        extras = {}
        if forward_extras:
            extras.update(self.referer.extras)
        extras.update(rest)
        return extras

    def log_skipped_page(self, query, reason):
        logging.info("Skipped %s (%s)", query, reason)

    def start(self):
        """
        A chance for subclasses to enqueue the first requests.
        """

    def crawl(self, query):
        """ Crawl is just fetch+parse. Subclases will not typically override this. """
        return getattr(self, query.methods.get('crawl', 'crawl_default'))(query)

    def fetch(self, query):
        """ Turns a Query into a Page. """
        return getattr(self, query.methods.get('fetch', 'fetch_default'))(query)

    def parse(self, page):
        """
        Takes a Page and yields a sequence that can either contain payload objects or further Queries to be added to the stack.
        """
        return getattr(self, page.query.methods.get('parse', 'parse_default'))(page)

    def husk(self, page):
        """ Takes a Page and returns husked parts for the `build` method. """
        return getattr(self, page.query.methods.get('husk', 'husk_default'))(page)

    def build(self, record_cls, parts):
        """ Instantiates the given `record_cls` using the given `parts` dict. Not typically overriden. """
        if not callable(getattr(parts, 'get', None)):
            parts = dict(parts)
        cleaned = {}
        for key, field in record_cls.record_fields.items():
            try:
                value = parts.get(key)
                if value is not None:
                    value = self.clean(key, field.type, value)
                cleaned[key] = value
            except Exception as exception:
                raise ValueError("Exception while cleaning %s:%r: %s" % (key, value, exception))
        return record_cls(**cleaned)

    def crawl_default(self, query):
        page = self.fetch(query)
        return self.parse(page)

    def fetch_default(self, query):
        response = self.fetch_response(query.request)
        return Page(
            query=query,
            response=response,
            husker=self.parse_html(response),
        )

    def parse_default(self, page):
        yield self.build(self.payload_type, self.husk(page))

    def husk_default(self, page):
        # If you've not overriden anything else in the chain above, you need to override this
        raise NotImplementedError(page)

#----------------------------------------------------------------------------------------------------------------------------------
