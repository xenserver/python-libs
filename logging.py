#!/usr/bin/env python
# Copyright (c) 2011 Citrix Systems, Inc. All use and distribution of this
# copyrighted material is governed by and subject to terms and conditions
# as licensed by Citrix Systems, Inc. All other rights reserved.
# Xen, XenSource and XenEnterprise are either registered trademarks or
# trademarks of Citrix Systems, Inc. in the United States and/or other 
# countries.

import datetime
import fcntl
import sys
import traceback

log_handles = []
timestamp = False

def openLog(lfile):
    if hasattr(lfile, 'name'):
        # file object
        log_handles.append(lfile)
    else:
        try:
            f = open(lfile, 'w', 1)
            log_handles.append(f)
            # set close-on-exec
            old = fcntl.fcntl(f.fileno(), fcntl.F_GETFD)
            fcntl.fcntl(f.fileno(), fcntl.F_SETFD, old | fcntl.FD_CLOEXEC)
        except:
            log("Error opening %s as a log output." % lfile)
            return False
    return True

def closeLogs():
    for fd in log_handles:
        if not fd.name.startswith('<'):
            fd.close()

def logToStderr():
    return openLog(sys.stderr)

def log(txt):
    """ Write txt to the log(s) """

    if timestamp:
        prefix = '[%s] ' % str(datetime.datetime.now().replace(microsecond=0))
        txt = prefix + txt
    txt += '\n'

    for fh in log_handles:
        fh.write(txt)
        fh.flush()

def logException(e):
    """ Formats exception and logs it """
    ex = sys.exc_info()
    err = traceback.format_exception(*ex)
    errmsg = "\n".join([ str(x) for x in e.args ])

    # print the exception args nicely
    log(errmsg)

    # now print the traceback
    for exline in err:
        log(exline)
