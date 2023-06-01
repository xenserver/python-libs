"""Test biosdevname in a user namespace. Needs to be a new file because of a bug in pytest-forked"""
import unittest
from os import system

import pytest
import pytest_forked  # pylint: disable=unused-import # Ensure pytest-forked is installed

import xcp.net.biosdevname

from .xcptestlib_unshare import CLONE_NEWUSER, disassociate_namespaces


def check_devices(self, devices):
    for item in devices.items():
        assert item[0]
        assert item[1]["BIOS device"]
        assert item[1]["Assigned MAC"]
        assert item[1]["Bus Info"]
        assert item[1]["Driver"]


class TestDeviceNames(unittest.TestCase):
    biosdevname_check = system("biosdevname --version")

    @unittest.skipIf(biosdevname_check, "requires the biosdevname command to read interfaces")
    @pytest.mark.forked  # The isolated network namespace would cause issues for other test cases
    def test_calling_biosdevname(self):
        disassociate_namespaces(CLONE_NEWUSER)
        devices = xcp.net.biosdevname.all_devices_all_names()
        self.assertGreater(len(devices), 0)
        check_devices(self, devices)
