import subprocess
import unittest
from mock import patch, Mock

from xcp import xcp_popen_text_kwargs
from xcp.net.biosdevname import has_ppn_quirks, all_devices_all_names

class TestQuirks(unittest.TestCase):

    def test_ppn_none(self):
        self.assertFalse(has_ppn_quirks([]))

    def test_ppn_empty(self):
        self.assertFalse(has_ppn_quirks([{},{},{}]))

    def test_ppn_false(self):
        self.assertFalse(has_ppn_quirks(
                [{"SMBIOS Instance": 1},
                 {"SMBIOS Instance": 2},
                 {"SMBIOS Instance": 3}
                 ]))

    def test_ppn_true(self):
        self.assertTrue(has_ppn_quirks(
                [{"SMBIOS Instance": 1},
                 {"SMBIOS Instance": 1}
                 ]))

class TestDeviceNames(unittest.TestCase):
    def test(self):
        with patch("xcp.net.biosdevname.Popen") as popen_mock:
            with open("tests/data/physical.biosdevname") as f:
                fake_output_1 = f.read()
            with open("tests/data/all_ethN.biosdevname") as f:
                fake_output_2 = f.read()
            communicate_mock = Mock(side_effect=iter([(fake_output_1, ""),
                                                      (fake_output_2, "")]))
            popen_mock.return_value.communicate = communicate_mock
            popen_mock.return_value.returncode = 0

            devices = all_devices_all_names()

        # check after the fact that we mocked the proper calls
        self.assertEqual(popen_mock.call_count, 2)
        popen_mock.assert_called_with(['/sbin/biosdevname', '--policy', 'all_ethN', '-d'],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      **xcp_popen_text_kwargs)

        calls = popen_mock.call_args_list
        self.assertEqual(calls[0].args[0], ['/sbin/biosdevname', '--policy', 'physical', '-d'])
        self.assertEqual(calls[1].args[0], ['/sbin/biosdevname', '--policy', 'all_ethN', '-d'])

        self.assertEqual(devices['eth0']['BIOS device'],
                         {'all_ethN': 'eth0', 'physical': 'em1'})
