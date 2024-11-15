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

"""
Python function using 'ip' for convenience
"""

__version__ = "1.0.1"
__author__ = "Andrew Cooper"

from os import environ
from subprocess import Popen, PIPE

from xcp.logger import LOG

# Deal with lack of environment more sensibly than hard coding /sbin/ip
# which happens to be false in the installer.
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
    link_show = Popen(["ip", "link", "show", src_name], stdout = PIPE, universal_newlines=True)

    stdout, _ = link_show.communicate()

    if link_show.returncode != 0:
        LOG.error("performing \"ip link show %s\" returned %d - skipping"
                  % (src_name, link_show.returncode))
        return

    # Does the string "UP" appear?
    isup = 'UP' in (stdout.split("<", 1)[1].split(">", 1)[0].split(','))

    # If it is up, bring it down for the rename
    if isup:
        link_down = Popen(["ip", "link", "set", src_name, "down"], universal_newlines=True)
        link_down.wait()

        if link_down.returncode != 0:
            LOG.error("Unable to bring link %s down. (Exit %d)"
                      % (src_name, link_down.returncode))
            return

    # Perform the rename
    link_rename = Popen(["ip", "link", "set", src_name, "name", dst_name], universal_newlines=True)
    link_rename.wait()

    if link_rename.returncode != 0:
        LOG.error("Unable to rename link %s to %s. (Exit %d)"
                  % (src_name, dst_name, link_rename.returncode))
        return

    # if the device was up before, bring it back up
    if isup:

        # Performance note: if we are doing an intermediate rename to
        # move a device sideways, we shouldn't bring it back until it has
        # its final name.  However, I can't think of a non-hacky way of doing
        # this with the current implementation

        link_up = Popen(["ip", "link", "set", dst_name, "up"], universal_newlines=True)
        link_up.wait()

        if link_up.returncode != 0:
            LOG.error("Unable to bring link %s back up. (Exit %d)"
                      % (src_name, link_up.returncode))  # pragma: no cover
            return

    LOG.info("Succesfully renamed link %s to %s" % (src_name, dst_name))
