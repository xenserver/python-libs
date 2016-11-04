#!/bin/bash

RES=0
for f in $(find . \( -path "./xcp" -prune \) -o -name "test*.py" -print)
do
    echo "Running $f"
    PYTHONPATH=.. python $f || RES=1
done
exit $RES
