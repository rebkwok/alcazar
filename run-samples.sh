#!/bin/bash

cd $(dirname $0)

for sample_dir in samples/trains; do
    echo "Running $sample_dir ..."
    sample_name=$(basename "$sample_dir")

    # The disk cache is not reusable across Python2/3, frustratingly. If the cache is written in Python 2, unpickling the responses
    # fails in Python 3. Culprit seems to be the OrderedDict shim provided by urllib3. The pickled response includes an OrderedDict
    # object, but that shim is not runnable in Python 3. Unpickling tries to create a urllib3.OrderedDict object in a Python 3
    # environment, which crashes with "No module named 'dummy_thread'".
    #
    # So, the cache is per-version, unfortunately.
    cache_root="cache/"$(python -c 'import sys; print("python" + sys.version[0])')

    actual_output=$( \
        cd "$sample_dir"; \
        HTTP_CACHE_ROOT_PATH="$cache_root" \
            python -c "import $sample_name; $sample_name.run_sample()" \
    )
    status="$?"
    rm -f "$sample_dir"/*.pyc
    rm -rf "$sample_dir"/__pycache__/

    if [ "$status" != "0" ]; then
        echo $actual_output 1>&2
        exit 1
    fi

    expected_output=$(cat "$sample_dir/output.json")
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
