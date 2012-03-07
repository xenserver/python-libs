#!/usr/bin/env python
# Copyright (c) 2012 Citrix Systems, Inc.
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

"""
Python function using 'ip' for convenience
"""

__version__ = "1.0.1"
__author__ = "Andrew Cooper"

from subprocess import Popen, PIPE

from xcp.logger import LOG

# Deal with lack of environment more sensibly than hard coding /sbin/ip
# which happens to be false in the installer.
from os import environ
paths = environ["PATH"].split(":")
if "/sbin" not in paths:
    environ["PATH"] += ":/sbin"
if "/bin" not in paths:
    environ["PATH"] += ":/bin"


def ip_link_set_name(src_name, dst_name):
    """
    Rename network interface src_name to dst_name using
      "ip link set $src_name name $dst_name"
    """

    LOG.debug("Attempting rename %s -> %s" % (src_name, dst_name))

    # Is the interface currently up?
    link_show = Popen(["ip", "link", "show", src_name], stdout = PIPE)
    stdout, _ = link_show.communicate()

    if link_show.returncode != 0:
        LOG.error("performing \"ip link show %s\" returned %d - skipping"
                  % (src_name, link_show.returncode))
        return

    # Does the string "UP" appear?
    isup = 'UP' in (stdout.split("<", 1)[1].split(">", 1)[0].split(','))

    # If it is up, bring it down for the rename
    if isup:
        link_down = Popen(["ip", "link", "set", src_name, "down"])
        link_down.wait()

        if link_down.returncode != 0:
            LOG.error("Unable to bring link %s down. (Exit %d)"
                      % (src_name, link_down.returncode))
            return

    # Perform the rename
    link_rename = Popen(["ip", "link", "set", src_name, "name", dst_name])
    link_rename.wait()

    if link_rename.returncode != 0:
        LOG.error("Unable to rename link %s to %s. (Exit %d)"
                  % (src_name, dst_name, link_rename.returncode))
        return

    # if the device was up before, bring it back up
    if isup:

        # Performace note: if we are doing an intermediate rename to
        # move a device sideways, we shouldnt bring it back until it has
        # its final name.  However, i cant think of a non-hacky way of doing
        # this with the current implementation

        link_up = Popen(["ip", "link", "set", dst_name, "up"])
        link_up.wait()

        if link_up.returncode != 0:
            LOG.error("Unable to bring link %s back up. (Exit %d)"
                      % (src_name, link_down.returncode))
            return

    LOG.info("Succesfully renamed link %s to %s" % (src_name, dst_name))

