#!/bin/bash

cd $(dirname $0)

for sample_dir in samples/trains; do
    script_name=$(basename "$sample_dir")
    sample_script="$sample_dir/$script_name.py"
    echo "Running $sample_script ..."

    actual_output=$("$sample_script")
    if [ "$?" != "0" ]; then
        echo $actual_output 1>&2
        exit 1
    fi

    expected_output=$(cat "$sample_dir/output.json")
    if [ "$actual_output" != "$expected_output" ]; then
        echo '--- expected output --------------------'
        echo "$expected_output"
        echo '--- actual output ----------------------'
        echo "$actual_output"
        echo '--- diff (expected left, actual right) -'
        diff <(echo "$expected_output") <(echo "$actual_output")
        echo '--- test failed ------------------------'
        exit 1
    fi
done
