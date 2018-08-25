#!/usr/bin/env python
# -*- coding: utf-8 -*-

import alcazar


def main():
    scraper = alcazar.Scraper(cache_root_path='cache')
    rate = scraper.scrape(
        'http://www.floatrates.com/daily/USD.xml',
        parse=lambda page: page.one(
            '/channel'
            '/item[baseCurrency="USD" and targetCurrency="AUD"]'
            '/exchangeRate'
        ).float,
    )
    print('1 USD = %.04f AUD' % rate)


if __name__ == '__main__':
    main()
