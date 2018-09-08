#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from contextlib import contextmanager
from datetime import datetime
from glob import glob
import gzip
from hashlib import md5
from os import environ, path
import subprocess
from shutil import copyfile, rmtree
from sys import argv, stderr, stdout, version_info
from tempfile import mkdtemp
from threading import Thread
from time import sleep
import webbrowser

# alcazar
import alcazar
import check_specimen

# more 2+3 compat
if version_info[0] == 2:
    input = raw_input

#----------------------------------------------------------------------------------------------------------------------------------

def run(root_dir, url, key):
    scraper = alcazar.Scraper()
    page = scraper.fetch(url)
    with temp_dir() as temp_dir_path:
        temp_file_path = lambda ext: path.join(temp_dir_path, '%s.%s' % (key, ext))
        write_gzip_file(
            temp_file_path('html.gz'), 
            page.response.text.encode('UTF-8'),
        )
        with open(temp_file_path('txt'), 'wb') as file_out:
            for line in [
                    "url: %s" % url,
                    "retrieved: %s" % datetime.now(),
                    ""
                    ]:
                file_out.write(line.encode('UTF-8') + b'\n')
        while True:
            with ParserThread.in_background(temp_file_path('html.gz')):
                webbrowser.open(url)
                run_editor(temp_file_path('txt'))
            done, category = conclude(temp_file_path)
            if done:
                if category:
                    save_specimen(root_dir, key, temp_file_path, category)
                else:
                    print("Discarded")
                break

def conclude(temp_file_path):
    if check_specimen.run(temp_file_path('html.gz'), silent=True):
        return True, 'passing'
    else:
        print("-" * 79)
        print("The file you saved does not match what ArticleParser outputs.")
        while True:
            print("Would you like to:")
            print()
            print("  F) Save the specimen as a failure of the algorithm")
            print("  R) Retry with the editor")
            print("  D) Discard this specimen")
            print()
            user_choice = str.upper(input("> ") or "")[:1]
            if user_choice == 'R':
                return False, None
            elif user_choice == 'F':
                return True, 'failing'
            elif user_choice == 'D':
                return True, None
            else:
                continue

def save_specimen(root_dir, key, temp_file_path, category):
    real_file_path = lambda ext: path.join(
        root_dir,
        category,
        '%s.%s' % (key, ext),
    )
    copyfile(
        temp_file_path('html.gz'),
        real_file_path('html.gz'),
    )
    with open(temp_file_path('txt'), 'rb') as file_in:
        write_gzip_file(
            real_file_path('txt.gz'),
            file_in.read().decode('UTF-8').encode('UTF-8'), # validate that it's UTF-8
        )
    print("Saved %s specimen %s" % (category, key))

def run_editor(text_file_path):
    subprocess.check_call([
        environ.get('EDITOR', 'emacsclient'),
        text_file_path,
    ])

#----------------------------------------------------------------------------------------------------------------------------------

class ParserThread(Thread):

    CLEAR_SCREEN = b"\x1b[2J\x1b[H"

    def __init__(self, html_file_path):
        super(ParserThread, self).__init__()
        self.html_file_path = html_file_path
        self.stop_requested = False

    def run(self):
        while not self.stop_requested:
            stdout.buffer.write(self.CLEAR_SCREEN)
            print(str(datetime.now()))
            check_specimen.run(self.html_file_path)
            sleep(1)
            
    def stop(self):
        self.stop_requested = True
        return self.join()

    @classmethod
    @contextmanager
    def in_background(cls, *args, **kwargs):
        thread = cls(*args, **kwargs)
        thread.start()
        try:
            yield
        finally:
            thread.stop()

#----------------------------------------------------------------------------------------------------------------------------------
# utils

@contextmanager
def temp_dir():
    # This would be tempfile.TemporaryDirectory but that's not available in 2.7
    dir_path = mkdtemp()
    try:
        yield dir_path
    finally:
        rmtree(dir_path)

def write_gzip_file(path, content):
    with gzip.open(path, 'wb') as file_out:
        file_out.write(content)

#----------------------------------------------------------------------------------------------------------------------------------

def main(selected_urls):
    root_dir = path.dirname(__file__)
    for url in selected_urls:
        key = md5(url.encode('UTF-8')).hexdigest()
        existing_files = glob(path.join(root_dir, '*', '%s.*' % key))
        if existing_files:
            print("%s exists - %s already fetched" % (existing_files[0], url))
        else:
            run(root_dir, url, key)

def _load_selected_urls():
    if len(argv) == 2:
        yield argv[1]
    elif len(argv) == 3 and argv[1] == '-i':
        url_list_file = argv[2]
        with open(url_list_file, 'rb') as file_in:
            for line in file_in:
                yield line.strip().decode('us-ascii')
    else:
        print("usage: %s <url>" % argv[0], file=stderr)
        print("       %s -i <urls.txt>" % argv[0], file=stderr)
        exit(2)

if __name__ == '__main__':
    main(_load_selected_urls())

#----------------------------------------------------------------------------------------------------------------------------------
