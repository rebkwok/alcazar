#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------

from __future__ import print_function, unicode_literals
import json

import alcazar

#----------------------------------------------------------------------------------------------------------------------------------

def run_sample():
    scraper = alcazar.Scraper()
    rate = scraper.scrape(
        'http://www.floatrates.com/daily/USD.xml',
        parse=lambda page: page.one(
            '/channel'
            '/item[baseCurrency="USD" and targetCurrency="AUD"]'
            '/exchangeRate'
        ).float,
    )
    print(json.dumps({"USDAUD": '%.04f' % rate}))

#----------------------------------------------------------------------------------------------------------------------------------
