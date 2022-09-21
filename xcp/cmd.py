# Copyright (c) 2013, Citrix Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Command processing"""

import subprocess
import six

import xcp.logger as logger

def runCmd(command, with_stdout = False, with_stderr = False, inputtext = None):
    cmd = subprocess.Popen(command, bufsize=1,
                           stdin=(inputtext and subprocess.PIPE or None),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           shell=isinstance(command, six.string_types))

    (out, err) = cmd.communicate(inputtext)
    rv = cmd.returncode

    l = "ran %s; rc %d" % (str(command), rv)
    if inputtext:
        l += " with input %s" % inputtext
    if out != "":
        l += "\nSTANDARD OUT:\n" + out
    if err != "":
        l += "\nSTANDARD ERROR:\n" + err

    for line in l.split('\n'):
        logger.debug(line)

    if with_stdout and with_stderr:
        return rv, out, err
    elif with_stdout:
        return rv, out
    elif with_stderr:
        return rv, err
    return rv

class OutputCache(object):
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
