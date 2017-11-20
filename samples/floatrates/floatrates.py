#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from decimal import Decimal
from os import path

# alcazar
import alcazar

#----------------------------------------------------------------------------------------------------------------------------------

def main():
    scraper = alcazar.Scraper(
        cache_root_path = path.join(path.dirname(__file__), 'cache'),
    )
    document = scraper.fetch('http://www.floatrates.com/daily/USD.xml')
    item = document(
        '/channel'
        + '/item[baseCurrency="USD" and targetCurrency="AUD"]'
        + '/exchangeRate'
    )
    rate = item.text.map(Decimal)
    floatrate = str(rate.quantize(Decimal('0.0001')))
    assert floatrate == '1.3229', repr(floatrate)

if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
