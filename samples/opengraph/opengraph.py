#!/usr/bin/env python

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
import json

# alcazar
import alcazar

#----------------------------------------------------------------------------------------------------------------------------------

def main():
    scraper = alcazar.Scraper(cache_root_path='cache')
    meta = scraper.scrape(
        'http://www.omgubuntu.co.uk/',
        parse=lambda page: dict(
            page.all('/html/head/meta[starts-with(@property, "og:")]')
                .map(lambda prop: (
                    prop['property'].sub('^og:', '').str,
                    prop['content'].str,
                ))
        ),
    )
    print(json.dumps(
        meta,
        indent=4,
        sort_keys=True,
    ))

if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------



