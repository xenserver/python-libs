# -*- coding: utf-8 -*-
import sys
import unittest
from os import environ

import pyfakefs.fake_filesystem_unittest
import pytest
from mock import Mock, patch

from xcp.pci import PCI, PCIDevices, PCIIds

if sys.version_info >= (3, 6):
    from pytest_subprocess.fake_process import FakeProcess

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


if sys.version_info >= (2, 7):
    def assert_videoclass_devices(ids, devs):  # type: (PCIIds, PCIDevices) -> None
        """Verification function for checking the otuput of PCIDevices.findByClass()"""
        video_class = ids.lookupClass('Display controller')
        assert video_class == ["03"]
        sorted_devices = sorted(devs.findByClass(video_class),
                                key=lambda x: x['id'])

        # Assert devs.findByClass() finding 3 GPUs from tests/data/lspci-mn in our mocked PCIIds DB:
        assert len(sorted_devices) == 3

        # For each of the found devices, assert these expected values:
        for (video_dev,
             num_functions,
             vendor,
             device,
             subdevice,
        ) in zip(sorted_devices,
            # 1: Number of other PCI device functions shown by mocked lspci in this PCI slot:
            (
                1,
                0,
                5,
            ),
            # 2: GPU Vendor
            (
                "Advanced Micro Devices, Inc. [AMD/ATI]",
                "Advanced Micro Devices, Inc. [AMD/ATI]",
                "Advanced Micro Devices, Inc. [AMD/ATI]",
            ),
            # 3: GPU Device name
            (
                "Navi 14 [Radeon RX 5500/5500M / Pro 5500M]",
                "Hawaii XT / Grenada XT [Radeon R9 290X/390X]",
                "Renoir",
            ),
            # 4: GPU Subdevice name
            (
                None,
                "R9 290X IceQ X² Ultra Turbo Overdrive³ USB 3.2 SuperSpeed Edition",
                None,
            ),
        ):
            assert len(devs.findRelatedFunctions(video_dev["id"])) == num_functions
            assert ids.findVendor(video_dev["vendor"]) == vendor
            assert ids.findDevice(video_dev["vendor"], video_dev["device"]) == device
            # Expect that we can lookup the subdevice and get the name of the subdevice, if found:
            assert ids.findSubdevice(video_dev["subvendor"], video_dev["subdevice"]) == subdevice

        assert len(devs.findRelatedFunctions("00:18.1")) == 7


class TestPCIIdsFailure(unittest.TestCase):
    def tests_nodb(self):
        with patch("xcp.pci.os.path.exists") as exists_mock:
            exists_mock.return_value = False
            with self.assertRaises(Exception):
                PCIIds.read()
        exists_mock.assert_called_once_with("/usr/share/hwdata/pci.ids")


if sys.version_info >= (2, 7):
    def test_videoclass_without_mock():
        """
        Verifies that xcp.pci uses the open() and Popen() correctly across versions.
        Tests PCIIds.read() and PCIDevices() without mock for verifying compatibility
        with all Python versions.
        (The old test using moc could not detect a missing step in the Py3 migration)
        """
        with pyfakefs.fake_filesystem_unittest.Patcher() as p:
            assert p.fs
            p.fs.add_real_file("tests/data/pci.ids", target_path="/usr/share/hwdata/pci.ids")
            ids = PCIIds.read()
        saved_PATH = environ["PATH"]
        environ["PATH"] = "tests/data"  # Let PCIDevices() call Popen("tests/data/lspci")
        assert_videoclass_devices(ids, PCIDevices())
        environ["PATH"] = saved_PATH

if sys.version_info >= (3, 0):
    @pytest.fixture()
    def pytest_popen_fixture(request, fp):
        """PyTest fixture for use by FTPAccessorTestCase to get the ftpserver object"""
        request.cls.fp = fp

    def test_videoclass_by_mock_calls(fp):
        with patch("xcp.pci.os.path.exists") as exists_mock, patch(
            "xcp.pci.open_with_codec_handling"
        ) as open_mock, open("tests/data/pci.ids", encoding="utf-8") as fake_data:
            exists_mock.return_value = True
            open_mock.return_value.__iter__ = Mock(return_value=iter(fake_data))
            ids = PCIIds.read()
        exists_mock.assert_called_once_with("/usr/share/hwdata/pci.ids")
        open_mock.assert_called_once_with("/usr/share/hwdata/pci.ids", encoding="utf-8")
        assert_videoclass_devices(ids, mock_lspci_using_open_testfile(fp))

    def mock_lspci_using_open_testfile(fp):
        """Mock xcp.pci.PCIDevices.Popen() using open(tests/data/lspci-mn)"""
        with open("tests/data/lspci-mn", "rb") as fake_data:
            assert isinstance(fp, FakeProcess)
            fp.register_subprocess(["lspci", "-mn"], stdout=fake_data.read())
        return PCIDevices()
