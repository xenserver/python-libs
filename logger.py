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

"""Logging support with backwards compatibility for xelogging"""

import fcntl
import os
import os.path
import sys
import traceback
import logging
import logging.handlers


LOG = logging.getLogger()
LOG.setLevel(logging.NOTSET)
FORMAT = logging.Formatter(
        "%(levelname)- 9.9s[%(asctime)s] %(message)s",
        "%F %T")

def openLog(lfile, level=logging.INFO):
    """Add a new file target to be logged to"""

    try:
        # if lfile is a string, assume we need to open() it
        if isinstance(lfile, str):
            h = open(lfile, 'a')
            if h.isatty():
                handler = logging.StreamHandler(h)
            else:
                h.close()
                handler = logging.handlers.RotatingFileHandler(lfile,
                                                               maxBytes=2**31)
            old = fcntl.fcntl(handler.stream.fileno(), fcntl.F_GETFD)
            fcntl.fcntl(handler.stream.fileno(),
                        fcntl.F_SETFD, old | fcntl.FD_CLOEXEC)

        # or if it is not a string, assume its a file-like object
        else:
            handler = logging.StreamHandler(lfile)

    except Exception:
        if len(LOG.handlers):
            log("Error opening %s as a log output." % str(lfile))
        else:
            sys.stderr.write("Error opening %s as a log output." % str(lfile))
        return False

    handler.setFormatter(FORMAT)
    handler.setLevel(level)
    LOG.addHandler(handler)
    return True

def closeLogs():
    """Close all logs"""
    for h in LOG.handlers:
        LOG.removeHandler(h)
        h.close()

def logToStdout(level=logging.INFO):
    """Log to stdout"""
    return openLog(sys.stdout, level)

def logToStderr(level=logging.INFO):
    """Log to stderr"""
    return openLog(sys.stderr, level)

def logToSyslog(ident = os.path.basename(sys.argv[0]), level = logging.INFO, 
                facility = logging.handlers.SysLogHandler.LOG_USER):
    """Log to syslog"""
    if os.path.exists("/dev/log"):
        syslog = logging.handlers.SysLogHandler("/dev/log", facility)
    else:
        syslog = logging.handlers.SysLogHandler(('localhost', 
                                                 logging.handlers.SYSLOG_UDP_PORT), facility)
    syslog.setLevel(level)
    fmt = logging.Formatter(ident+" %(levelname)s: %(message)s")
    syslog.setFormatter(fmt)
    LOG.addHandler(syslog)

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

# export the standard logging calls at the module level

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

def critical(*al, **ad):
    """critical"""
    LOG.critical(*al, **ad)
