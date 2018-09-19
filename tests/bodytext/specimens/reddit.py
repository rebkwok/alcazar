#!/usr/bin/env python3

# standards
from os import path

# alcazar
import alcazar


class RedditScraper(alcazar.Scraper):

    cache_root_path = path.join(
        path.dirname(__file__),
        '..',
        '..',
        '..',
        'cache',
    )

    params = {
        'rtj': 'debug',
        'redditWebClient': 'web2x',
        'app': 'web2x-client-production',
        'dist': '14',
        'layout': 'card',
        'sort': 'hot',
        'allow_over18': '',
        'include': '',
    }

    def __init__(self, subreddit):
        super().__init__()
        self.url = 'https://gateway.reddit.com/desktopapi/v1/subreddits/%s' % subreddit

    def run(self):
        params = dict(self.params)
        for page_num in range(8):
            page = self.fetch(self.compile_request(self.url, params=params))
            yield from page.all('posts | values(@)[?!isSponsored].source.url').str
            params['after'] = page('postIds').raw[-1]


def main():
    scraper = RedditScraper('news')
    for url in scraper.run():
        print(repr(url))


if __name__ == '__main__':
    main()
