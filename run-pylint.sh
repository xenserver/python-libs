#!/bin/bash

if [ $# = 0 ]; then
    pylint *.py xcp
else
    pylint "$@"
fi
