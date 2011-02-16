#!/usr/bin/env python
# Copyright (c) 2011 Citrix Systems, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; version 2.1 only. with the special
# exception on linking described in file LICENSE.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

"""Logging support with backwards compatability for xelogging"""

import fcntl
import sys
import traceback
import logging
import logging.handlers


LOG = logging.getLogger()
LOG.setLevel(logging.INFO)
FORMAT = logging.Formatter(
        "%(levelname)- 9.9s[%(asctime)s] %(message)s")

def openLog(lfile):
    """Add a new file target to be logged too"""
    if hasattr(lfile, 'name'):
        LOG.addHandler(logging.StreamHandler(lfile))
    else:
        try:
            handler = logging.FileHandler(lfile)
            old = fcntl.fcntl(handler.stream.fileno(), fcntl.F_GETFD)
            fcntl.fcntl(handler.stream.fileno(),
                        fcntl.F_SETFD, old | fcntl.FD_CLOEXEC)
            handler.setFormatter(FORMAT)
            LOG.addHandler(handler)
        except Exception:
            log("Error opening %s as a log output." % lfile)
            return False
    return True

def closeLogs():
    """Close all logs"""
    for h in LOG.handlers:
        LOG.removeHandler(h)

def logToStderr():
    """Log to stderr"""
    return openLog(sys.stderr)

def log(txt):
    """ Write txt to the log(s) """
    LOG.info(txt)

def logException(e):
    """ Formats exception and logs it """
    ex = sys.exc_info()
    err = traceback.format_exception(*ex)
    errmsg = "\n".join([ str(x) for x in e.args ])

    LOG.critical(errmsg)
    LOG.critical(err)

# export the standard logging calles at the module level

def debug(*al, **ad):
    """debug"""
    LOG.debug(*al, **ad)

def info(*al, **ad):
    """info"""
    LOG.info(*al, **ad)

def warning(*al, **ad):
    """warning"""
    LOG.warning(*al, **ad)

def error(*al, **ad):
    """error"""
    LOG.error(*al, **ad)

def criticial(*al, **ad):
    """critical"""
    LOG.critical(*al, **ad)
