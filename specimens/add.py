#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from datetime import datetime
from glob import glob
import gzip
from hashlib import md5
from os import environ, makedirs, path, unlink
import subprocess
from shutil import move as move_file, rmtree
from sys import argv, stderr, stdout, version_info
import webbrowser

# alcazar
from alcazar import MultiLineTextExtractor, Scraper, Skeleton, SkeletonItem
import check

# more 2+3 compat
if version_info[0] == 2:
    input = raw_input

#----------------------------------------------------------------------------------------------------------------------------------
# core

def save_html_to_temp_file(key, page):
    temp_html_file = file_path('temp', key, 'html.gz')
    with gzip.open(temp_html_file, 'wb') as file_out:
        file_out.write(page.response.text.encode('UTF-8'))
    return temp_html_file


def save_skeleton(url, key, page, temp_html_file):
    temp_text_file = file_path('temp', key, 'txt')
    if not path.exists(temp_text_file):
        raw_skeleton = extract_raw_skeleton(url, etree=page.husker.raw)
        with open(temp_text_file, 'wb') as file_out:
            for line in raw_skeleton.dump_to_lines():
                file_out.write(line.encode('UTF-8') + b'\n')
    while True:
        subprocess.check_call([
            environ.get('EDITOR', 'emacsclient'),
            temp_text_file,
        ])
        check.run(
            temp_html_file,
            temp_text_file,
        )
        if input('Save? [y/N] ').strip().lower().startswith('y'):
            try:
                with open(temp_text_file, 'rb') as file_in:
                    text = file_in.read().decode('UTF-8')
            except UnicodeError:
                print("File is not UTF-8. Save again")
            else:
                return temp_text_file, text


def extract_raw_skeleton(url, etree):
    items = [
        SkeletonItem('url', url),
        SkeletonItem('retrieved', str(datetime.now())),
    ] + [
        SkeletonItem('p', line)
        for line in MultiLineTextExtractor()(etree)
    ]
    return Skeleton.build(items)


def save_specimen(collection, key, temp_html_file, temp_text_file, skeleton_text):
    real_html_file = file_path(collection, key, 'html.gz')
    real_skel_file = file_path(collection, key, 'skel.gz')
    move_file(
        temp_html_file,
        real_html_file,
    )
    with gzip.open(real_skel_file, 'wb') as file_out:
        file_out.write(skeleton_text.encode('UTF-8'))
    unlink(temp_text_file)
    print("Saved %s" % real_html_file)

#----------------------------------------------------------------------------------------------------------------------------------
# utils

def url_to_key(url):
    return md5(url.encode('UTF-8')).hexdigest()


def collection_path(collection):
    return path.join(
        path.dirname(__file__),
        collection,
    )


def file_path(collection, key, extension):
    return path.join(
        collection_path(collection),
        '%s.%s' % (key, extension),
    )


def ensure_collection_dir_exists(collection):
    dir_path = collection_path(collection)
    if not path.isdir(dir_path):
        makedirs(dir_path)


def write_gzip_file(path, content):
    with gzip.open(path, 'wb') as file_out:
        file_out.write(content)

#----------------------------------------------------------------------------------------------------------------------------------
# main
        
def main(collection, selected_urls):
    ensure_collection_dir_exists('temp')
    ensure_collection_dir_exists(collection)
    scraper = Scraper()
    for url in selected_urls:
        key = url_to_key(url)
        existing_files = glob(file_path(collection, key, '*'))
        if existing_files:
            print("%s exists - %s already fetched" % (existing_files[0], url))
            continue
        page = scraper.fetch(url)
        temp_html_file = save_html_to_temp_file(key, page)
        webbrowser.open(url, new=2)
        temp_text_file, skeleton_text = save_skeleton(url, key, page, temp_html_file)
        save_specimen(collection, key, temp_html_file, temp_text_file, skeleton_text)


def parse_cmd_line():
    if len(argv) == 3:
        collection = argv[1]
        selected_urls = [argv[2]]
    elif len(argv) == 4 and argv[2] == '-i':
        collection = argv[1]
        url_list_file = argv[3]
        with open(url_list_file, 'rb') as file_in:
            selected_urls = [
                line.strip().decode('us-ascii')
                for line in file_in
            ]
    else:
        print("usage: %s <collection> <url>" % argv[0], file=stderr)
        print("       %s <collection> -i <urls.txt>" % argv[0], file=stderr)
        exit(2)
    main(collection, selected_urls)


if __name__ == '__main__':
    parse_cmd_line()

#----------------------------------------------------------------------------------------------------------------------------------
