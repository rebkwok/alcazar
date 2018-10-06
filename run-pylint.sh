#!/bin/bash

set -e

cd $(dirname $0)
pylint --rcfile=.pylintrc alcazar
# pylint --rcfile=.pylintrc specimens
