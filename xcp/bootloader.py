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

from __future__ import division, print_function

import copy
from enum import Enum
import os
import os.path
import re
import tempfile
from typing import cast

import xcp.cmd

try:  # xenserver-release.rpm puts a branding.py into our xcp installation directory:
    from xcp import branding  # type:ignore[attr-defined] # pytype: disable=import-error
except ImportError:  # For CI, use stubs/branding.py (./stubs is added to pythonpath)
    import branding

from .compat import open_textfile

_counter = 0

class Grub2Format(Enum):
    MULTIBOOT2 = 0
    LINUX = 1
    XEN_BOOT = 2

class MenuEntry(object):
    # pylint: disable=too-many-positional-arguments
    def __init__(self, hypervisor, hypervisor_args, kernel, kernel_args,
                 initrd, title = None, root = None):
        self.extra = None
        self.contents = []
        self.hypervisor = hypervisor
        self.hypervisor_args = hypervisor_args
        self.kernel = kernel
        self.kernel_args = kernel_args
        self.initrd = initrd
        self.title = title
        self.root = root
        self.entry_format = None  # type: Grub2Format | None

    def getHypervisorArgs(self):
        return re.findall(r'\S[^ "]*(?:"[^"]*")?\S*', self.hypervisor_args)

    def setHypervisorArgs(self, args):
        self.hypervisor_args = ' '.join(args)

    def getKernelArgs(self):
        return re.findall(r'\S[^ "]*(?:"[^"]*")?\S*', self.kernel_args)

    def setKernelArgs(self, args):
        self.kernel_args = ' '.join(args)

class Bootloader(object):
    # pylint: disable=too-many-positional-arguments
    def __init__(self, src_fmt, src_file, menu = None, menu_order = None,
                 default = None, timeout = None, serial = None,
                 location = None, env_block = None):

        if menu is None:
            menu = {}

        if menu_order is None:
            menu_order = []

        self.boilerplate = []
        self.src_fmt = src_fmt
        self.src_file = src_file
        self.menu = menu
        self.menu_order = menu_order
        self.default = default
        self.timeout = timeout
        self.serial = serial
        self.location = location and location or 'mbr'
        self.env_block = env_block

    def append(self, label, entry):
        self.menu[label] = entry
        self.menu_order.append(label)

    def remove(self, label):
        del self.menu[label]
        self.menu_order.remove(label)

    @classmethod
    def readGrub2(cls, src_file):
        # type:(str) -> Bootloader
        menu = {}
        menu_order = []
        default = 0  # type: str | int # is mapped to str for Bootloader(..., default)
        timeout = None
        serial = None
        title = None
        hypervisor = None
        hypervisor_args = None
        kernel = None
        kernel_args = None
        initrd = None
        root = None
        menu_entry_extra = None
        menu_entry_contents = []  # type: list[str]
        boilerplate = []  # type: list[str]
        boilerplates = []  # type: list[list[str]]
        entry_format = Grub2Format.MULTIBOOT2

        def create_label(title):
            global _counter

            if title == branding.PRODUCT_BRAND:
                return 'xe'
            if title.endswith('(Serial)'):
                return 'xe-serial'
            if title.endswith('Safe Mode'):
                return 'safe'
            if title.endswith('upgrade'):
                return 'upgrade'
            if ' / ' in title:
                if '(Serial,' in title:
                    return 'fallback-serial'
                else:
                    return 'fallback'
            _counter += 1
            return "label%d" % _counter

        def parse_boot_entry(line):
            parts = line.split(None, 2)  # Split into at most 3 parts
            entry = parts[1] if len(parts) > 1 else ""
            args = parts[2] if len(parts) > 2 else ""
            return entry, args

        fh = open_textfile(src_file, "r")
        try:
            for line in fh:
                l = line.strip()
                menu_match = re.match(r"menuentry ['\"]([^']*)['\"](.*){", l)

                # Only parse unindented default and timeout lines to prevent
                # changing these lines in if statements.
                if l.startswith('set default=') and l == line.rstrip():
                    default = l.split('=')[1]
                    match = re.match(r"['\"](.*)['\"]$", default)
                    if match:
                        default = match.group(1)
                elif l.startswith('set timeout=') and l == line.rstrip():
                    timeout = int(l.split('=')[1]) * 10
                elif l.startswith('serial'):
                    match = re.match(r"serial --unit=(\d+) --speed=(\d+)", l)
                    if match:
                        serial = {
                            'port': int(match.group(1)),
                            'baud': int(match.group(2)),
                        }
                elif l.startswith('terminal_'):
                    pass
                elif menu_match:
                    title = menu_match.group(1)
                    menu_entry_extra = menu_match.group(2)
                    if len(boilerplates) == 0:
                        # Add boilerplate to read override entry from environment
                        # block if not present
                        override_bp = False
                        for boilerplate_line in boilerplate:
                            if 'load_env' in boilerplate_line:
                                override_bp = True
                                break
                        if not override_bp:
                            extra = ['if [ -s $prefix/grubenv ]; then',
                                     '\tload_env',
                                     'fi',
                                     '',
                                     'if [ -n "$override_entry" ]; then',
                                     '\tset default=$override_entry',
                                     'fi',
                                     '']
                            boilerplate += extra
                    boilerplates.append(boilerplate)
                    boilerplate = []
                elif title:
                    if l.startswith("multiboot2"):
                        hypervisor, hypervisor_args = parse_boot_entry(l)
                    elif l.startswith("xen_hypervisor"):
                        entry_format = Grub2Format.XEN_BOOT
                        hypervisor, hypervisor_args = parse_boot_entry(l)
                    elif l.startswith("module2"):
                        if not hypervisor:
                            raise RuntimeError("Need a multiboot2 kernel")
                        if kernel:
                            initrd = l.split(None, 1)[1]
                        else:
                            kernel, kernel_args = parse_boot_entry(l)
                    elif l.startswith("xen_module"):
                        if not hypervisor:
                            raise RuntimeError("Need a hypervisor")
                        if kernel:
                            initrd = l.split(None, 1)[1]
                        else:
                            kernel, kernel_args = parse_boot_entry(l)
                    elif l.startswith("linux"):
                        entry_format = Grub2Format.LINUX
                        kernel, kernel_args = parse_boot_entry(l)
                    elif l.startswith("initrd"):
                        if not kernel:
                            raise RuntimeError("Need a kernel")
                        initrd = l.split(None, 1)[1]
                    elif l.startswith("search --label --set root"):
                        root = l.split()[4]
                    elif l == "}":
                        label = create_label(title)
                        menu_order.append(label)
                        menu[label] = MenuEntry(hypervisor = hypervisor,
                                                hypervisor_args = hypervisor_args,
                                                kernel = kernel,
                                                kernel_args = kernel_args,
                                                initrd = initrd, title = title,
                                                root = root)
                        menu[label].extra = menu_entry_extra
                        menu[label].contents = menu_entry_contents
                        menu[label].entry_format = entry_format

                        title = None
                        hypervisor = None
                        hypervisor_args = None
                        kernel = None
                        kernel_args = None
                        initrd = None
                        root = None
                        menu_entry_extra = None
                        menu_entry_contents = []
                        entry_format = Grub2Format.MULTIBOOT2

                    else:
                        menu_entry_contents.append(line.rstrip())
                else:
                    boilerplate.append(line.rstrip())

            # Try parse default as an index into the menu_order list.
            # If this fails, it is probably a string, so leave it unchanged.
            try:
                default = menu_order[int(default)]
            except (ValueError, KeyError):
                pass
        finally:
            fh.close()

        env_block = os.path.join(os.path.dirname(src_file), 'grubenv')
        bootloader = cls('grub2', src_file, menu, menu_order, default,
                         timeout, serial, env_block = env_block)
        bootloader.boilerplate = boilerplates
        return bootloader

    @classmethod
    def loadExisting(cls, root = '/'):
        # type: (str) -> Bootloader
        if os.path.exists(os.path.join(root, "boot/efi/EFI/xenserver/grub.cfg")):
            return cls.readGrub2(os.path.join(root, "boot/efi/EFI/xenserver/grub.cfg"))
        elif os.path.exists(os.path.join(root, "boot/grub/grub.cfg")):
            return cls.readGrub2(os.path.join(root, "boot/grub/grub.cfg"))
        elif os.path.exists(os.path.join(root, "boot/grub2/grub.cfg")):
            return cls.readGrub2(os.path.join(root, "boot/grub2/grub.cfg"))
        else:
            raise RuntimeError("No existing bootloader configuration found")

    def writeGrub2(self, dst_file = None):
        if dst_file and hasattr(dst_file, 'name'):
            fh = dst_file
        else:
            fh = open_textfile(cast(str, dst_file), "w")

        if self.serial:
            print("serial --unit=%s --speed=%s" % (self.serial['port'],
                                                   self.serial['baud']), file=fh)
            print("terminal_input serial console", file=fh)
            print("terminal_output serial console", file=fh)
        if self.default:
            for i in range(len(self.menu_order)):
                if self.menu_order[i] == self.default:
                    print("set default=%d" % i, file=fh)
                    break
            else:
                print("set default='%s'" % str(self.default), file=fh)
        if self.timeout:
            print("set timeout=%d" % (self.timeout // 10), file=fh)

        boilerplate = getattr(self, 'boilerplate', [])[:]
        boilerplate.reverse()

        for label in self.menu_order:
            m = self.menu[label]

            if boilerplate:
                text = boilerplate.pop()
                if text:
                    print("\n".join(text), file=fh)

            extra = m.extra if m.extra else ' '
            print("menuentry '%s'%s{" % (m.title, extra), file=fh)

            try:
                contents = "\n".join(m.contents)
                if contents:
                    print(contents, file=fh)
            except AttributeError:
                pass

            if m.root:
                print("\tsearch --label --set root %s" % m.root, file=fh)

            if ((m.entry_format is None and m.hypervisor) or
                    m.entry_format == Grub2Format.MULTIBOOT2):
                print("\tmultiboot2 %s %s" % (m.hypervisor, m.hypervisor_args), file=fh)
                if m.kernel:
                    print("\tmodule2 %s %s" % (m.kernel, m.kernel_args), file=fh)
                if m.initrd:
                    print("\tmodule2 %s" % m.initrd, file=fh)
            elif ((m.entry_format is None and not m.hypervisor) or
                    m.entry_format == Grub2Format.LINUX):
                print("\tlinux %s %s" % (m.kernel, m.kernel_args), file=fh)
                if m.initrd:
                    print("\tinitrd %s" % m.initrd, file=fh)
            elif m.entry_format == Grub2Format.XEN_BOOT:
                print("\txen_hypervisor %s %s" % (m.hypervisor, m.hypervisor_args), file=fh)
                if m.kernel:
                    print("\txen_module %s %s" % (m.kernel, m.kernel_args), file=fh)
                if m.initrd:
                    print("\txen_module %s" % m.initrd, file=fh)
            else:
                raise AssertionError("Unreachable")

            print("}", file=fh)
        if not hasattr(dst_file, 'name'):
            fh.close()

    def commit(self, dst_file = None):
        if not dst_file:
            dst_file = self.src_file

        # write to temp file in final destination directory
        fd, tmp_file = tempfile.mkstemp(dir = os.path.dirname(dst_file))

        assert self.src_fmt == 'grub2'
        self.writeGrub2(tmp_file)

        # atomically replace destination file
        os.close(fd)
        os.rename(tmp_file, dst_file)

    def setNextBoot(self, entry):
        if entry not in self.menu:
            return False
        if self.env_block is None:
            return False

        clear_default = ['\tunset override_entry', '\tsave_env override_entry']
        if clear_default[0] not in self.menu[entry].contents:
            self.menu[entry].contents = clear_default + self.menu[entry].contents

        for i in range(len(self.menu_order)):
            if self.menu_order[i] == entry:
                return self.setGrubVariable('override_entry=%d' % i)

        return False

    def setGrubVariable(self, var):
        if self.env_block is None:
            raise AssertionError("No grubenv file")
        cmd = ['grub-editenv', self.env_block, 'set', var]
        return xcp.cmd.runCmd(cmd) == 0

    @classmethod
    def newDefault(cls, kernel_link_name, initrd_link_name, root = '/'):
        b = cls.loadExisting(root)
        if b.menu[b.default].kernel != kernel_link_name:
            backup = []
            if not os.path.exists(os.path.join(root, kernel_link_name[1:])):
                raise RuntimeError("kernel symlink not found")
            if not os.path.exists(os.path.join(root, initrd_link_name[1:])):
                raise RuntimeError("initrd symlink not found")
            old_kernel_link = b.menu[b.default].kernel
            old_ver = 'old'
            m = re.search(r'(-\d+\.\d+)-', old_kernel_link)
            if m:
                old_ver = m.group(1)

            for k, v in b.menu.items():
                if v.kernel == old_kernel_link:
                    c = copy.deepcopy(v)
                    if c.title:
                        c.title += " (%s)" % old_ver
                    backup.append((k+old_ver, c))
                    v.kernel = kernel_link_name
                    v.initrd = initrd_link_name

            if len(backup) > 0:
                for l, e in backup:
                    b.append(l, e)
            b.commit()
