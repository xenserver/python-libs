#!/bin/bash

SITE_PACKAGE_NAME=xcp

if [[ ! -d "xcp" ]]; then
    mkdir $SITE_PACKAGE_NAME
fi

if [[ $EUID -ne 0 ]]; then
    echo "Must be run as root to bind mount"
    exit 2
fi


mount --bind ../../python-libs.hg $SITE_PACKAGE_NAME

if [[ $? -ne 0 ]]; then
    echo "Mount failed"
    exit 3
fi

python "$@"

umount $SITE_PACKAGE_NAME
rmdir $SITE_PACKAGE_NAME --ignore-fail-on-non-empty