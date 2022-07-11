#!/bin/bash

if [ $# = 0 ]; then
    pylint --rcfile=pylint.rc *.py xcp
else
    pylint --rcfile=pylint.rc "$@"
fi
