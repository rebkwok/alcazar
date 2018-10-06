#!/usr/bin/env python
# -*- coding: utf-8 -*-

# For each test we spin up a tiny, transient HTTP server, to make requests against. Each TestCase class can define a RequestHandler
# that specifies how the server is to respond to calls for the test.

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from contextlib import contextmanager
from itertools import product
from random import randrange
import re
import socket
from threading import Event, Thread
from unittest import TestCase

# alcazar
from alcazar import HttpClient, Request
from alcazar.config import DEFAULT_CONFIG, ScraperConfig
from alcazar.utils.compatibility import PY2, BaseHTTPRequestHandler, HTTPServer, bytes_type, native_string, parse_qsl, urljoin

#----------------------------------------------------------------------------------------------------------------------------------
# HTTP server

# In order to test our HTTP client, we spin up a transient HTTP server for each test, and make calls against that.

class HTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        """
        This is called by HTTPServer. We parse the request, and delegate to the method with the same name as the root of the path,
        so a GET request to /hello will be handled by `self.hello()`.
        """
        match = re.search(r'/(\w*)(?:\?(.*))?$', self.path)
        if not match:
            raise ValueError(repr(self.path))
        method_name = match.group(1) or 'default'
        method_kwargs = dict(parse_qsl(match.group(2) or ''))
        # 2017-05-14 - can't say I'm in love with this hack
        self.handler.headers = self.headers
        method = getattr(
            self.handler,
            method_name,
            lambda: {'body': method_name.encode('ascii'), 'status': 404, 'reason': b'Not Here'},
        )
        response_parts = method(**method_kwargs)
        if isinstance(response_parts, bytes_type):
            response_parts = {'body': response_parts}
        self._send_response(**response_parts)

    do_POST = do_GET

    def _send_response(self, body, status=200, reason='OK', headers={}):
        self.send_response(status, reason)
        headers.setdefault('Content-Type', 'text/plain; charset=UTF-8')
        for key, values in headers.items():
            if not isinstance(values, list):
                values = [values]
            for value in values:
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        """
        We override the default implementation of this method, which prints to stderr and needlessly pollutes our log output.
        """


class HttpServerThread(Thread):
    """ Stoppable server thread. """

    def __init__(self, server):
        super(HttpServerThread, self).__init__()
        self.server = server
        self.start_event = Event()
        self.stop_event = Event()

    def start(self):
        super(HttpServerThread, self).start()
        self.start_event.wait()

    def run(self):
        self.server.timeout = 0.05
        while not self.stop_event.is_set():
            self.server.handle_request()
            self.start_event.set()
        self.server.server_close()

    def stop(self):
        self.stop_event.set()
        self.join()


class ServerFixture(object):

    @staticmethod
    def _setup_server(handler):
        num_attempts = 5
        for attempt in range(num_attempts):
            try:
                port = randrange(10000, 50000)
                server = HTTPServer(('0.0.0.0', port), type(
                    # this little beauty required because HTTPRequestHandler is instantiated for every request, but I want the
                    # RequestHandler instance to live through each individual test
                    native_string('HTTPRequestHandler'),
                    (HTTPRequestHandler, object),
                    {'handler': handler},
                ))
            except socket.error:
                if attempt == num_attempts-1:
                    raise
            else:
                return port, server

    def setUp(self):
        super(ServerFixture, self).setUp()
        self.handler = self.new_server()
        port, server = self._setup_server(self.handler)
        self.port = port
        self.thread = HttpServerThread(server)
        self.thread.start()

    def server_url(self, path='/'):
        return urljoin('http://localhost:%d/' % self.port, path)

    def tearDown(self):
        super(ServerFixture, self).tearDown()
        self.thread.stop()

#----------------------------------------------------------------------------------------------------------------------------------

# There's many ways to submit a request: you can call `client.get`, `client.post`, or `client.request`. This decorator allows
# a single test definition to test all of these.

class FetcherFixture(object):

    def url(self, url):
        if callable(getattr(self, 'server_url', None)):
            return self.server_url(url)
        else:
            return url

    def _build_request(self, **kwargs):
        request = Request(
            url=kwargs.pop('url'),
            data=kwargs.pop('data', None),
            headers=kwargs.pop('headers', {}),
            method=kwargs.pop('method'),
        )
        return request, kwargs


class GetReq(FetcherFixture):

    def fetch(self, url='/', **kwargs):
        client = kwargs.pop('client', self.client)
        kwargs['url'] = self.url(url)
        kwargs['method'] = 'GET'
        config = ScraperConfig.from_kwargs(kwargs)
        request, rest = self._build_request(**kwargs)
        return client.submit(request, config, **rest)


class PostReq(FetcherFixture):

    def fetch(self, url='/', **kwargs):
        client = kwargs.pop('client', self.client)
        kwargs['url'] = self.url(url)
        kwargs['data'] = b''
        kwargs['method'] = 'POST'
        config = ScraperConfig.from_kwargs(kwargs)
        request, rest = self._build_request(**kwargs)
        return client.submit(request, config, **rest)

#----------------------------------------------------------------------------------------------------------------------------------

class ClientFixture(object):

    courtesy_seconds = 0

    def cache(self):
        return None

    def new_client(self):
        return HttpClient(
            courtesy_seconds = self.courtesy_seconds,
            cache = self.cache(),
            logger = None,
        )

    def setUp(self):
        super(ClientFixture, self).setUp()
        self.client = self.new_client()

    def tearDown(self):
        super(ClientFixture, self).tearDown()
        self.client.close()

    @contextmanager
    def alt_client(self, **kwargs):
        prev_client = self.client
        with self.new_client(**kwargs) as alt_client:
            self.client = alt_client
            yield
        self.client = prev_client

#----------------------------------------------------------------------------------------------------------------------------------

class AlcazarTestCase(TestCase):

    if PY2:
        def assertRegex(self, *args, **kwargs):
            return self.assertRegexpMatches(*args, **kwargs)


def compile_test_case_classes(namespace):
    for symbol in tuple(namespace):
        if isinstance(namespace[symbol], type) \
                and hasattr(namespace[symbol], '__fixtures__'):
            test_class = namespace[symbol]
            for fixture_combo in product(*test_class.__fixtures__):
                name = '%s_%s' % (test_class.__name__, '_'.join(
                    fixture.__name__.replace('Fixture', '')
                    for fixture, siblings in zip(fixture_combo, test_class.__fixtures__)
                    if len(siblings) > 1
                ))
                assert name not in namespace, name
                namespace[native_string(name)] = type(
                    native_string(name),
                    (test_class,) + fixture_combo + (AlcazarTestCase,),
                    {}
                )

#----------------------------------------------------------------------------------------------------------------------------------
