#!/usr/bin/env python3

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
import json

# alcazar
import alcazar

#----------------------------------------------------------------------------------------------------------------------------------

def run_sample():
    scraper = alcazar.Scraper()
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

#----------------------------------------------------------------------------------------------------------------------------------



