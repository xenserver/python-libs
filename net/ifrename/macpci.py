#!/usr/bin/env python

"""
Copyright (c) 2013, Citrix Inc.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met: 

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer. 
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
MACPCI object.

Used extensivly for interface rename logic.
"""

__version__ = "1.0.1"
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

    def __hash__(self):
        return hash("%s-%s" % (self.mac, self.pci))

    def __eq__(self, other):
        return ( self.mac == other.mac and
                 self.pci == other.pci )

    def __ne__(self, other):
        return ( self.mac != other.mac or
                 self.pci != other.pci )

    def __lt__(self, other):
        return self.order < other.order
