#!/usr/bin/env python3

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
from decimal import Decimal
from hashlib import sha256
import json
from os import path

# alcazar
import alcazar
from alcazar.utils.compatibility import urlquote_plus

#----------------------------------------------------------------------------------------------------------------------------------

class Gumtree(alcazar.CatalogParser, alcazar.Scraper):

    cache_root_path = path.join(path.dirname(__file__), 'cache')

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
                .text('^£(\d+(?:,\d\d\d)*)\.00$')
                .sub(',', '')
                .int,
            'location': page('span[@itemprop="address"]').str,
            'age': item('.//*[@data-q="listing-adAge"]')
                .text('Ad posted (\d+ (?:second|minute|hour|day)s?) ago$')
                .str,
            'image_urls': page('div#vip-tabs-images').selection_of(
                './/img/@src',
                './/img/@data-lazy',
            ).str,
        }

#----------------------------------------------------------------------------------------------------------------------------------

def main():
    scraper = Gumtree()
    offers = tuple(scraper.search('edinburgh', 'coffee machine'))
    json_output = json.dumps(
        offers,
        indent=4,
        sort_keys=True,
        default=str,
    )
    print(json_output)
    hexdigest = sha256(json_output.encode('UTF-8')).hexdigest()
    assert hexdigest == '4a18656f93ee61b3bf5e60109a0d6cc457a00567dad594ba8fe8cf0275a6d966', hexdigest

if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
