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

def readInventory(root = '/'):
    fh = open(os.path.join(root, 'etc/xensource-inventory'))
    d = dict(map(lambda x: [x[:x.find('=')], x[x.find('=')+1:].strip().strip("'")], fh))
    fh.close()

    return d
