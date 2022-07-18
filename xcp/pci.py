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

import os.path
import subprocess
import re
import six

_SBDF = (r"(?:(?P<segment> [\da-dA-F]{4}):)?" # Segment (optional)
         r"     (?P<bus>     [\da-fA-F]{2}):"   # Bus
         r"     (?P<device>  [\da-fA-F]{2})\."  # Device
         r"     (?P<function>[\da-fA-F])"       # Function
         )

# Don't change the meaning of VALID_SBDF as some parties may be using it
VALID_SBDF = re.compile(r"^%s$" % _SBDF, re.X)

VALID_SBDFI = re.compile(
    r"^(?P<sbdf>%s)"
    r"  (?:[[](?P<index>[\d]{1,2})[]])?$"   # Index (optional)
    % _SBDF
    , re.X)


class PCI(object):
    """PCI address object for manipulation and comparison"""

    @classmethod
    def is_valid(cls, addr):
        """
        Static method to assertain whether addr is a recognised PCI address
        or not
        """
        try:
            PCI(addr)
        except Exception:
            return False
        return True

    def __init__(self, addr):
        """Constructor"""

        self.integer = -1
        self.segment = -1
        self.bus = -1
        self.device = -1
        self.function = -1
        self.index = -1

        if isinstance(addr, six.string_types):

            res = VALID_SBDFI.match(addr)
            if res:
                groups = res.groupdict()

                if "segment" in groups and groups["segment"] is not None:
                    self.segment = int(groups["segment"], 16)
                else:
                    self.segment = 0

                self.bus = int(groups["bus"], 16)
                if not ( 0 <= self.bus < 2**8 ):
                    raise ValueError("Bus '%d' out of range 0 <= bus < 256"
                                     % (self.bus,))

                self.device = int(groups["device"], 16)
                if not ( 0 <= self.device < 2**5):
                    raise ValueError("Device '%d' out of range 0 <= device < 32"
                                     % (self.device,))

                self.function = int(groups["function"], 16)
                if not ( 0 <= self.function < 2**3):
                    raise ValueError("Function '%d' out of range 0 <= device "
                                     "< 8" % (self.function,))

                if "index" in groups and groups["index"] is not None:
                    self.index = int(groups["index"])
                else:
                    self.index = 0

                self.integer = (int(self.segment   << 16 |
                                    self.bus       << 8  |
                                    self.device    << 3  |
                                    self.function) << 8  |
                                self.index)
                return

            raise ValueError("Unrecognised PCI address '%s'" % addr)

        else:
            raise TypeError("String expected")


    def __str__(self):
        pci_sbdf = "%04x:%02x:%02x.%1x" % (self.segment, self.bus,
                                           self.device, self.function)
        return "%s[%d]" % (pci_sbdf, self.index)

    def __repr__(self):
        return "<PCI %s>" % (self,)

    def __eq__(self, rhs):
        if hasattr(rhs, "integer"):
            return self.integer == rhs.integer
        else:
            try:
                return self.integer == PCI(rhs).integer
            except Exception:
                return NotImplemented

    def __ne__(self, rhs):
        if hasattr(rhs, "integer"):
            return self.integer != rhs.integer
        else:
            try:
                return self.integer != PCI(rhs).integer
            except Exception:
                return NotImplemented

    def __hash__(self):
        return self.__str__().__hash__()

    def __lt__(self, rhs):
        if hasattr(rhs, "integer"):
            return self.integer < rhs.integer
        else:
            try:
                return self.integer < PCI(rhs).integer
            except Exception:
                return NotImplemented

    def __le__(self, rhs):
        if hasattr(rhs, "integer"):
            return self.integer <= rhs.integer
        else:
            try:
                return self.integer <= PCI(rhs).integer
            except Exception:
                return NotImplemented

    def __gt__(self, rhs):
        if hasattr(rhs, "integer"):
            return self.integer > rhs.integer
        else:
            try:
                return self.integer > PCI(rhs).integer
            except Exception:
                return NotImplemented

    def __ge__(self, rhs):
        if hasattr(rhs, "integer"):
            return self.integer >= rhs.integer
        else:
            try:
                return self.integer >= PCI(rhs).integer
            except Exception:
                return NotImplemented


class PCIIds(object):
    def __init__(self, fn):
        self.vendor_dict = {}
        self.sub_dict = {}
        self.main_dict = {}
        self.class_dict = {}

        vendor = None
        cls = None

        fh = open(fn)
        for l in fh:
            line = l.rstrip()
            if line == '' or line.startswith('#'):
                continue

            if line.startswith('C'):
                # Class
                vendor = None
                _, cls, cls_text = line.split(None, 2)
                if cls not in self.class_dict:
                    self.class_dict[cls] = (cls_text, None)
            elif line.startswith('\t\t'):
                if vendor:
                    # subvendor, subdevice
                    subvendor, subdevice, text = line.split(None, 2)
                    key = "%s:%s" % (subvendor, subdevice)
                    if key not in self.sub_dict:
                        self.sub_dict[key] = text
            elif line.startswith('\t'):
                if vendor:
                    # device
                    device, text = line.split(None, 1)
                    key = "%s:%s" % (vendor, device)
                    if key not in self.main_dict:
                        self.main_dict[key] = text
                else:
                    # subclass
                    sub_cls, sub_text = line.split(None, 1)
                    key = "%s:%s" % (cls, sub_cls)
                    if key not in self.class_dict:
                        self.class_dict[key] = (cls_text, sub_text)
            else:
                # vendor
                cls = None
                vendor, text = line.split(None, 1)
                if vendor not in self.vendor_dict:
                    self.vendor_dict[vendor] = text

        fh.close()

    @classmethod
    def read(cls):
        for f in ['/usr/share/hwdata/pci.ids']:
            if os.path.exists(f):
                return cls(f)
        raise Exception('Failed to open PCI database')

    def findVendor(self, vendor):
        return vendor in self.vendor_dict and self.vendor_dict[vendor] or None

    def findDevice(self, vendor, device):
        key = "%s:%s" % (vendor, device)
        return key in self.main_dict and self.main_dict[key] or None

    def findSubdevice(self, subvendor, subdevice):
        key = "%s:%s" % (subvendor, subdevice)
        return key in self.sub_dict and self.sub_dict[key] or None

    def lookupClass(self, cls_str):
        ret = []
        for k, (c, sc) in self.class_dict.items():
            if not sc and cls_str in c and k not in ret:
                ret.append(k)
        return ret

class PCIDevices(object):
    def __init__(self):
        self.devs = {}

        cmd = subprocess.Popen(['lspci', '-mn'], bufsize = 1,
                               stdout = subprocess.PIPE)
        for l in cmd.stdout:
            line = l.rstrip()
            el = [x for x in line.replace('"', '').split() if not x.startswith('-')]
            self.devs[el[0]] = {'id': el[0],
                                'class': el[1][:2],
                                'subclass': el[1][2:],
                                'vendor': el[2],
                                'device': el[3]}
            if len(el) == 6:
                self.devs[el[0]]['subvendor'] = el[4]
                self.devs[el[0]]['subdevice'] = el[5]
        cmd.wait()

    def findByClass(self, cls, subcls = None):
        """ return all devices that match either of:

        	class, subclass
        	[class1, class2, ... classN]"""
        if subcls:
            assert isinstance(cls, six.string_types)
            return [x for x in self.devs.values() if x['class'] == cls and x['subclass'] == subcls]
        else:
            assert isinstance(cls, list)
            return [x for x in self.devs.values() if x['class'] in cls]

    def findRelatedFunctions(self, dev):
        """ return other devices that share the same bus & slot"""
        def slot(dev):
            left, _ = dev.rsplit('.', 1)
            return left

        return [x for x in self.devs if x != dev and slot(x) == slot(dev)]


def pci_sbdfi_to_nic(sbdfi, nics):
    match = VALID_SBDFI.match(sbdfi)

    index = 0
    if 'index' in match.groupdict():
        index_str = match.group("index")
        if index_str is not None:
            index = int(index_str)
    value = match.group("sbdf")

    matching_nics = [nic for nic in nics if nic.pci == value]
    matching_nics.sort(key=lambda nic: nic.mac)

    if index >= len(matching_nics):
        raise Exception("Insufficient NICs with PCI SBDF %s (Found %d, wanted at least %d)" % (value, len(matching_nics), index))

    return matching_nics[index]
