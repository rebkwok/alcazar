#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from glob import iglob

# alcazar
from . import check
from .add import file_path

#----------------------------------------------------------------------------------------------------------------------------------

def main():
    for html_file_path in sorted(iglob(file_path('*', '*', 'html.gz'))):
        skel_file_path = html_file_path.replace('.html.gz', '.skel.gz')
        print(html_file_path)
        is_same = check.run(
            html_file_path,
            skel_file_path,
        )
        print('Same' if is_same else 'Not same')


if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
