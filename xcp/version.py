#!/usr/bin/env python

# Copyright (c) 2013, 2017 Citrix Inc.
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

"""version - version comparison methods"""

class Version(object):
    def __init__(self, ver, build = None):
        self.ver = ver
        self.build = build

    @staticmethod
    def intify(x):
        if x.isdigit():
            return int(x)
        return x

    @classmethod
    def from_string(cls, ver_str):
        """ Create an object instance from a string conforming to:

        p.q. ... y.z[-b]

        where:

        p.q. ... y.z are integer arcs
        b is a build identifier"""

        build = None

        if '-' in ver_str:
            ver_str, build = ver_str.split('-', 1)

        ver = [cls.intify(i) for i in ver_str.split('.')]

        return cls(ver, build)

    def ver_as_string(self):
        return '.'.join(map(str, self.ver))

    def build_as_string(self):
        return self.build if self.build else ''

    def __str__(self):
        build = self.build_as_string()
        if build != '':
            return self.ver_as_string() + '-' + build
        return self.ver_as_string()

    #************************************************************
    #
    # NOTE: Comparisons are performed as follows
    #
    # The version is always compared.
    #
    # Build identifiers are ignored.
    #
    #************************************************************

    @classmethod
    def arc_cmp(cls, l, r):
        return l - r

    @classmethod
    def ver_cmp(cls, l, r):
        assert type(l) is list
        assert type(r) is list

        # iterate over arcs in turn, zip() returns min(len(l), len(r)) tuples
        for la, ra in zip(l, r):
            ret = cls.arc_cmp(la, ra)
            if ret != 0:
                return ret

        # equal to this point, down to list length
        return (len(l) - len(r))

    def __eq__(self, v):
        return self.ver_cmp(self.ver, v.ver) == 0

    # The Python3 datamodel requires to implement __hash__ when __eq__
    # is implemented:
    # https://docs.python.org/3/reference/datamodel.html#object.__hash__
    # Example:https://github.com/swagger-api/swagger-codegen/issues/6475
    # Python2 pylint --py3k warns about it, and Pylint3 with out pylintrc
    # now too:
    def __hash__(self):  # type:() -> int
        return hash(str(self.ver))

    def __ne__(self, v):
        return self.ver_cmp(self.ver, v.ver) != 0

    def __lt__(self, v):
        return self.ver_cmp(self.ver, v.ver) < 0

    def __gt__(self, v):
        return self.ver_cmp(self.ver, v.ver) > 0

    def __le__(self, v):
        return self.ver_cmp(self.ver, v.ver) <= 0

    def __ge__(self, v):
        return self.ver_cmp(self.ver, v.ver) >= 0
