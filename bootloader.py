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

import os
import os.path
import re
import tempfile

COUNTER = 0

class MenuEntry(object):
    def __init__(self, hypervisor, hypervisor_args, kernel, kernel_args,
                 initrd, title = None):
        self.hypervisor = hypervisor
        self.hypervisor_args = hypervisor_args
        self.kernel = kernel
        self.kernel_args = kernel_args
        self.initrd = initrd
        self.title = title

    def getHypervisorArgs(self):
        return re.findall(r'\S[^ "]*(?:"[^"]*")?\S*', self.hypervisor_args)

    def setHypervisorArgs(self, args):
        self.hypervisor_args = ' '.join(args)

    def getKernelArgs(self):
        return re.findall(r'\S[^ "]*(?:"[^"]*")?\S*', self.kernel_args)

    def setKernelArgs(self, args):
        self.kernel_args = ' '.join(args)
    
class Bootloader(object):
    def __init__(self, src_fmt, src_file, menu = None, menu_order = None,
                 default = None, timeout = None, serial = None, 
                 location = None):

        if menu is None:
            menu = {}

        if menu_order is None:
            menu_order = []

        self.src_fmt = src_fmt
        self.src_file = src_file
        self.menu = menu
        self.menu_order = menu_order
        self.default = default
        self.timeout = timeout
        self.serial = serial
        self.location = location and location or 'mbr'

    def append(self, label, entry):
        self.menu[label] = entry
        self.menu_order.append(label)
        
    def remove(self, label):
        del self.menu[label]
        self.menu_order.remove(label)
        
    @classmethod
    def readExtLinux(cls, src_file):
        menu = {}
        menu_order = []
        default = None
        timeout = None
        location = None
        serial = None
        label = None
        title = None

        fh = open(src_file)
        try:
            for line in fh:
                l = line.strip()
                els = l.split(None, 2)
                if len(els) == 0:
                    continue

                # header
                if (l.startswith('# location ') and len(els) == 3 and 
                    els[2] in ['mbr', 'partition']):
                    location = els[2]
                elif els[0] == 'serial' and len(els) > 1:
                    baud = 9600
                    if len(els) > 2:
                        baud = int(els[2])
                    serial = {'port': int(els[1]), 'baud': baud}
                elif els[0] == 'default' and len(els) == 2:
                    default = els[1]
                elif els[0] == 'timeout' and len(els) == 2:
                    timeout = int(els[1])

                # menu
                elif els[0] == 'label' and len(els) == 2:
                    label = els[1]
                    menu[label] = {}
                    menu_order.append(label)
                    title = None
                elif label:
                    if els[0] == '#':
                        title = l[1:].lstrip()
                    elif els[0] == 'append' and len(els) > 1:
                        # els[2] contains hypervisor args, kernel,
                        # kernel args & initrd
                        args = map(lambda x: x.strip(), els[2].split('---'))
                        if len(args) == 3:
                            kernel = args[1].split(None, 1)
                            if len(kernel) == 2:
                                menu[label] = MenuEntry(els[1], args[0], 
                                                        kernel[0], kernel[1],
                                                        args[2], title)
        finally:
            fh.close()

        return cls('extlinux', src_file, menu, menu_order, default, timeout,
                   serial, location)

    @classmethod
    def readGrub(cls, src_file):
        menu = {}
        menu_order = []
        default = 0
        timeout = None
        location = None
        serial = None
        label = None
        title = None
        hypervisor = None
        hypervisor_args = None
        kernel = None
        kernel_args = None

        def create_label(title):
            global COUNTER
            
            # FIXME use branding
            if title == 'XenServer':
                return 'xe'

            if title.endswith('(Serial)'):
                return 'xe-serial'
            if title.endswith('Safe Mode'):
                return 'safe'
            if ' / ' in title:
                if '(Serial,' in title:
                    return 'fallback-serial'
                else:
                    return 'fallback'
            COUNTER += 1
            return "label%d" % COUNTER

        fh = open(src_file)
        try:
            for line in fh:
                l = line.strip()
                els = l.split(None, 2)
                if len(els) == 0:
                    continue

                # header
                if (l.startswith('# location ') and len(els) == 3 and 
                    els[2] in ['mbr', 'partition']):
                    location = els[2]
                elif els[0] == 'serial' and len(els) > 1:
                    port = 0
                    baud = 9600
                    for arg in l.split(None, 1)[1].split():
                        if '=' in arg:
                            opt, val = arg.split('=')
                            if opt == '--unit':
                                port = int(val)
                            elif opt == '--speed':
                                baud = int(val)
                    serial = {'port': port, 'baud': baud}
                elif els[0] == 'default' and len(els) == 2:
                    # default is index into menu list, fixup later
                    default = int(els[1])
                elif els[0] == 'timeout' and len(els) == 2:
                    timeout = int(els[1]) * 10

                # menu
                elif els[0] == 'title' and len(els) > 1:
                    title = l.split(None, 1)[1]
                elif title:
                    if els[0] == 'kernel' and len(els) > 2:
                        hypervisor, hypervisor_args = (l.split(None, 1)
                                                       [1].split(None, 1))
                    elif els[0] == 'module' and len(els) > 1:
                        if kernel and hypervisor:
                            # second module == initrd
                            label = create_label(title)
                            menu_order.append(label)
                            menu[label] = MenuEntry(hypervisor, hypervisor_args,
                                                    kernel, kernel_args,
                                                    els[1], title)
                            hypervisor = None
                            kernel = None
                        else:
                            kernel, kernel_args = (l.split(None, 1)
                                                   [1].split(None, 1))
                    elif els[0] == 'initrd' and len(els) > 1:
                        # not multiboot
                        kernel = hypervisor
                        kernel_args = hypervisor_args
                        label = create_label(title)
                        menu_order.append(label)
                        menu[label] = MenuEntry(None, None,
                                                kernel, kernel_args,
                                                els[1], title)
                        hypervisor = None
                        hypervisor_args = None

            # fixup default
            if len(menu_order) > default:
                default = menu_order[default]
        finally:
            fh.close()

        return cls('grub', src_file, menu, menu_order, default,
                   timeout, serial, location)

    @classmethod
    def loadExisting(cls, root = '/'):
        if os.path.exists(os.path.join(root, "boot/extlinux.conf")):
            return cls.readExtLinux(os.path.join(root, "boot/extlinux.conf"))
        elif os.path.exists(os.path.join(root, "boot/grub/menu.lst")):
            return cls.readGrub(os.path.join(root, "boot/grub/menu.lst"))
        else:
            raise RuntimeError, "No existing bootloader configuration found"

    def writeExtLinux(self, dst_file = None):
        if hasattr(dst_file, 'name'):
            fh = dst_file
        else:
            fh = open(dst_file, 'w')
        print >> fh, "# location " + self.location

        if self.serial:
            print >> fh, "serial %d %d" % (self.serial['port'],
                                           self.serial['baud'])
        if self.default:
            print >> fh, "default " + self.default
        print >> fh, "prompt 1"
        if self.timeout:
            print >> fh, "timeout %d" % self.timeout

        for label in self.menu_order:
            print >> fh, "\nlabel " + label
            m = self.menu[label]
            if m.title:
                print >> fh, "  # " + m.title
            if m.hypervisor:
                print >> fh, "  kernel mboot.c32"
                print >> fh, "  append %s %s --- %s %s --- %s" % \
                    (m.hypervisor, m.hypervisor_args, m.kernel, m.kernel_args, m.initrd)
            else:
                print >> fh, "  kernel " + m.kernel
                print >> fh, "  append " + m.kernel_args
                print >> fh, "  initrd " + m.initrd
        if not hasattr(dst_file, 'name'):
            fh.close()

    def writeGrub(self, dst_file = None):
        if hasattr(dst_file, 'name'):
            fh = dst_file
        else:
            fh = open(dst_file, 'w')
        print >> fh, "# location " + self.location

        if self.serial:
            print >> fh, "serial --unit=%d --speed=%s" % (self.serial['port'],
                                                          self.serial['baud'])
            print >> fh, "terminal --timeout=10 console serial"
        else:
            print >> fh, "terminal console"
        if self.default:
            for i in range(len(self.menu_order)):
                if self.menu_order[i] == self.default:
                    print >> fh, "default %d" % i
                    break
        if self.timeout:
            print >> fh, "timeout %d" % (self.timeout / 10)

        for label in self.menu_order:
            m = self.menu[label]
            print >> fh, "\ntitle " + m.title
            if m.hypervisor:
                print >> fh, "   kernel " + m.hypervisor + " " + m.hypervisor_args
                print >> fh, "   module " + m.kernel + " " + m.kernel_args
                print >> fh, "   module " + m.initrd
            else:
                print >> fh, "   kernel " + m.kernel + " " + m.kernel_args
                print >> fh, "   initrd " + m.initrd
        if not hasattr(dst_file, 'name'):
            fh.close()

    def commit(self, dst_file = None):
        if not dst_file:
            dst_file = self.src_file

        # write to temp file in final destination directory
        fd, tmp_file = tempfile.mkstemp(dir = os.path.dirname(dst_file))

        if self.src_fmt == 'extlinux':
            self.writeExtLinux(tmp_file)
        elif self.src_fmt == 'grub':
            self.writeGrub(tmp_file)

        # atomically replace destination file
        os.close(fd)
        os.rename(tmp_file, dst_file)

    @classmethod
    def newDefault(cls, kernel_link_name, initrd_link_name, root = '/'):
        b = cls.loadExisting(root)
        # FIXME handle initial case
        if b.menu[b.default].kernel != kernel_link_name:
            backup = []
            if not os.path.exists(kernel_link_name):
                raise RuntimeError, "kernel symlink not found"
            if not os.path.exists(initrd_link_name):
                raise RuntimeError, "initrd symlink not found"
            old_kernel_link = b.menu[b.default].kernel
            old_ver = 'old'
            m = re.search(r'(-\d+\.\d+)-', old_kernel_link)
            if m:
                old_ver = m.group(1)

            for k, v in b.menu.items():
                if v.kernel == old_kernel_link:
                    backup.append((k+old_ver, MenuEntry(**v.__dict__)))
                    v.kernel = kernel_link_name
                    v.initrd = initrd_link_name

            if len(backup) > 0:
                for l, e in backup:
                    b.append(l, e)
            b.commit()
