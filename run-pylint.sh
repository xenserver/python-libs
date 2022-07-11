#!/bin/bash

test -r xcp || ln -sf . xcp

if [[ -z $1 ]]; then
    pylint --rcfile=pylint.rc *.py xcp
else
    pylint --rcfile=pylint.rc $1
fi
