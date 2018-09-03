#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import json

# alcazar
from alcazar import HttpClient

# tests
from .plumbing import FetcherFixture, ClientFixture, ServerFixture, compile_test_case_classes

#----------------------------------------------------------------------------------------------------------------------------------

class HeadersTestServer(object):

    def default(self):
        body = json.dumps({
            key.title(): value
            for key, value in self.headers.items()
        })
        return {
            'body': body.encode('UTF-8'),
            'headers': {'Content-Type': 'application/json'},
        }

    def redirect1(self):
        return {
            'body': b'redirect1',
            'status': 301,
            'headers': {
                'Set-Cookie': 'redirect1=yes',
                'Location': '/redirect2',
            },
        }

    def redirect2(self):
        return {
            'body': b'redirect2',
            'status': 301,
            'headers': {
                'Set-Cookie': 'redirect2=yes',
                'Location': '/landing',
            },
        }

    def landing(self):
        return {
            'body': b'landing',
            'status': 301,
            'headers': {
                'Set-Cookie': 'landing=yes',
            },
        }

#----------------------------------------------------------------------------------------------------------------------------------

class HeadersTests(object):

    __fixtures__ = [
        FetcherFixture.__subclasses__(),
        [ClientFixture],
        [ServerFixture],
    ]

    new_server = HeadersTestServer

    def test_default_accept(self):
        self.assertIn(
            'text/html',
            self.fetch().json().get('Accept', ''),
        )

    def test_default_accept_can_be_set_in_constructor(self):
        with HttpClient(headers={'Accept': 'something/else'}, logger=None) as client:
            self.assertEqual(
                'something/else',
                self.fetch(client=client).json().get('Accept', ''),
            )

    def test_default_accept_can_be_set_on_clientsession(self):
        with HttpClient(logger=None) as client:
            client.session.headers.update({'Accept': 'something/else'})
            self.assertEqual(
                'something/else',
                self.fetch(client=client).json().get('Accept', ''),
            )

    def test_default_accept_in_constructor_is_case_insensitive(self):
        with HttpClient(headers={'ACCEPT': 'something/else'}, logger=None) as client:
            self.assertEqual(
                'something/else',
                self.fetch(client=client).json().get('Accept', ''),
            )

    def test_default_accept_still_there_if_empty_dict_passed_to_constructor(self):
        with HttpClient(headers={}, logger=None) as client:
            self.assertIn(
                'text/html',
                self.fetch(client=client).json().get('Accept', ''),
            )

    def test_accept_can_be_set_per_request(self):
        response = self.fetch(
            headers={'Accept': 'something/else'},
        )
        self.assertEqual(
            'something/else',
            response.json().get('Accept', ''),
        )

    def test_accept_per_request_is_case_insensitive(self):
        response = self.fetch(
            headers={'ACCEPT': 'something/else'},
        )
        self.assertEqual(
            'something/else',
            response.json().get('Accept', ''),
        )

    def test_accept_can_be_set_per_request_even_when_constructor_sets_default(self):
        with HttpClient(headers={'Accept': 'something/else'}, logger=None) as client:
            response = self.fetch(
                client=client,
                headers={'Accept': 'something/other'},
            )
        self.assertEqual(
            'something/other',
            response.json().get('Accept', ''),
        )

    def test_accept_can_be_disabled_in_constructor_call(self):
        with HttpClient(headers={'Accept': None}, logger=None) as client:
            response = self.fetch(client=client)
        self.assertNotIn(
            'Accept',
            response.json(),
        )

    def test_accept_can_be_disabled_in_method_call(self):
        response = self.fetch(
            headers={'Accept': None}
        )
        self.assertNotIn(
            'Accept',
            response.json(),
        )

    def test_default_accept_encoding_header(self):
        self.assertIn(
            'gzip',
            self.fetch().json().get('Accept-Encoding', ''),
        )

    def test_custom_headers_get_case_normalized(self):
        response = self.fetch(headers={
            'X-ALCAZAR-test': 'whammo',
        })
        self.assertEqual(
            'whammo',
            # FIXME we don't know it's not the server normalising the header here
            response.json().get('X-Alcazar-Test', ''),
        )

    def test_default_user_agent_header(self):
        self.assertIn(
            'Alcazar',
            self.fetch().json().get('User-Agent', ''),
        )

    def test_can_set_user_agent(self):
        with HttpClient(user_agent='Shabang 3.4', logger=None) as client:
            self.assertEqual(
                'Shabang 3.4',
                self.fetch(client=client).json().get('User-Agent', ''),
            )

    def test_redirects_set_cookies_when_fetched_manually(self):
        self.assertEqual({}, dict(self.client.session.cookies))
        self.assertEqual(
            self.fetch('/redirect1', allow_redirects=False).text,
            'redirect1',
        )
        self.assertEqual(
            self.fetch('/redirect2', allow_redirects=False).text,
            'redirect2',
        )
        self.assertEqual(
            self.fetch('/landing', allow_redirects=False).text,
            'landing',
        )
        self.assertEqual(
            {
                'redirect1': 'yes',
                'redirect2': 'yes',
                'landing': 'yes',
            },
            dict(self.client.session.cookies),
        )

    def test_redirects_set_cookies_when_fetched_automatically(self):
        self.assertEqual({}, dict(self.client.session.cookies))
        self.assertEqual(
            self.fetch('/redirect1').text,
            'landing',
        )
        self.assertEqual(
            {
                'redirect1': 'yes',
                'redirect2': 'yes',
                'landing': 'yes',
            },
            dict(self.client.session.cookies),
        )

    def test_can_set_default_headers(self):
        self.client.default_headers['Something'] = 'Else'
        self.assertEqual(
            'Else',
            self.fetch().json().get('Something'),
        )

#----------------------------------------------------------------------------------------------------------------------------------

compile_test_case_classes(globals()) 

#----------------------------------------------------------------------------------------------------------------------------------
