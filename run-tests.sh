#!/bin/bash

# $Id: $
# Herve Saint-Amand
# Edinburgh

#------------------------------------------------------------------------------

cd $(dirname $0)

supported_versions=(2.7 3.3 3.4 3.5 3.6)
tested_versions=()
summary=""
exit_status=0

for v in ${supported_versions[@]}; do
    cmd="python$v"
    if [ $(which $cmd) ]; then
        full_version=$($cmd --version 2>&1 | sed 's/Python //')
        tested_versions+=($full_version)
        echo "Running tests for Python $full_version"
        $cmd -m unittest discover -f tests "$@"
        if [ "$?" == "0" ]; then
            summary_entry="pass"
        else
            summary_entry="FAIL"
            exit_status=1
        fi
        summary=$(printf "%s\n    %7s: %s" "$summary" "$full_version" "$summary_entry")
        if [ $exit_status == 1 ]; then
            break
        fi
    fi
done

echo ----------------------------------------------------------------------
echo -e "Summary for each Python version:\n$summary"

exit $exit_status

#------------------------------------------------------------------------------
