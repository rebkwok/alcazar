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
    json_url = scraper.scrape(
        'https://newsapi.org/s/google-news-api',
        parse=lambda page: page.link(
            page.js().one(r"url: '(/v2/top-headlines\?sources=google-news&apiKey=\w+)'")
        ),
    )
    news_urls = scraper.scrape(
        json_url,
        parse=lambda page: page.all('articles[*].url').str,
    )
    add.main(
        news_urls,
        collection='google-news',
    )


if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
