#!/bin/bash

set -e

python -m unittest discover -f tests "$@" \
    && bash ./run-samples.sh
