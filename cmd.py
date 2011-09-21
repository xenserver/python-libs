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

"""Command processing"""

import subprocess

import xcp.logger as logger

def runCmd(command, with_stdout = False, with_stderr = False, inputtext = None):
    cmd = subprocess.Popen(command, bufsize = 1,
                           stdin = (inputtext and subprocess.PIPE or None),
                           stdout = subprocess.PIPE,
                           stderr = subprocess.PIPE,
                           shell = isinstance(command, str))

    (out, err) = cmd.communicate(inputtext)
    rv = cmd.returncode

    l = "ran %s; rc %d" % (str(command), rv)
    if inputtext:
        l += " with input %s" % inputtext
    if out != "":
        l += "\nSTANDARD OUT:\n" + out
    if err != "":
        l += "\nSTANDARD ERROR:\n" + err
    logger.debug(l)

    if with_stdout and with_stderr:
        return rv, out, err
    elif with_stdout:
        return rv, out
    elif with_stderr:
        return rv, err
    return rv

class OutputCache:
    def __init__(self):
        self.cache = {}

    def fileContents(self, fn):
        key = 'file:' + fn
        if key not in self.cache:
            logger.debug("Opening " + fn)
            f = open(fn)
            self.cache[key] = ''.join(f.readlines())
            f.close()
        return self.cache[key]

    def runCmd(self, command, with_stdout = False, with_stderr = False, inputtext = None):
        key = str(command) + str(inputtext)
        rckey = 'cmd.rc:' + key
        outkey = 'cmd.out:' + key
        errkey = 'cmd.err:' + key
        if rckey not in self.cache:
            (self.cache[rckey], self.cache[outkey], self.cache[errkey]) = \
                                runCmd(command, True, True, inputtext)
        if with_stdout and with_stderr:
            return self.cache[rckey], self.cache[outkey], self.cache[errkey]
        elif with_stdout:
            return self.cache[rckey], self.cache[outkey]
        elif with_stderr:
            return self.cache[rckey], self.cache[errkey]
        return self.cache[rckey]

    def clearCache(self):
        self.cache.clear()

if __name__ == '__main__':
    c = OutputCache()
    print c.fileContents('/tmp/foo')
    print c.fileContents('/tmp/foo')
    c.clearCache()
    print c.fileContents('/tmp/foo')
    print c.runCmd(['ls', '/tmp'], True)
    print c.runCmd(['ls', '/tmp'], True)
