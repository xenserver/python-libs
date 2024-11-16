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
Mac address object for manipulation and comparison.
"""

__version__ = "1.0.1"
__author__  = "Andrew Cooper"

import re
import six

VALID_COLON_MAC = re.compile(r"^([\da-fA-F]{1,2}:){5}[\da-fA-F]{1,2}$")
VALID_DASH_MAC = re.compile(r"^([\da-fA-F]{1,2}-){5}[\da-fA-F]{1,2}$")
VALID_DOTQUAD_MAC = re.compile(r"^([\da-fA-F]{1,4}\.){2}[\da-fA-F]{1,4}$")

@six.python_2_unicode_compatible
class MAC(object):
    """
    Mac address object for manipulation and comparison
    """

    @classmethod
    def is_valid(cls, addr):
        """
        Static method to ascertain whether addr is a recognised MAC address or
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
        self.integer = -1

        if not isinstance(addr, six.string_types):
            raise TypeError("String expected")

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


    def _set_from_str_octets(self, octets):
        """Private helper"""
        if len(octets) != 6:
            raise ValueError("Expected 6 octets, got %d" % len(octets))

        self.octets = [ int(i, 16) for i in octets ]
        # See:https://diveintopython3.net/porting-code-to-python-3-with-2to3.html#xrange
        # False positive from pylint --py3k: pylint: disable=range-builtin-not-iterating
        self.integer = sum(t[0] << t[1] for t in
                           zip(self.octets, range(40, -1, -8)))

    def _set_from_str_quads(self, quads):
        """Private helper"""
        if len(quads) != 3:
            raise ValueError("Expected 3 quads, got %d" % len(quads))

        self.octets = []
        for quad in ( int(i, 16) for i in quads ):
            self.octets.extend([(quad >> 8) & 0xff, quad & 0xff])

        # False positive from pylint --py3k: pylint: disable=range-builtin-not-iterating
        self.integer = sum(t[0] << t[1] for t in
                           zip(self.octets, range(40, -1, -8)))

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
        return ':'.join([ "%0.2x" % x for x in self.octets])

    def __repr__(self):
        return "<MAC %s>" % ':'.join([ "%0.2x" % x for x in self.octets])

    def as_string(self, sep = ".", upper = False):
        """Get a string representation of this MAC address"""
        res = ""

        if sep == ".":
            # this is a hack but I cant think of an easy way of
            # manipulating self.octets
            res = "%0.4x.%0.4x.%0.4x" % ( (self.integer >> 32) & 0xffff,
                                          (self.integer >> 16) & 0xffff,
                                          (self.integer      ) & 0xffff )

        elif sep == "-":
            res = '-'.join([ "%0.2x" % o for o in self.octets])

        elif sep == ":":
            res = ':'.join([ "%0.2x" % o for o in self.octets])

        else:
            raise ValueError("'%s' is not a valid separator" % sep)

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
