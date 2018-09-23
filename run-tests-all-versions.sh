#!/bin/bash

# $Id: $
# Herve Saint-Amand
# Edinburgh

#------------------------------------------------------------------------------

function python_full_version {
    cmd="$1"
    "$cmd" --version 2>&1 | sed 's/Python //'
}

#------------------------------------------------------------------------------

cd $(dirname $0)

supported_versions=(2.7 3.3 3.4 3.5 3.6)
tested_versions=()
summary=""
exit_status=0

./run-pylint.sh || exit "$?"

for v in ${supported_versions[@]}; do
    cmd="python$v"
    if [ $(which $cmd) ]; then
        full_version=$(python_full_version "$cmd")
        tested_versions+=($full_version)
        echo "### Python $full_version"

        # setup virtualenv
        venv_dir="venv-tests-$v"
        if [ ! -d "$venv_dir" ]; then
            virtualenv --python=$(which "$cmd") "$venv_dir"
        fi
        . "$venv_dir/bin/activate"
        if [ $(python_full_version 'python') != "$full_version" ]; then
            echo "virtualenv not properly setup"
            "$cmd" --version
            python --version
            exit 3
        fi
        (pip install -e . || exit "$?") \
            | grep -v '^\(Cleaning up\|Requirement already satisfied\)'

        # run the tests
        ./run-tests.sh
        if [ "$?" == "0" ]; then
            summary_entry="pass"
        else
            summary_entry="FAIL"
            exit_status=1
        fi
        summary=$(printf "%s\n    %7s: %s" "$summary" "$full_version" "$summary_entry")

        # clean up
        deactivate
        if [ $exit_status == 1 ]; then
            break
        fi
    fi
done

echo ----------------------------------------------------------------------
echo -e "Summary for each Python version:\n$summary"

exit $exit_status

#------------------------------------------------------------------------------
