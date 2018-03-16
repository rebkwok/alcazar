#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from os import path

# alcazar
import alcazar

#----------------------------------------------------------------------------------------------------------------------------------

def main():
    scraper = alcazar.Scraper(
        cache_root_path = path.join(path.dirname(__file__), 'cache'),
    )
    rate = scraper.scrape(
        'http://www.floatrates.com/daily/USD.xml',
        parse=lambda page: page.one(
            '/channel'
            '/item[baseCurrency="USD" and targetCurrency="AUD"]'
            '/exchangeRate'
        ).float,
    )
    assert '%.4f' % rate == '1.3238', repr(rate)
    print('1 USD = %.04f AUD' % rate)

if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
