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

def get_new_temp_name(nics, eth):
    """Generate a new temporary name"""
    names = ( [ x.kname for x in nics if x.kname ] +
              [ x.tname for x in nics if x.tname ] )
    while True:
        rn = random.randrange(1, 2**16-1)
        name = "side-%d-%s" % (rn, eth)
        if name not in names:
            return name

def needs_renaming(nic):
    """Check whether a nic needs renaming or not"""
    if nic.tname and VALID_ETH_NAME.match(nic.tname) is not None:
        return False
    return True
