#!/usr/bin/env python

#----------------------------------------------------------------------------------------------------------------------------------

# 2+3 compatibility
from __future__ import unicode_literals

# standards
import setuptools
from os import path

#----------------------------------------------------------------------------------------------------------------------------------

with open(path.join(path.dirname(__file__), 'README.md'), 'rb') as file_in:
    long_description = file_in.read().decode('UTF-8')

setuptools.setup(
    name='alcazar',
    version='0.2.0',
    author='Herv\u00e9 Saint-Amand',
    author_email='alcazar@saintamh.org',
    description='Web scraper framework',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/saintamh/alcazar/',
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'alcazar = alcazar.cli:main',
        ],
    },
    install_requires=[
        'lxml>=3',
        'cssselect>=1.0',
        'jmespath>=0.9.3',
        'requests>=2',
        'urllib3>=1.17',
    ],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'Topic :: Software Development :: Libraries',
    ],
)

#----------------------------------------------------------------------------------------------------------------------------------
