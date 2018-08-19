Alcazar is a Python library that simplifies the task of writing web scrapers.

Some of its core features are:

* *succinct syntax* for locating relevant data within an HTML page, JSON document, string of text
* *HTTP caching to disk* for exact replay of scrapes without resubmitting HTTP requests
* *Throttling* of requests to the same host
* *Crawler* facilities for maintaining a queue of URLs to visit
* *fail-fast by default*: by default, we'd rather crash than save incorrect or incomplete data

This project brings together the following libraries:

* [Requests](https://github.com/requests/requests)
* [lxml](https://lxml.de/)
* [JMESPath](http://jmespath.org/)

See the `samples` directory for a taste of how Alcazar works.
