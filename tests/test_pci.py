# -*- coding: utf-8 -*-
# pylint: disable=unspecified-encoding  # we pass encoding using kwargs

import os
import subprocess
import unittest
from hashlib import md5

import pyfakefs.fake_filesystem_unittest  # type: ignore[import]
from mock import Mock, patch

from xcp.utf8mode import open_textmode, popen_textmode
from xcp.pci import PCI, PCIIds, PCIDevices

class TestInvalid(unittest.TestCase):

    def test_invalid_types(self):
        with self.assertRaises(TypeError):
            PCI(0)
        with self.assertRaises(TypeError):
            PCI((0,))
        with self.assertRaises(TypeError):
            PCI([])
        with self.assertRaises(TypeError):
            PCI({})

    def test_invalid_format(self):
        pass

class TestValid(unittest.TestCase):

    def test_null_with_segment(self):

        c = PCI("0000:00:00.0")

        self.assertEqual(c.segment, 0)
        self.assertEqual(c.bus, 0)
        self.assertEqual(c.device, 0)
        self.assertEqual(c.function, 0)

        self.assertEqual(c.integer, 0)


    def test_null_without_segment(self):

        c = PCI("00:00.0")

        self.assertEqual(c.segment, 0)
        self.assertEqual(c.bus, 0)
        self.assertEqual(c.device, 0)
        self.assertEqual(c.function, 0)

        self.assertEqual(c.integer, 0)

    def test_valid(self):

        c = PCI("8765:43:1f.3")

        self.assertEqual(c.segment, 0x8765)
        self.assertEqual(c.bus, 0x43)
        self.assertEqual(c.device, 0x1f)
        self.assertEqual(c.function, 0x3)

    def test_equality(self):

        self.assertEqual(PCI("0000:00:00.0"), PCI("00:00.0"))


class TestPCIIds(unittest.TestCase):
    pciids_file_md5sum = "291f2026f14725ab9eed93f03ec4e522"

    def setUp(self):
        """
        To test the real open() and Popen() API usage of xcp.pci, this enables test cases
        which don't mock open() and popen(), but use small shims to wrap the calls.
        """
        # Used for test cases which don't mock in order to test the real Popen() API:
        subprocess.Popen = self.PopenWrapper  # type: ignore[misc]
        self.check("tests/data/pci.ids", self.pciids_file_md5sum)

    class PopenWrapper(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            """Wrap Popen(), replace [lspci, -mn] with [cat, tests/data/lspci-mn]"""
            kwargs["args"] = args
            if args == (["lspci", "-mn"],):
                kwargs["args"] = ["cat", "tests/data/lspci-mn"]
            super(subprocess.Popen, self).__init__(**kwargs)

    def test_videoclass_using_wrappers(self):
        """Variant of tests_videoclass() using wrapped calls, without mock"""
        with open("tests/data/pci.ids", "rb") as pciids:
            pciids_data = pciids.read()

        with pyfakefs.fake_filesystem_unittest.Patcher():
            self.create_pciids_file(pciids_data)
            self.check("/usr/share/hwdata/pci.ids", self.pciids_file_md5sum)
            ids = PCIIds.read()

        video_class = ids.lookupClass("Display controller")
        self.verify_videoclass_devices(ids, PCIDevices(), video_class)

    def tests_nodb(self):
        with patch("xcp.pci.os.path.exists") as exists_mock:
            exists_mock.return_value = False
            with self.assertRaises(Exception):
                PCIIds.read()
        exists_mock.assert_called_once_with("/usr/share/hwdata/pci.ids")

    def tests_videoclass(self):
        with patch("xcp.pci.os.path.exists") as exists_mock, \
             patch("xcp.pci.utf8open") as open_mock, \
             open("tests/data/pci.ids", **open_textmode) as fake_data:
            exists_mock.return_value = True
            open_mock.return_value.__iter__ = Mock(return_value=iter(fake_data))
            ids = PCIIds.read()
        exists_mock.assert_called_once_with("/usr/share/hwdata/pci.ids")
        open_mock.assert_called_once_with("/usr/share/hwdata/pci.ids")
        video_class = ids.lookupClass('Display controller')
        self.assertEqual(video_class, ['03'])
        devs = self.get_mocked_gpus(video_class, ids)
        self.verify_videoclass_devices(ids, devs, video_class)

    def get_mocked_gpus(self, video_class, ids):
        """Lookup devices from tests/data/lspci-mn in this test's pci.ids database"""

        with patch("xcp.pci.subprocess.Popen") as popen_mock, \
             open("tests/data/lspci-mn", **popen_textmode) as fake_data:
            popen_mock.return_value.stdout.__iter__ = Mock(return_value=iter(fake_data))
            devs = PCIDevices()
        popen_mock.assert_called_once_with(['lspci', '-mn'], bufsize = 1,
                                           stdout = subprocess.PIPE, **popen_textmode)
        return devs

    def verify_videoclass_devices(self, ids, devs, video_class):
        self.assertEqual(video_class, ["03"])
        sorted_devices = sorted(devs.findByClass(video_class),
                                key=lambda x: x['id'])

        # Assert devs.findByClass() finding 3 GPUs from tests/data/lspci-mn in our mocked PCIIds DB:
        self.assertEqual(len(sorted_devices), 3)

        for (video_dev,
             num_functions,
             vendor,
             device,
             subdevice,
        ) in zip(sorted_devices,
                 # For each of the found devices, supply these expected values:
                 # 1: Number of other PCI device functions shown by mocked lspci in this PCI slot:
                 (1, 0, 5),
                 # 2: GPU Vendor
                 ("Advanced Micro Devices, Inc. [AMD/ATI]",
                  "Advanced Micro Devices, Inc. [AMD/ATI]",
                  "Advanced Micro Devices, Inc. [AMD/ATI]"),
                 # 3: GPU Device name
                 ("Navi 14 [Radeon RX 5500/5500M / Pro 5500M]",
                  "Hawaii XT / Grenada XT [Radeon R9 290X/390X]",
                  "Renoir"),
                 # 4: GPU Subdevice name
                 (None,
                  "R9 290X IceQ X² Turbo³",
                  None)
        ):
            self.assertEqual(len(devs.findRelatedFunctions(video_dev['id'])), num_functions)
            self.assertEqual(ids.findVendor(video_dev['vendor']), vendor)
            self.assertEqual(ids.findDevice(video_dev['vendor'], video_dev['device']), device)
            # Expect that we can lookup the subdevice and get the name of the subdevice, if found:
            self.assertEqual(ids.findSubdevice(video_dev['subvendor'], video_dev['subdevice']), subdevice)

        self.assertEqual(len(devs.findRelatedFunctions('00:18.1')), 7)

    def check(self, file, expected_checksum):
        with open(file, "rb") as fileobj:
            self.assertEqual(md5(fileobj.read()).hexdigest(), expected_checksum)

    def create_pciids_file(self, pciids):
        """Create pciids file, works as user using open() wrapped by pyfakefs wrapper"""
        os.mkdir("/usr")  # Python2.7 does not have makedirs()
        os.mkdir("/usr/share")
        os.mkdir("/usr/share/hwdata")
        with open("/usr/share/hwdata/pci.ids", "wb") as f:
            f.write(pciids)
