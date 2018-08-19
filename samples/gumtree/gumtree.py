#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
import json

# alcazar
import alcazar
from alcazar.utils.compatibility import urlquote_plus

#----------------------------------------------------------------------------------------------------------------------------------

class Gumtree(alcazar.CatalogParser, alcazar.Scraper):

    cache_root_path = 'cache'

    item_request_path = './/a[not(contains(@style, "display: none"))]/@href'
    result_list_path = 'main#fullListings'
    result_item_path = './/li/article[@itemtype="http://schema.org/Product"]'
    no_results_apology_path = '//h1[starts-with(text(), "0 ads for ")]'
    expected_total_items_path = '//h1[re:test(text(), "^(\d+) ads? for ")]'
    next_page_request_path = 'li[@class="pagination-next"]//a/@href'

    def search(self, location, search_term):
        return self.scrape_catalog([
            'https://www.gumtree.com/for-sale/%s/%s' % (
                urlquote_plus(location),
                urlquote_plus(search_term),
            ),
        ])

    def parse_catalog_item(self, page, item):
        return {
            'url': page.url,
            'title': item('.listing-title').str,
            'description': page('p.ad-description').multiline.str,
            'price_gbp': page('strong.ad-price')
                .text('^£(\d+(?:,\d\d\d)*\.\d\d)$')
                .sub(',', '')
                .decimal,
            'location': page('span[@itemprop="address"]').str,
            'age': item('.//*[@data-q="listing-adAge"]')
                .text('Ad posted (\d+ (?:second|minute|hour|day)s?) ago$')
                .str,
            'image_urls': page.js()
                .one(r'imageUrls\s*:\s*\[(.*?)\]')
                .selection(r'https?://[^\"]+')
                .str,
        }

#----------------------------------------------------------------------------------------------------------------------------------

def main():
    scraper = Gumtree()
    offers = tuple(scraper.search('edinburgh', 'coffee machine'))
    print(json.dumps(
        offers,
        indent=4,
        sort_keys=True,
        default=str,
    ))

if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
