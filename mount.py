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

import os
import os.path
import subprocess
import tempfile

import xcp.cmd
import xcp.logger as logger

class MountException(Exception):
    pass

def mount(dev, mountpoint, options = None, fstype = None, label = None):
    cmd = ['/bin/mount']
    if options:
        assert type(options) == list

    if fstype:
        cmd += ['-t', fstype]

    if options:
        cmd += ['-o', ",".join(options)]

    if label:
        cmd += ['-L', "%s" % label]
    else:
        assert(dev)
        cmd.append(dev)
    cmd.append(mountpoint)

    rc, out, err = xcp.cmd.runCmd(cmd, with_stdout=True, with_stderr=True)
    if rc != 0:
        raise MountException, "out: '%s' err: '%s'" % (out, err)

def bindMount(source, mountpoint):
    cmd = [ '/bin/mount', '--bind', source, mountpoint]
    rc, out, err = xcp.cmd.runCmd(cmd, with_stdout=True, with_stderr=True)
    if rc != 0:
        raise MountException, "out: '%s' err: '%s'" % (out, err)

def umount(mountpoint, force = False):
    # -d option also removes the loop device (if present)
    cmd = ['/bin/umount', '-d'] 
    if force:
        cmd.append('-f')
    cmd.append(mountpoint)

    rc = xcp.cmd.runCmd(cmd)
    return rc

class TempMount(object):
    def __init__(self, device, tmp_prefix, options = None, fstype = None, label = None):
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
