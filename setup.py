#!/usr/bin/env python

#----------------------------------------------------------------------------------------------------------------------------------

# 2+3 compatibility
from __future__ import unicode_literals

# standards
from distutils.core import setup

# 3rd parties
from pip.req import parse_requirements

#----------------------------------------------------------------------------------------------------------------------------------

setup(
    name='Alcazar',
    version='0.1',
    description='Alcazar web scraping library',
    author='Herv\u00e9 Saint-Amand',
    author_email='alcazar@saintamh.org',
    url='https://saintamh.org/code/alcazar/',
    packages=['alcazar'],
    install_requires=[
        'lxml>=3',
        'cssselect>=1.0',
        'jmespath>=0.9.3',
        'requests>=2',
        'urllib3>=1.17',
    ],
)

#----------------------------------------------------------------------------------------------------------------------------------
