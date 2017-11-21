#!/usr/bin/env python3.5

#----------------------------------------------------------------------------------------------------------------------------------

# standards
import csv
from hashlib import sha256
import logging
from os import path
import re
from urllib.parse import urljoin

# alcazar
import alcazar

#----------------------------------------------------------------------------------------------------------------------------------

COLUMNS = [
    'Scheme',
    'Provider',
    'Contact',
    'Contact First Name',
    'Contact Middle Name',
    'Contact Last Name',
    'Telephone',
    'Email',
    'Website',
]

#----------------------------------------------------------------------------------------------------------------------------------

class LloydsRegisterScraper(alcazar.Scraper):

    cache_root_path = path.join(path.dirname(__file__), 'cache')

    def run(self):
        scheme_meta = self.scrape(
            'http://www.lr.org/en/utilities-building-assurance-schemes/uk-schemes/',
            self.parse_scheme_meta,
        )
        for scheme_name, scheme_url in scheme_meta:
            for search_url in self.scrape(scheme_url, self.parse_search_urls, scheme_name=scheme_name):
                yield from self.scrape(
                    search_url,
                    self.parse_scheme_rows,
                    scheme_name=scheme_name,
                )

    def parse_scheme_meta(self, page):
        for link_el in page.all('//a[./header[@class="promo-header"]]'):
            scheme_name = str(link_el.one('.//h2'))
            scheme_url = page.link(link_el['href'])
            yield scheme_name, scheme_url

    def parse_search_urls(self, page, scheme_name):
        try:
            return page.all(
                '//article[starts-with(@class, "promo")]'
                '//a[starts-with(@title, "Find")]'
                '/@href'
            ).map(page.link)
        except alcazar.HuskerMismatch:
            logging.warning("No search URL found for %r, skipped", scheme_name)
            return []

    def parse_scheme_rows(self, page, scheme_name):
        for company_el in page.all(
                '//div[@class="container"]'
                '/div[starts-with(@class,"accordion-list")]'
                '//article[starts-with(@class, "panel")]'
                ):
            yield from CompanyDataParser.parse_csv_rows(scheme_name, company_el)

#----------------------------------------------------------------------------------------------------------------------------------

class CompanyDataParser(object):

    @classmethod
    def parse_csv_rows(cls, scheme_name, company_el):
        base_data = dict(cls.extract_company_data(scheme_name, company_el))
        for full_name in cls.split_multiple_contact_names(base_data.get('Contact')):
            company_data = dict(base_data)
            company_data.update(cls.extract_first_and_last_names(full_name))
            yield [company_data.get(column,'') for column in COLUMNS]

    @classmethod
    def extract_company_data(cls, scheme_name, company_el):
        yield 'Scheme', scheme_name
        yield 'Provider', str(company_el.one('.//h3'))
        for item_el in company_el.one('.//ul[@class="list-style-b"]').selection('./li'):
            label_el = item_el.children[0]
            label_el.detach()
            yield str(label_el), str(item_el)

    @classmethod
    def split_multiple_contact_names(cls, raw_name):
        if raw_name:
            return [
                name.strip()
                for name in re.findall(r'(?:[^/\(]|\([^\)]+\))+', raw_name)
            ]
        else:
            return [raw_name]

    @classmethod
    def extract_first_and_last_names(cls, full_name):
        original_name = full_name
        if full_name:
            full_name = re.sub(r'^(?:Mr|Ms|Mrs|Miss)\.? ', '', full_name)
            full_name = re.sub(r'^[A-Z][A-Z]RS:? ', '', full_name)
            full_name = re.sub(r' [A-Z][A-Z]RS$', '', full_name)
            full_name = re.sub(r', (?:\w+ )?Manager.*', '', full_name)
        if not full_name \
                or re.search(r' (?:Team|Office|Ltd|Helpline)$', full_name, flags=re.I) \
                or re.search(r'[\(\):]', full_name) \
                or full_name == 'TBA':
            parts = ['', '', '']
        else:
            match = re.search(
                r'^(\S+)(?: (\w\.?|Woodcock|Godfrey))? ((?:de )?\S+)$',
                full_name,
                flags=re.I
            )
            if match:
                parts = match.groups()
            else:
                raise ValueError((original_name, full_name))
        yield 'Contact', full_name
        for key, value in zip(('First', 'Middle', 'Last'), parts):
            yield 'Contact %s Name' % key, value

#----------------------------------------------------------------------------------------------------------------------------------

def main():
    scraper = LloydsRegisterScraper()
    output_csv_file = path.join(path.dirname(__file__), 'out.csv')
    with open(output_csv_file, 'w', encoding='UTF-8') as file_out:
        writer = csv.writer(file_out)
        writer.writerow(COLUMNS)
        for row in scraper.run():
            writer.writerow(row)
    logging.info("Wrote %s", output_csv_file)
    with open(output_csv_file, 'rb') as file_in:
        hexdigest = sha256(file_in.read()).hexdigest()
    if hexdigest != '14946129ab82eeae2c641df3029c02365998302012d9e2ccb739f421728f556d':
        raise Exception(hexdigest)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()

#----------------------------------------------------------------------------------------------------------------------------------
