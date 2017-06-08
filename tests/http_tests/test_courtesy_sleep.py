#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# 3rd parties
import requests

# alcazar
from alcazar import HttpClient

# tests
from .plumbing import FetcherFixture, ClientFixture, ServerFixture, compile_test_case_classes

#----------------------------------------------------------------------------------------------------------------------------------

class CourtesySleepTestServer(object):

    def redirect(self):
        return {
            'body': b'', 
            'status': 301,
            'headers': {'Location': '/landing'},
        }

    def landing(self):
        return b'You got redirected'


def make_send_base_wrapper(send_base):
    def wrapper(prepared_request, **kwargs):
        if '.test' in prepared_request.url:
            response = requests.Response()
            response.status_code = 0
            return response
        else:
            return send_base(prepared_request, **kwargs)
    return wrapper


class CourtesySleepTestClient(HttpClient):

    def __init__(self, **kwargs):
        kwargs.setdefault('logger', None)
        super(CourtesySleepTestClient, self).__init__(**kwargs)
        adapter = self.session.adapters['http://']
        adapter._sleep = lambda seconds: setattr(self, 'actual_sleep', seconds)
        adapter.send_base = make_send_base_wrapper(adapter.send_base)

    def request(self, request, **kwargs):
        self.actual_sleep = 0
        return super(CourtesySleepTestClient, self).request(request, **kwargs)

#----------------------------------------------------------------------------------------------------------------------------------

class CourtesySleepTests(object):

    __fixtures__ = [
        FetcherFixture.__subclasses__(),
        [ClientFixture],
        [ServerFixture],
    ]

    new_server = CourtesySleepTestServer
    new_client = CourtesySleepTestClient

    def assertDidntSleep(self):
        return self.assertEqual(
            self.client.actual_sleep,
            0,
        )

    def assertDidSleep(self, expected=5):
        return self.assertLess(
            abs(self.client.actual_sleep - expected),
            0.5,
        )

    def test_no_courtesy_sleep_across_domains(self):
        self.fetch('http://a.test/')
        self.assertDidntSleep()
        self.fetch('http://b.test/')
        self.assertDidntSleep()
        self.fetch('http://c.test/')
        self.assertDidntSleep()

    def test_no_courtesy_sleep_across_hosts(self):
        self.fetch('http://a.example.test/')
        self.assertDidntSleep()
        self.fetch('http://b.example.test/')
        self.assertDidntSleep()
        self.fetch('http://c.example.test/')
        self.assertDidntSleep()

    def test_default_courtesy_sleep_same_domain(self):
        self.fetch('http://a.test/')
        self.assertDidntSleep()
        self.fetch('http://a.test/')
        self.assertDidSleep()
        self.fetch('http://a.test/')
        self.assertDidSleep()

    def test_default_courtesy_sleep_same_domain_diff_port(self):
        self.fetch('http://a.test/')
        self.assertDidntSleep()
        self.fetch('http://a.test:80/')
        self.assertDidSleep()
        self.fetch('http://a.test:81/')
        self.assertDidntSleep()
        self.fetch('http://a.test:82/')
        self.assertDidntSleep()

    def test_courtesy_sleep_remembers_last_request(self):
        all_urls = ('http://a.test/', 'http://b.test/', 'http://c.test/')
        for url in all_urls:
            self.fetch(url)
            self.assertDidntSleep()
        for url in all_urls:
            self.fetch(url)
            self.assertDidSleep()

    def test_redirect_works_as_expected(self):
        self.assertEqual(
            self.fetch('/redirect').text,
            'You got redirected',
        )
        self.assertDidntSleep()

    def test_set_courtesy_sleep_in_constructor(self):
        with self.alt_client(courtesy_seconds=10):
            self.fetch('http://a.test/')
            self.fetch('http://a.test/')
            self.assertDidSleep(10)

    def test_disable_courtesy_sleep_in_constructor_with_none(self):
        with self.alt_client(courtesy_seconds=None):
            self.fetch('http://a.test/')
            self.fetch('http://a.test/')
            self.assertDidntSleep()

    def test_disable_courtesy_sleep_in_constructor_with_zero(self):
        with self.alt_client(courtesy_seconds=0):
            self.fetch('http://a.test/')
            self.fetch('http://a.test/')
            self.assertDidntSleep()

    def test_set_courtesy_sleep_in_method(self):
        self.fetch('http://a.test/')
        self.fetch('http://a.test/', courtesy_seconds=12)
        self.assertDidSleep(12)

    def test_disable_courtesy_sleep_in_method_with_none(self):
        self.fetch('http://a.test/')
        self.fetch('http://a.test/', courtesy_seconds=None)
        self.assertDidntSleep()

    def test_disable_courtesy_sleep_in_method_with_zero(self):
        self.fetch('http://a.test/')
        self.fetch('http://a.test/', courtesy_seconds=0)
        self.assertDidntSleep()

#----------------------------------------------------------------------------------------------------------------------------------

compile_test_case_classes(globals())

#----------------------------------------------------------------------------------------------------------------------------------
