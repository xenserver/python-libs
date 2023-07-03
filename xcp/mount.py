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

import os
import os.path
import tempfile

import xcp.cmd

class MountException(Exception):
    pass

def mount(dev, mountpoint, options = None, fstype = None, label = None):
    # type:(str, str, list[str] | None, str | None, str | None) -> None
    cmd = ['/bin/mount']
    if options:
        assert isinstance(options, list)

    if fstype:
        cmd += ['-t', fstype]

    if options:
        cmd += ['-o', ",".join(options)]

    if label:
        cmd += ['-L', "%s" % label]
    else:
        assert dev
        cmd.append(dev)
    cmd.append(mountpoint)

    rc, out, err = xcp.cmd.runCmd(cmd, with_stdout=True, with_stderr=True)
    if rc != 0:
        raise MountException("out: '%s' err: '%s'" % (out, err))

def bindMount(source, mountpoint):
    cmd = [ '/bin/mount', '--bind', source, mountpoint]
    rc, out, err = xcp.cmd.runCmd(cmd, with_stdout=True, with_stderr=True)
    if rc != 0:
        raise MountException("out: '%s' err: '%s'" % (out, err))

def umount(mountpoint, force = False):
    # -d option also removes the loop device (if present)
    cmd = ['/bin/umount', '-d']
    if force:
        cmd.append('-f')
    cmd.append(mountpoint)

    return xcp.cmd.runCmd(cmd)

class TempMount(object):
    def __init__(self, device, tmp_prefix, options = None, fstype = None,
                 label = None):
        self.mounted = False
        self.mount_point = tempfile.mkdtemp(dir = "/tmp", prefix = tmp_prefix)
        try:
            mount(device, self.mount_point, options, fstype, label)
        except:
            os.rmdir(self.mount_point)
            raise
        self.mounted = True

    def unmount(self):
        if self.mounted:
            umount(self.mount_point, True)
            self.mounted = False
        if os.path.isdir(self.mount_point):
            os.rmdir(self.mount_point)
