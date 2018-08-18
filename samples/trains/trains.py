#!/usr/bin/env python3

# standards
from collections import namedtuple
from datetime import datetime, timedelta
from hashlib import sha256
import json
from os import path

# alcazar
import alcazar

#----------------------------------------------------------------------------------------------------------------------------------

class TrainTimesScraper(alcazar.Scraper):

    cache_root_path = path.join(path.dirname(__file__), 'cache')

    Query = namedtuple('Query', (
        'from_station',
        'to_station',
        'dep_datetime',
    ))

    Train = namedtuple('Train', (
        'dep_time',
        'dep_platform',
        'arr_time',
        'arr_platform',
    ))

    def search(self, query):
        return self.scrape(
            'http://ojp.nationalrail.co.uk/service/timesandfares/%s/%s/%s/%s/dep' % (
                query.from_station,
                query.to_station,
                query.dep_datetime.strftime('%d%m%y'),
                query.dep_datetime.strftime('%H%M'),
            ),
            parse=self.parse_trains,
        )

    def parse_trains(self, page):
        parse_platform = lambda el: el.text(u'^Platform (\w+)$')
        for row in page('#oft').all('tbody tr.mtx'):
            yield self.Train(
                dep_time=row('.dep').datetime('%H:%M').time(),
                dep_platform=row.some('.from .ctf-plat').map(parse_platform).str,
                arr_time=row('.arr').datetime('%H:%M').time(),
                arr_platform=row.some('.to .ctf-plat').map(parse_platform).str,
            )

#----------------------------------------------------------------------------------------------------------------------------------

def main():
    query = TrainTimesScraper.Query(
        from_station='EDB',
        to_station='GLQ',
        dep_datetime=datetime(2017, 11, 21, 14, 0),
    )
    all_trains = tuple(TrainTimesScraper().search(query))
    print(json.dumps(
        {
            "query": query._asdict(),
            "trains": [
                train._asdict()
                for train in all_trains
            ],
        },
        indent=4,
        sort_keys=True,
        default=lambda v: v and v.strftime('%H:%M')
    ))

if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
