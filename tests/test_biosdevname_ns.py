"""Test biosdevname in a user namespace. Needs to be a new file because of a bug in pytest-forked"""
import re
import sys
import unittest
from os import system

import pytest
import pytest_forked  # pylint: disable=unused-import # Ensure pytest-forked is installed

import xcp.net.biosdevname

from .xcptestlib_unshare import CLONE_NEWUSER, disassociate_namespaces

if tuple(sys.version_info) == (3, 10):
    pytest.skip(allow_module_level=True)

def check_devices(self, devices):
    pci_bus_info = re.compile(r'\d*:?[a-f0-9]+:[a-f0-9]+\.[a-f0-9]')

    found_pci = False
    for interface, value in devices.items():
        assert interface[-1] in "0123456789"
        assert value["BIOS device"]
        assert value["Assigned MAC"]
        assert value["Driver"]
        if pci_bus_info.match(value['Bus Info']):
            found_pci = True
    assert found_pci


class TestDeviceNames(unittest.TestCase):
    biosdevname_check = system("biosdevname --version")

    @unittest.skipIf(biosdevname_check, "requires the biosdevname command to read interfaces")
    @pytest.mark.forked  # The isolated network namespace would cause issues for other test cases
    def test_calling_biosdevname(self):
        disassociate_namespaces(CLONE_NEWUSER)
        devices = xcp.net.biosdevname.all_devices_all_names()
        self.assertGreater(len(devices), 0)
        check_devices(self, devices)
