#!/usr/bin/env python
# Copyright (c) 2011,2012 Citrix Systems, Inc.
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
Mac address object for manipulation and comparison.
"""

__version__ = "1.0.1"
__author__  = "Andrew Cooper"

import re

VALID_COLON_MAC = re.compile(r"^([\da-fA-F]{1,2}:){5}[\da-fA-F]{1,2}$")
VALID_DASH_MAC = re.compile(r"^([\da-fA-F]{1,2}-){5}[\da-fA-F]{1,2}$")
VALID_DOTQUAD_MAC = re.compile(r"^([\da-fA-F]{1,4}\.){2}[\da-fA-F]{1,4}$")

class MAC(object):
    """
    Mac address object for manipulation and comparison
    """

    @classmethod
    def is_valid(cls, addr):
        """
        Static method to assertain whether addr is a recognised MAC address or
        not
        """
        try:
            MAC(addr)
        except Exception:
            return False
        return True

    def __init__(self, addr):
        """Constructor"""

        self.octets = []
        self.integer = -1L

        if isinstance(addr, (str, unicode)):

            res = VALID_COLON_MAC.match(addr)
            if res:
                self._set_from_str_octets(addr.split(":"))
                return

            res = VALID_DASH_MAC.match(addr)
            if res:
                self._set_from_str_octets(addr.split("-"))
                return

            res = VALID_DOTQUAD_MAC.match(addr)
            if res:
                self._set_from_str_quads(addr.split("."))
                return

            raise ValueError("Unrecognised MAC address '%s'" % addr)

        else:
            raise TypeError("String expected")


    def _set_from_str_octets(self, octets):
        """Private helper"""
        if len(octets) != 6:
            raise ValueError("Expected 6 octets, got %d" % len(octets))

        self.octets = [ int(i, 16) for i in octets ]
        self.integer = long(sum(t[0] << t[1] for t in
                                zip(self.octets, xrange(40, -1, -8))))

    def _set_from_str_quads(self, quads):
        """Private helper"""
        if len(quads) != 3:
            raise ValueError("Expected 3 quads, got %d" % len(quads))

        self.octets = []
        for quad in ( int(i, 16) for i in quads ):
            self.octets.extend([(quad >> 8) & 0xff, quad & 0xff])

        self.integer = long(sum(t[0] << t[1] for t in
                                zip(self.octets, xrange(40, -1, -8))))

    def is_unicast(self):
        """is this a unicast address?"""
        return (self.integer & 1 << 40) == 0

    def is_multicast(self):
        """is this a multicast address?"""
        return (self.integer & 1 << 40) != 0

    def is_global(self):
        """is this a globally administered address?"""
        return (self.integer & 1 << 41) == 0

    def is_local(self):
        """is this a locally administered address?"""
        return (self.integer & 1 << 41) != 0



    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return ':'.join([ "%0.2x" % x for x in self.octets])

    def __repr__(self):
        return "<MAC %s>" % ':'.join([ "%0.2x" % x for x in self.octets])

    def as_string(self, sep = ".", upper = False):
        """Get a string representation of this MAC address"""
        res = ""

        if sep == ".":
            # this is a hack but I cant think of an easy way of
            # manipulating self.octetes
            res = "%0.4x.%0.4x.%0.4x" % ( (self.integer >> 32) & 0xffff,
                                          (self.integer >> 16) & 0xffff,
                                          (self.integer      ) & 0xffff )

        elif sep == "-":
            res = '-'.join([ "%0.2x" % o for o in self.octets])

        elif sep == ":":
            res = ':'.join([ "%0.2x" % o for o in self.octets])

        else:
            raise ValueError("'%s' is not a valid seperator" % sep)

        if upper:
            return res.upper()
        return res

    def __eq__(self, rhs):
        if hasattr(rhs, "integer"):
            return self.integer == rhs.integer
        elif MAC.is_valid(rhs):
            return self.integer == MAC(rhs).integer
        else:
            return NotImplemented

    def __ne__(self, rhs):
        if hasattr(rhs, "integer"):
            return self.integer != rhs.integer
        elif MAC.is_valid(rhs):
            return self.integer != MAC(rhs).integer
        else:
            return NotImplemented

    def __hash__(self):
        return self.__str__().__hash__()

    def __lt__(self, rhs):
        if hasattr(rhs, "integer"):
            return self.integer < rhs.integer
        elif MAC.is_valid(rhs):
            return self.integer < MAC(rhs).integer
        else:
            return NotImplemented

    def __le__(self, rhs):
        if hasattr(rhs, "integer"):
            return self.integer <= rhs.integer
        elif MAC.is_valid(rhs):
            return self.integer <= MAC(rhs).integer
        else:
            return NotImplemented

    def __gt__(self, rhs):
        if hasattr(rhs, "integer"):
            return self.integer > rhs.integer
        elif MAC.is_valid(rhs):
            return self.integer > MAC(rhs).integer
        else:
            return NotImplemented

    def __ge__(self, rhs):
        if hasattr(rhs, "integer"):
            return self.integer >= rhs.integer
        elif MAC.is_valid(rhs):
            return self.integer >= MAC(rhs).integer
        else:
            return NotImplemented
