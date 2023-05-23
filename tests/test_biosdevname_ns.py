"""Test biosdevname in a user namespace. Needs to be a new file because of a bug in pytest-forked"""
import unittest
from os import system

import pytest  # type: ignore # for pyre in tox only
import pytest_forked  # type: ignore # pylint: disable=unused-import # This needs pytest-forked

import xcp.net.biosdevname

from .xcptestlib_unshare import CLONE_NEWUSER, disassociate_namespaces


def check_devices(self, devices):
    for item in devices.items():
        print(item[0])
        print(item[1]["BIOS device"])
        print(item[1]["Assigned MAC"])
        print(item[1]["Bus Info"])
        print(item[1]["Driver"])


class TestDeviceNames(unittest.TestCase):
    biosdevname_check = system("biosdevname --version")

    @unittest.skipIf(biosdevname_check, "requires the biosdevname command to read interfaces")
    @pytest.mark.forked  # The isolated network namespace would cause issues for other test cases
    def test_calling_biosdevname(self):
        disassociate_namespaces(CLONE_NEWUSER)
        devices = xcp.net.biosdevname.all_devices_all_names()
        self.assertGreater(len(devices), 0)
        check_devices(self, devices)
