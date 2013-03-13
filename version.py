#!/usr/bin/env python
# Copyright (c) 2011 Citrix Systems, Inc.
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

"""version - version comparison methods"""

class Version:
    def __init__(self, ver, build = None, build_suf = None):
        self.ver = ver
        self.build = build
        self.build_suf = build_suf

    @staticmethod
    def intify(x):
        if x.isdigit():
            return int(x)
        return x

    @classmethod
    def from_string(cls, ver_str):
        """ Create an object instance from a string conforming to:

        p.q. ... y.z[-b[s]]

        where:

        p.q. ... y.z are arcs
        b is a build number
        s is a build suffix

        an arc is one of:

        a positive integer
        a sequence of subarcs, s-t-u"""

        build = None
        build_suf = None

        ver = map(cls.intify, ver_str.split('.'))

        if type(ver[-1]) is str and '-' in ver[-1] and ver[-1][-1].isalpha():
            ver_el, build_str = ver[-1].rsplit('-', 1)
            ver[-1] = cls.intify(ver_el)

            if build_str:
                if not build_str.isdigit():
                    build_suf = build_str[-1]
                    build_str = build_str[:-1]
                build = int(build_str)

        return cls(ver, build, build_suf)

    def ver_as_string(self):
        return '.'.join(map(str, self.ver))

    def build_as_string(self):
        val = ''
        if self.build:
            val += str(self.build)
        if self.build_suf:
            val += self.build_suf
        return val

    def __str__(self):
        build = self.build_as_string()
        if build != '':
            return self.ver_as_string() + '-' + self.build_as_string()
        return self.ver_as_string()

    #************************************************************
    #
    # NOTE: Comparisons are performed as follows
    #
    # The version is always compared.
    #
    # If rhs has a build it is compared. If lhs has no build it evaluates
    # to -1.
    #
    # Build suffix is ignored.
    #
    #************************************************************

    @classmethod
    def arc_cmp(cls, l, r):
        if type(l) is int and type(r) is int:
            return (l-r)
        elif type(l) is str and '-' in l:
            if type(r) is str and '-' in r:
                return cls.ver_cmp(map(cls.intify, l.split('-')),
                                   map(cls.intify, r.split('-')))
            elif type(r) is int:
                return cls.ver_cmp(map(cls.intify, l.split('-')), [r])
        elif type(l) is int:
            return cls.ver_cmp([l], map(cls.intify, r.split('-')))
        else:
            raise RuntimeError, "Invalid arc types"

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

    def ver_build_cmp(self, v):
        l = self.ver[:]
        r = v.ver[:]

        if v.build != None:
            l.append(self.build == None and -1 or self.build)
            r.append(v.build)

        return self.ver_cmp(l, r)

    def __eq__(self, v):
        return self.ver_build_cmp(v) == 0

    def __ne__(self, v):
        return self.ver_build_cmp(v) != 0

    def __lt__(self, v):
        return self.ver_build_cmp(v) < 0

    def __gt__(self, v):
        return self.ver_build_cmp(v) > 0

    def __le__(self, v):
        return self.ver_build_cmp(v) <= 0

    def __ge__(self, v):
        return self.ver_build_cmp(v) >= 0
