#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# 3rd parties
from record import Record, absolute_http_url, dict_of, nullable
import requests

# alcazar
from .utils.compatibility import bytes_type, text_type

#----------------------------------------------------------------------------------------------------------------------------------

# class ScraperRequest(Record):

#     url = text_type
#     method = nullable(text_type, default='GET')
#     headers = nullable(dict_of(text_type, text_type), default={})
#     data = nullable(bytes_type)

#     def compile(self):
#         return requests.Request(
#             url=self.url,
#             method=self.method,
#             headers=self.headers,
#             data=self.data,
#         )

#     def record_pods(self):
#         if self.method == 'GET' and not self.headers:
#             return self.url
#         else:
#             return super(ScraperRequest, self).record_pods()

#     @classmethod
#     def from_pods(cls, pods):
#         if not isinstance(pods, dict):
#             pods = {'url': pods}
#         return super(ScraperRequest, cls).from_pods(pods)

#----------------------------------------------------------------------------------------------------------------------------------
