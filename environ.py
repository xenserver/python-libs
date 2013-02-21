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

import os
import os.path

EXTRA_SCRIPTS_DIR = '/mnt'

def installerRunning():
    return os.environ.get('XS_INSTALLATION', '0') != '0'

def buildingInitialTar():
    return 'CARBON_DISTROS_DIR' in os.environ

class InventoryError(Exception):
    pass

def readInventory(root = '/'):

    fh = None
    d = {}

    try:

        try:
            fh = open(os.path.join(root, 'etc/xensource-inventory'))

            for line in ( x for x in ( y.strip() for y in fh.xreadlines() )
                          if not x.startswith('#') ):

                vals = line.split('=', 1)

                if ( len(vals) != 2 or
                     vals[0].endswith(" ") or vals[0].endswith("\t") or
                     vals[1].startswith(" ") or vals[1].startswith("\t") ):
                    raise InventoryError("Invalid line found '%s'" % (line,))

                d[vals[0]] = vals[1].strip('"\'')

        except IOError, e:
            raise InventoryError("Error reading from file '%s'" % (e,))

    finally:
        if fh:
            fh.close()

    return d
