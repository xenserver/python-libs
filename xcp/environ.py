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
