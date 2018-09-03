#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# alcazar
import alcazar

# tests
from .plumbing import FetcherFixture, ClientFixture, ServerFixture, compile_test_case_classes

#----------------------------------------------------------------------------------------------------------------------------------

class HeadersTestServer(object):

    def default(self, status_code):
        headers = {}
        if 300 <= int(status_code) < 400:
            headers['Location'] = '/landing'
        return {
            'body': status_code.encode('UTF-8'),
            'status': int(status_code),
            'headers': headers,
        }

    def landing(self):
        return {'body': b'You have been redirected'}

#----------------------------------------------------------------------------------------------------------------------------------

class HeadersTests(object):

    __fixtures__ = [
        FetcherFixture.__subclasses__(),
        [ClientFixture],
        [ServerFixture],
    ]

    new_server = HeadersTestServer

    def test_200_raises_no_error(self):
        self.assertEqual(
            '200',
            self.fetch('/?status_code=200').text,
        )

    def test_301_raises_no_error_by_default(self):
        self.assertEqual(
            'You have been redirected',
            self.fetch('/?status_code=301').text,
        )

    def test_301_raises_no_error_when_simply_disabled(self):
        self.assertEqual(
            '301',
            self.fetch('/?status_code=301', allow_redirects=False).text,
        )

    def test_301_raises_httpredirect_when_not_allowed(self):
        with self.assertRaises(alcazar.HttpRedirect):
            self.fetch(
                '/?status_code=301',
                allow_redirects=False,
                auto_raise_for_redirect=True,
            )

    def test_307_raises_no_error_by_default(self):
        self.assertEqual(
            'You have been redirected',
            self.fetch('/?status_code=307').text,
        )

    def test_301_raises_no_error_when_simply_disabled(self):
        self.assertEqual(
            '307',
            self.fetch('/?status_code=307', allow_redirects=False).text,
        )

    def test_307_raises_httpredirect_when_not_allowed(self):
        with self.assertRaises(alcazar.HttpRedirect):
            self.fetch(
                '/?status_code=307',
                allow_redirects=False,
                auto_raise_for_redirect=True,
            )

    def test_httpredirect_is_an_httperror(self):
        with self.assertRaises(alcazar.HttpError):
            self.fetch(
                '/?status_code=307',
                allow_redirects=False,
                auto_raise_for_redirect=True,
            )

    def test_404_raises_httperror(self):
        with self.assertRaises(alcazar.HttpError):
            self.fetch('/?status_code=404')

    def test_404_raises_httperror404(self):
        with self.assertRaises(alcazar.HttpError.Http404):
            self.fetch('/?status_code=404')

#----------------------------------------------------------------------------------------------------------------------------------

compile_test_case_classes(globals()) 

#----------------------------------------------------------------------------------------------------------------------------------
