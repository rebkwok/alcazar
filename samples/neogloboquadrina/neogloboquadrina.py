#!/usr/bin/env python

import csv
from sys import stdout

import alcazar


def main():
    scraper = alcazar.Scraper(
        cache_root_path='cache',
    )
    page = scraper.fetch('http://www.ucmp.berkeley.edu/fosrec/Olson2.html')
    table = page.one('p[./a[@name="TABLE2"]]/following-sibling::table')
    writer = csv.writer(stdout)
    for row in table:
        writer.writerow([cell.text.normalized.str for cell in row])


if __name__ == '__main__':
    main()
