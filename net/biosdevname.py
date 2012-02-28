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
Utility functions to get information from biosdevname about the
current network state.
"""

__version__ = "1.0.0"
__author__ = "Andrew Cooper"

from subprocess import Popen, PIPE

__ALL_POLICIES = [ "physical", "all_ethN" ]

def __run_single_device(eth, policy = "physical"):
    """
    Run 'biosdevname -i eth' for a specified policy.
    Return (stdout, stderr, returncode) tuple.
    """

    proc = Popen(["/sbin/biosdevname", "--policy", policy,
                  "-i"], stdout=PIPE, stderr=PIPE)

    stdout, stderr = proc.communicate()

    return ( stdout, stderr, proc.returncode )

def __run_all_devices(policy = "physical"):
    """
    Run 'biosdevname -d' for a specified policy.
    Return (stdout, stderr, returncode) tuple.
    """

    proc = Popen(["/sbin/biosdevname", "--policy", policy,
                  "-d"], stdout=PIPE, stderr=PIPE)

    stdout, stderr = proc.communicate()

    return ( stdout, stderr, proc.returncode )

def all_devices_all_names():
    """
    Get all information, including all names, for all devices.
    Returns a dictionary of devices, indexed by current kernel name.  All
    entries will be string to string mappings, with the exception of
    'BIOS device' which will be a dictonary of policies to names.
    """

    devices = {}

    for policy in __ALL_POLICIES:

        (stdout, _, retcode) = __run_all_devices(policy)

        if retcode:
            continue

        for device in (x.strip() for x in stdout.split("\n\n") if len(x)):
            dinfo = {}

            for l in device.split("\n"):
                k, v = l.split(":", 1)
                dinfo[k.strip()] = v.strip()

            if ( "Kernel name" not in dinfo or
                 "BIOS device" not in dinfo ):
                continue

            kname = dinfo["Kernel name"]

            if kname in devices:
                devices[kname]["BIOS device"][policy] = dinfo["BIOS device"]
            else:
                devices[kname] = dinfo
                devices[kname]["BIOS device"] = {policy: dinfo["BIOS device"]}

    return devices
