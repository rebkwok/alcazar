#!/bin/bash

set -e

cd $(dirname $0)
python -m unittest discover -f tests "$@"
