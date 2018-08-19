#!/bin/bash

python -m unittest discover -f tests "$@" \
    && ./run-samples.sh
