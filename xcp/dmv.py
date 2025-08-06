# Copyright (c) 2025, Citrix Inc.
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
import subprocess
import json
import re
import struct
import glob
import errno

from .compat import open_with_codec_handling

dmv_proto_ver = 0.1
err_proto_ver = 0.1

def get_all_kabi_dirs():
    """Return a list of (kabi_ver, updates_dir, dmv_dir) tuples for all kernel versions."""
    modules_root = "/lib/modules/"
    dirs = []
    for kabi_ver in os.listdir(modules_root):
        updates_dir = os.path.join(modules_root, kabi_ver, "updates")
        dmv_dir = os.path.join(modules_root, kabi_ver, "dmv")
        # not checking if updates_dir and dmv_dir exist here, will check later when use them
        dirs.append((kabi_ver, updates_dir, dmv_dir))
    return dirs

def note_offset(var_len):
    """Note section has 4 bytes padding"""
    ret = (((var_len - 1) & ~3) + 4) - var_len
    return ret

def get_active_variant(modules):
    """Check and report active driver"""
    # Check if any module in the modules is loaded
    for module in modules:
        # get 'module' from 'module.ko'
        module_name = os.path.splitext(module)[0]
        note_file = os.path.join("/sys/module", module_name, "notes/.note.XenServer")
        if not os.path.isfile(note_file):
            continue

        note_struct_size = struct.calcsize('III')
        with open(note_file, "rb") as n_file:
            for _ in range(3):
                note_hdr = struct.unpack('III', n_file.read(note_struct_size))
                n_file.read(note_offset(note_struct_size))
                vendor = n_file.read(note_hdr[0])
                n_file.read(note_offset(note_hdr[0]))
                content = n_file.read(note_hdr[1])[:-1]
                n_file.read(note_offset(note_hdr[1]))
                note_type = note_hdr[2]
                if vendor == b'XenServer' and note_type == 1:
                    variant = content.decode("ascii")
                    return variant
    return None

def get_loaded_modules(modules):
    """Return all loaded modules"""
    loaded_modules = []
    for module in modules:
        # get 'module' from 'module.ko'
        module_name = os.path.splitext(module)[0]
        note_file = os.path.join("/sys/module", module_name, "notes/.note.XenServer")
        if os.path.isfile(note_file):
            loaded_modules.append(module)
    return loaded_modules

def id_matches(id1, id2):
    if '*' in [id1, id2]:
        return True
    return id1 == id2

'''
driver_pci_ids example:
{
        "abc.ko": [
            {
                "vendor_id": "14e4",
                "device_id": "163c",
                "subvendor_id": "*",
                "subdevice_id": "*"
            },
            {
                "vendor_id": "14e4",
                "device_id": "163b",
                "subvendor_id": "*",
                "subdevice_id": "*"
            }],
        "de.ko": [
            {
                "vendor_id": "eees",
                "device_id": "163c",
                "subvendor_id": "*",
                "subdevice_id": "*"
            },
            {
                "vendor_id": "14f4",
                "device_id": "16db",
                "subvendor_id": "2123",
                "subdevice_id": "1123"
            }]
}
'''
def pci_matches(present_pci_id, driver_pci_ids):
    """Check if present PCI ID matches any of the driver PCI IDs."""
    merged_driver_pci_id_list = []
    for module_pci_list in driver_pci_ids.values():
        for item in module_pci_list:
            merged_driver_pci_id_list.append(item)

    for pci_id in merged_driver_pci_id_list:
        if (id_matches(present_pci_id['vendor'], pci_id['vendor_id']) and
            id_matches(present_pci_id['device'], pci_id['device_id']) and
            id_matches(present_pci_id['subvendor'], pci_id['subvendor_id']) and
            id_matches(present_pci_id['subdevice'], pci_id['subdevice_id'])):
            return True
    return False

def hardware_present(lspci_out, pci_ids):
    """Check if supported hardware is fitted"""
    if not pci_ids or not lspci_out:
        return False

    # 'lspci -nm' output:
    # 00:15.3 "0604" "15ad" "07a0" -r01 -p00 "15ad" "07a0"
    # 00:01.0 "0604" "8086" "7191" -r01 -p00 "" ""
    lspci_expression = r'''
        ^
        (?P<slot>\S+)                # PCI slot (00:15.3)
        \s+
        "(?P<class>[^"]*)"           # Device class (0604)
        \s+
        "(?P<vendor>[^"]*)"          # Vendor (15ad)
        \s+
        "(?P<device>[^"]*)"          # Device name (07a0)
        \s*
        (?:-(?P<revision>\S+))?      # Optional revision (-r01)
        \s*
        (?:-(?P<progif>\S+))?        # Optional programming interface (-p00)
        \s+
        "(?P<subvendor>[^"]*)"       # Subvendor (15ad or empty)
        \s+
        "(?P<subdevice>[^"]*)"       # Subdevice (07a0 or empty)
        $
    '''
    lscpi_pattern = re.compile(lspci_expression, re.VERBOSE | re.MULTILINE)
    for match in lscpi_pattern.finditer(lspci_out):
        if pci_matches(match.groupdict(), pci_ids):
            return True
    return False

def variant_selected(modules, updates_dir):
    """Check and return which driver is selected"""
    # Check if any module in the modules is selected
    for module in modules:
        slink_file = os.path.join(updates_dir, module)
        if os.path.islink(slink_file):
            module_path = os.path.realpath(slink_file)
            module_dir = os.path.dirname(module_path)
            info_file = os.path.join(module_dir, "info.json")
            with open(info_file, "r", encoding="ascii") as json_file:
                json_data = json.load(json_file)
                variant = json_data["variant"]

            return variant
    return None

class DriverMultiVersion(object):
    def __init__(self, updates_dir, lspci_out, runtime=False):
        self.updates_dir = updates_dir
        self.lspci_out = lspci_out
        self.runtime = runtime

    def variant_selected(self, modules):
        """Check and return which driver is selected"""
        # Check if any module in the modules is selected
        for module in modules:
            slink_file = os.path.join(self.updates_dir, module)
            if os.path.islink(slink_file):
                module_path = os.path.realpath(slink_file)
                module_dir = os.path.dirname(module_path)
                info_file = os.path.join(module_dir, "info.json")
                with open(info_file, "r", encoding="ascii") as json_file:
                    json_data = json.load(json_file)
                    variant = json_data["variant"]

                return variant
        return None

    def parse_dmv_info(self, fpath):
        """Populate dmv list with information"""
        json_data = None
        with open_with_codec_handling(fpath, encoding="ascii") as json_file:
            json_data = json.load(json_file)
            json_formatted = {
                "type": json_data["category"],
                "friendly_name": json_data["name"],
                "description": json_data["description"],
                "info": json_data["name"],
                "variants": {
                    json_data["variant"]: {
                        "version": json_data["version"],
                        "hardware_present": hardware_present(
                            self.lspci_out.stdout,
                            json_data["pci_ids"]),
                        "priority": json_data["priority"],
                        "status": json_data["status"]}}}
            if self.runtime:
                json_formatted["selected"] = self.variant_selected(
                    json_data["pci_ids"].keys())
                json_formatted["active"] =  get_active_variant(
                    json_data["pci_ids"].keys())
                json_formatted["loaded modules"] = get_loaded_modules(
                    json_data["pci_ids"].keys())
        return json_data, json_formatted

class DriverMultiVersionManager(object):
    def __init__(self, runtime=False):
        self.runtime = runtime
        self.dmv_list = {
            "protocol": {"version": dmv_proto_ver},
            "operation": {"reboot": False},
            "drivers": {}
        }
        self.errors_list = {
            "version": err_proto_ver,
            "exit_code": 0,
            "message": "Success"
        }

    def merge_jsondata(self, oldone, newone):
        variants = oldone["variants"]
        for k, v in newone["variants"].items():
            variants[k] = v

        json_formatted = {
             "type": oldone["type"],
             "friendly_name": oldone["friendly_name"],
             "description": oldone["description"],
             "info": oldone["info"],
             "variants": variants}

        if self.runtime:
            selected = None
            if oldone["selected"] is not None:
                selected = oldone["selected"]
            elif newone["selected"] is not None:
                selected = newone["selected"]
            json_formatted["selected"] = selected

            active = None
            if oldone["active"] is not None:
                active = oldone["active"]
            elif newone["active"] is not None:
                active = newone["active"]
            json_formatted["active"] = active

            loaded = oldone["loaded modules"] + newone["loaded modules"]
            json_formatted["loaded modules"] = loaded

        self.dmv_list["drivers"][oldone["info"]] = json_formatted

    def process_dmv_data(self, json_data, json_formatted):
        if not json_data["name"] in self.dmv_list["drivers"]:
            self.dmv_list["drivers"][json_data["name"]] = json_formatted
        elif self.dmv_list["drivers"][json_data["name"]] is None:
            self.dmv_list["drivers"][json_data["name"]] = json_formatted
        else:
            self.merge_jsondata(self.dmv_list["drivers"][json_data["name"]], json_formatted)

    def parse_dmv_list(self):
        lspci_out = subprocess.run(["lspci", '-nm'], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, universal_newlines=True,
                                   check=True)
        for _, updates_dir, dmv_dir in get_all_kabi_dirs():
            if not os.path.isdir(dmv_dir):
                continue
    
            for path, _, files in os.walk(dmv_dir):
                if "info.json" not in files:
                    continue

                fpath = os.path.join(path, "info.json")
                d = DriverMultiVersion(updates_dir, lspci_out, self.runtime)
                json_data, json_formatted = d.parse_dmv_info(fpath)
                self.process_dmv_data(json_data, json_formatted)

    def parse_dmv_file(self, fpath):
        lspci_out = subprocess.run(["lspci", '-nm'], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, universal_newlines=True,
                                   check=True)
        d = DriverMultiVersion("", lspci_out)
        json_data, json_formatted = d.parse_dmv_info(fpath)
        self.process_dmv_data(json_data, json_formatted)

    def get_dmv_list(self):
        return self.dmv_list

    def create_dmv_symlink(self, name, ver):
        created = False
        for _, updates_dir, dmv_dir in get_all_kabi_dirs():
            module_dir = os.path.join(dmv_dir, name, ver)
            module_files = glob.glob(os.path.join(module_dir, "**", "*.ko"), recursive=True)
            for module_file in module_files:
                # updates_dir may not exist
                os.makedirs(updates_dir, exist_ok=True)
                module_sym = os.path.join(updates_dir, os.path.basename(module_file))
                tmp_name = module_sym + ".tmp"
                try:
                    os.unlink(tmp_name)
                except FileNotFoundError:
                    pass
                os.symlink(module_file, tmp_name)
                os.rename(tmp_name, module_sym)
                created = True
                modules = [module_sym]
                input_data = "\n".join(modules) + "\n"
                subprocess.run(
                    ["/usr/sbin/weak-modules", "--no-initramfs", "--add-modules"],
                    input=input_data,
                    text=True,
                    check=True
                )
        if created:
            subprocess.run(["/usr/sbin/depmod", "-a"], check=True)
            uname_r = subprocess.run(["uname", '-r'], stdout=subprocess.PIPE, text=True,
                              check=True).stdout.strip()
            if os.path.exists("/usr/bin/dracut"):
                initrd_img = "/boot/initrd-" + uname_r + ".img"
                subprocess.run(["/usr/bin/dracut", "-f", initrd_img, uname_r], check=True)
            return True
        self.errors_list["exit_code"] = errno.ENOENT
        self.errors_list["message"] = os.strerror(errno.ENOENT)
        return False

    def get_dmv_error(self):
        return self.errors_list

    def set_dmv_error(self, errcode):
        self.errors_list["exit_code"] = errcode
        self.errors_list["message"] = os.strerror(errcode)
