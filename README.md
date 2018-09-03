[![Build Status](https://travis-ci.org/saintamh/alcazar.svg?branch=master)](https://travis-ci.org/saintamh/alcazar)
[![PyPI version](https://badge.fury.io/py/alcazar.svg)](https://pypi.org/project/alcazar/)

Alcazar is a Python library that simplifies the task of writing web scrapers.

Some of its core features are:

* *succinct syntax* for locating relevant data within an HTML page, JSON document, string of text
* *HTTP caching to disk* for exact replay of scrapes without resubmitting HTTP requests
* *Throttling* of requests to the same host
* *Automatic retries* when an HTTP request fails, or when a page fails to parse as expected
* *Crawler* facilities for maintaining a queue of URLs to visit
* *fail-fast*: by default, we'd rather crash than save incorrect or incomplete data

Alcazar brings together the following libraries:

* [Requests](https://github.com/requests/requests)
* [lxml](https://lxml.de/) (including [cssselect](https://lxml.de/cssselect.html))
* [JMESPath](http://jmespath.org/)

Getting Started
===============

Alcazar is [available on PyPi](https://pypi.org/project/alcazar/) so it can be installed it using `pip`:

```
pip install alcazar
```

The simplest way to use the library is to instantiate a `Scraper` and call its `fetch` method:

```python
>>> import alcazar
>>> scraper = alcazar.Scraper()
>>> page = scraper.fetch('https://en.wikipedia.org/wiki/Gorgie')
>>> print(page.one('div[@id="toc"]/preceding-sibling::p[./b]').text.normalized)
Gorgie (/ˈɡɔːrɡiː/ GOR-gee) is a densely populated area of Edinburgh, Scotland. It is located in the west of the city and borders Murrayfield, Ardmillan and Dalry.
```

In this snippet:

* we've fetched the HTML for the page
  * if any network error or HTTP error happens, we'll retry to fetch it a few times, sleeping increasing delays between every attempt
* we've parsed the HTML into a tree
  * using lxml's excellent handling and recovery from "broken" HTML, as seen in the wild
* we've located the element we're interested in
  * here using an XPath expression, but we could've used a CSS selector too
  * we've checked that there was one and only one element that matched our query
  * else an exception would've been thrown, ensuring we capture only exactly what we wanted
* we've extracted its text, removed all tags from it, and normalized its whitespace

See the `samples` directory for a taste of how Alcazar works.
