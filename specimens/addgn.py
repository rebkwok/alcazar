#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
import random
import re
from sys import argv

# alcazar
import alcazar
from . import add

#----------------------------------------------------------------------------------------------------------------------------------

ALL_FEED_IDS = [
    'google-news',
    'google-news-ar',
    'google-news-au',
    'google-news-br',
    'google-news-ca',
    'google-news-fr',
    'google-news-in',
    'google-news-it',
    'google-news-ru',
    'google-news-uk',

    # Excluding these two because frankly I'm not qualified to build the skeleton files for right-to-left languages.
    #'google-news-is',
    #'google-news-sa',
]

#----------------------------------------------------------------------------------------------------------------------------------

def main(feed_id=None):
    if feed_id is None:
        feed_id = random.choice(ALL_FEED_IDS)
    scraper = alcazar.Scraper()
    json_url = scraper.scrape(
        'https://newsapi.org/s/%s-api' % feed_id,
        parse=lambda page: page.link(
            page.js().one(r"url: '(/v2/top-headlines\?sources=%s&apiKey=\w+)'" % re.escape(feed_id))
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
    main(*argv[1:])

#----------------------------------------------------------------------------------------------------------------------------------
