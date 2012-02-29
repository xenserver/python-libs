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
MACPCI object.

Used extensivly for interface rename logic.
"""

__version__ = "1.0.0"
__author__  = "Andrew Cooper"

from xcp.pci import PCI
from xcp.net.mac import MAC

class MACPCI(object):

    def __init__(self, mac, pci, kname=None, tname=None, order=0,
                 ppn=None, label=None):

        if isinstance(mac, MAC):
            self.mac = mac
        else:
            self.mac = MAC(mac)

        if isinstance(pci, PCI):
            self.pci = pci
        else:
            self.pci = PCI(pci)

        self.kname = kname
        self.tname = tname
        self.order = order

        self.ppn = ppn
        self.label = label

    def __str__(self):
        res = ""
        if self.kname:
            res += "%s->" % (self.kname,)
        res += "(%s,%s)" % (self.mac, self.pci)
        if self.tname:
            res += "->%s" % (self.tname,)
        return res

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return ( self.mac == other.mac and
                 self.pci == other.pci )

    def __ne__(self, other):
        return ( self.mac != other.mac or
                 self.pci != other.pci )

    def __lt__(self, other):
        return self.order < other.order
