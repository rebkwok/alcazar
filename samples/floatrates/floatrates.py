#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------

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
    print('1 USD = %.04f AUD' % rate)

#----------------------------------------------------------------------------------------------------------------------------------
