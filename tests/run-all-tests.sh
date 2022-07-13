#!/bin/bash
set -eE
set -o pipefail

TESTDIR=$(dirname $0)
PYTHONPATH="$TESTDIR"/.. pytest "$@"
