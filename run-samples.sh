#!/bin/bash

cd $(dirname $0)

for sample_dir in samples/*; do
    echo "Running $sample_dir ..."
    sample_name=$(basename "$sample_dir")

    actual_output=$(cd "$sample_dir"; ls -l cache; python "$sample_name.py")
    if [ "$?" != "0" ]; then
        echo $actual_output 1>&2
        exit 1
    fi

    expected_output=$(cat "$sample_dir"/output.*)
    diff=$(diff --ignore-all-space <(echo "$expected_output") <(echo "$actual_output"))

    if [ "$diff" ]; then
        echo '--- expected output --------------------'
        echo "$expected_output"
        echo '--- actual output ----------------------'
        echo "$actual_output"
        echo '--- diff (expected left, actual right) -'
        echo "$diff"
        echo '--- test failed ------------------------'
        exit 1
    fi
done
