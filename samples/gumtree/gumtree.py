#!/usr/bin/env python3

#----------------------------------------------------------------------------------------------------------------------------------

# standards
from hashlib import sha256
import json
from os import path

# alcazar
from alcazar import Scraper

#----------------------------------------------------------------------------------------------------------------------------------

def fetch_items():
    scraper = Scraper(
        cache_root_path = path.join(path.dirname(__file__), 'cache'),
    )
    return scraper.scrape(
        'https://www.gumtree.com/for-sale/edinburgh/patio',
        lambda html: (
            {
                'title': item('.listing-title').str,
                'location': item('.listing-location').str,
                'num_photos': item('.listing-thumbnail li').text('^(\d+) images?$').int,
                'age_days': item('.//*[@data-q="listing-adAge"]').text('Ad posted (\d+) days? ago$').int,
            }
            for item in html('//ul[@data-q="naturalresults"]').all('./li')
            if item.text
        ),
    )

#----------------------------------------------------------------------------------------------------------------------------------

def main():
    items = tuple(fetch_items())
    json_output = json.dumps(
        items,
        indent=4,
        sort_keys=True,
    )
    print(json_output)
    hexdigest = sha256(json_output.encode('UTF-8')).hexdigest()
    assert hexdigest == '83ddc1b80e8918fd9ed3db1903b5947bfdc8b18f4a6b584b5b57a9a20bb9c05a', hexdigest

if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
