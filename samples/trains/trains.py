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

    Train = namedtuple('Train', (
        'dep_time',
        'dep_platform',
        'arr_time',
        'arr_platform',
    ))

    def search(self, from_station, to_station, dep_datetime):
        return self.scrape(
            'http://ojp.nationalrail.co.uk/service/timesandfares/%s/%s/%s/%s/dep' % (
                from_station,
                to_station,
                dep_datetime.strftime ('%d%m%y'),
                dep_datetime.strftime ('%H%M'),
            ),
            self.parse_trains,
        )

    def parse_trains(self, page):
        for row in page('#oft').all('tbody tr.mtx'):
            yield self.Train(
                dep_time=row('.dep').datetime('%H:%M').time(),
                dep_platform=row.some('.from .ctf-plat').then(self.parse_platform),
                arr_time=row('.arr').datetime('%H:%M').time(),
                arr_platform=row.some('.to .ctf-plat').then(self.parse_platform),
            )

    def parse_platform(self, el):
        return el.text('^Platform (\w+)$').str

#----------------------------------------------------------------------------------------------------------------------------------

def main():
    dep_datetime = datetime(2017, 11, 21, 14, 0)
    all_trains = tuple(TrainTimesScraper().search('EDB', 'GLQ', dep_datetime))
    json_str = json.dumps(
        all_trains,
        indent=4,
        sort_keys=True,
        default=lambda v: v.strftime('%H:%M'),
    )
    print(json_str)
    hexdigest = sha256(json_str.encode('UTF-8')).hexdigest()
    assert hexdigest == '817e8f10016dee3661515070fed9c9e25449475bd0af2d61eaa8c699aa9b9910', hexdigest

if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
