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
Utility functions to get information from biosdevname about the
current network state.
"""

__version__ = "1.0.0"
__author__ = "Andrew Cooper"

from subprocess import Popen, PIPE

__ALL_POLICIES = [ "physical", "all_ethN" ]

def __run_all_devices(policy = "physical"):
    """
    Run 'biosdevname -d' for a specified policy.
    Return (stdout, stderr, returncode) tuple.
    """

    proc = Popen(["/sbin/biosdevname", "--policy", policy,
                  "-d", "-x"], stdout=PIPE, stderr=PIPE, universal_newlines=True)

    stdout, stderr = proc.communicate()

    return ( stdout, stderr, proc.returncode )

def all_devices_all_names():
    """
    Get all information, including all names, for all devices.
    Returns a dictionary of devices, indexed by current kernel name.  All
    entries will be string to string mappings, with the exception of
    'BIOS device' which will be a dictionary of policies to names.
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

            # Treat USB devices the PCI device of their host adapter
            if dinfo.get("Bus Info", "").startswith("usb-") and "eth" in dinfo["Kernel name"]:
                dinfo["Bus Info"] = dinfo["Bus Info"].split('-')[1]

            kname = dinfo["Kernel name"]

            if kname in devices:
                devices[kname]["BIOS device"][policy] = dinfo["BIOS device"]
            else:
                devices[kname] = dinfo
                devices[kname]["BIOS device"] = {policy: dinfo["BIOS device"]}

    return devices

def has_ppn_quirks(bdn_dicts):
    # CA-75599 - Assert that no devices share the same SMBIOS Instance.  Some
    # BIOSes have multiple different NICs with the same value set, which causes
    # biosdevname to mis-name its physical policy names (emXX, pciXpX etc)

    smbios_instances = set()

    for info in bdn_dicts:

        instance = info.get("SMBIOS Instance", None)

        if instance:
            if instance in smbios_instances:
                return True
            else:
                smbios_instances.add(instance)

    return False
