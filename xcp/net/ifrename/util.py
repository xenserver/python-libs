#!/usr/bin/env python

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
Utility functions for ifrename code
"""

import pprint, random
from xcp.net.ifrename.logic import VALID_ETH_NAME

def niceformat(obj):
    """conditional pprint"""
    try:
        if len(obj) > 1:
            return pprint.pformat(obj, indent=2)
    except Exception:
        return str(obj)
    else:
        return str(obj)


def get_nic_with_kname(nics, kname):
    """Search for nic with kname"""
    for nic in nics:
        if nic.kname == kname:
            return nic
    return None

def tname_free(nics, name):
    """Check that name is not taken by any nics"""
    return name not in map(lambda x: x.tname, nics)

def get_nic_with_mac(nics, mac):
    """Search for nic with mac"""
    for nic in nics:
        if nic.mac == mac:
            return nic
    return None

def get_nic_with_pci(nics, pci):
    """Search for nic with pci"""
    for nic in nics:
        if nic.pci == pci:
            return nic
    return None

def get_nics_with_pci(nics, pci):
    """Search for all nics with a PCI for multi-eth-per-function cards"""
    return [ n for n in nics if n.pci == pci ]

def get_new_temp_name(nics, eth):
    """Generate a new temporary name"""
    names = ( [ x.kname for x in nics if x.kname ] +
              [ x.tname for x in nics if x.tname ] )
    while True:
        # len(name) cannot be greater than 15. Using a 4 digit random number
        # allows for 100 (eth0-eth99) devices to have a temp name without going
        # over 15 byte limit
        rn = random.randrange(1, 10000)
        name = "side-%d-%s" % (rn, eth)
        if name not in names:
            return name

def needs_renaming(nic):
    """Check whether a nic needs renaming or not"""
    if nic.tname and VALID_ETH_NAME.match(nic.tname) is not None:
        return False
    return True
