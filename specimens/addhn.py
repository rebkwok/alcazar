#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# alcazar
import alcazar
from . import add

#----------------------------------------------------------------------------------------------------------------------------------

def main():
    scraper = alcazar.Scraper()
    urls = scraper.scrape(
        'https://news.ycombinator.com/',
        parse=lambda page: [
            url.str
            for url in (
                item('.//a[@class="storylink"]/@href')
                for item in page('table.itemlist').all('tr.athing')
            )
            if url.some(r'^https?://')
        ],
    )
    add.main(
        urls,
        collection='hacker-news',
    )

if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
