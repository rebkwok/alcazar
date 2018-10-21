#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from argparse import ArgumentParser
from datetime import datetime
from glob import glob
import gzip
from hashlib import md5
from itertools import chain
from os import environ, makedirs, path, unlink
import re
import subprocess
from shutil import copyfile, copyfileobj, move as move_file, rmtree
from sys import argv, stderr, stdout, version_info
from traceback import print_exc
import webbrowser

# alcazar
from alcazar import MultiLineTextExtractor, Scraper, Skeleton, SkeletonItem
from alcazar.etree_parser import parse_html_etree
from . import check

# more 2+3 compat
if version_info[0] == 2:
    input = raw_input

#----------------------------------------------------------------------------------------------------------------------------------
# core

def save_html_to_temp_file(key, page):
    temp_html_file = file_path('temp', key, 'html.gz')
    html_str = page.response.text
    with gzip.open(temp_html_file, 'wb') as file_out:
        file_out.write(html_str.encode('UTF-8'))
    return html_str


def let_user_edit_skeleton(url, key, html_str):
    temp_html_file = file_path('temp', key, 'html.gz')
    temp_text_file = file_path('temp', key, 'txt')
    if not path.exists(temp_text_file):
        raw_skeleton = extract_raw_skeleton(url, parse_html_etree(html_str))
        with open(temp_text_file, 'wb') as file_out:
            for line in raw_skeleton.dump_to_lines():
                file_out.write(line.encode('UTF-8') + b'\n')
    while True:
        try:
            subprocess.check_call([
                environ.get('EDITOR', 'emacsclient'),
                temp_text_file,
            ])
            skeleton = check.load_reference_skeleton(temp_text_file)
            skeleton.validate()
        except (ValueError, subprocess.CalledProcessError):
            print_exc()
            input('Press enter to continue... ')
            continue
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
                return text


def extract_raw_skeleton(url, etree):
    items = [
        SkeletonItem('url', url),
        SkeletonItem('retrieved', str(datetime.now())),
    ] + [
        SkeletonItem('p', line)
        for line in MultiLineTextExtractor()(etree)
    ]
    return Skeleton.build(items)


def save_specimen(collection, key, skeleton_text):
    temp_html_file = file_path('temp', key, 'html.gz')
    real_html_file = file_path(collection, key, 'html.gz')
    real_skel_file = file_path(collection, key, 'skel.gz')
    move_file(
        temp_html_file,
        real_html_file,
    )
    with gzip.open(real_skel_file, 'wb') as file_out:
        file_out.write(skeleton_text.encode('UTF-8'))
    unlink(file_path('temp', key, 'txt'))
    print("Saved %s" % real_html_file)

#----------------------------------------------------------------------------------------------------------------------------------
# utils

def url_to_key(url):
    return md5(url.encode('UTF-8')).hexdigest()


def collection_path(collection):
    if collection == 'temp':
        return path.join(path.dirname(__file__), collection)
    else:
        return path.join(path.dirname(__file__), 'reference', collection)


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


def gunzip_file(from_gzipped_path, to_text_path):
    with gzip.open(from_gzipped_path, 'rb') as file_in:
        with open(to_text_path, 'wb') as file_out:
            copyfileobj(file_in, file_out)

#----------------------------------------------------------------------------------------------------------------------------------
# main
        
def main(inputs, collection, inputs_are_files=False, force_refresh=False):
    ensure_collection_dir_exists('temp')
    ensure_collection_dir_exists(collection)
    scraper = Scraper(
        user_agent='Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:62.0) Gecko/20100101 Firefox/62.0',
    )
    for url in iter_urls_from_args(inputs, inputs_are_files):
        key = url_to_key(url)
        existing_files = {
            re.sub(r'^[^\.]+\.', '', path.basename(f)): f
            for f in (
                glob(file_path(collection, key, '*'))
                or sorted(glob(file_path('*', key, '*')))
            )
        }
        if existing_files:
            if not force_refresh:
                print("%s exists - %s already fetched" % (existing_files['skel.gz'], url))
                continue
            else:
                gunzip_file(
                    existing_files['skel.gz'],
                    file_path('temp', key, 'txt'),
                )
                copyfile(existing_files['html.gz'], file_path('temp', key, 'html.gz'))
                with gzip.open(existing_files['html.gz'], 'rb') as file_in:
                    html_str = file_in.read().decode('UTF-8')
        else:
            page = scraper.fetch(url)
            html_str = save_html_to_temp_file(key, page)
        webbrowser.open(url, new=2)
        skeleton_text = let_user_edit_skeleton(url, key, html_str)
        save_specimen(collection, key, skeleton_text)


def iter_urls_from_args(inputs, inputs_are_files):
    if inputs_are_files:
        for urls_file_path in inputs:
            for url in load_urls_from_file(urls_file_path):
                yield url
    else:
        for url in inputs:
            yield url


def load_urls_from_file(urls_file_path):
    with open(urls_file_path, 'rb') as file_in:
        for line in file_in:
            line = re.sub(r'#.*', '', line.decode('us-ascii')).strip()
            if line:
                yield line


def parse_cmd_line():
    parser = ArgumentParser(description='Add one or more documents to the specimen corpus')
    parser.add_argument(
        'inputs',
        nargs='+',
    )
    parser.add_argument(
        '-i',
        '--input-file',
        dest='inputs_are_files',
        action='store_true',
        help='When present, the URLs are interpreted as paths to local files that must contain URLs, one per line',
    )
    parser.add_argument(
        '-f',
        '--force-refresh',
        dest='force_refresh',
        action='store_true',
        help="By default, URLs already in store won't be re-fetched; this option flips that",
    )
    parser.add_argument(
        '-c',
        '--collection',
        default='misc',
        help='Name of the collection under which to store the specimens',
    )
    return parser.parse_args()


if __name__ == '__main__':
    main(**parse_cmd_line().__dict__)

#----------------------------------------------------------------------------------------------------------------------------------
