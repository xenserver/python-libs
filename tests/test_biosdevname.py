import unittest
from subprocess import PIPE

from mock import patch, Mock

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
        # sourcery skip: extract-method, inline-immediately-returned-variable, path-read
        with patch("xcp.net.biosdevname.Popen") as popen_mock:
            # pylint: disable=unspecified-encoding
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
        calls = popen_mock.call_args_list
        self.assertEqual(calls[0].args[0], ['/sbin/biosdevname', '--policy', 'physical', '-d'])
        self.assertEqual(calls[1].args[0], ['/sbin/biosdevname', '--policy', 'all_ethN', '-d'])
        popen_kwargs = {"stdout": PIPE, "stderr": PIPE, "universal_newlines": True}
        self.assertEqual(calls[0].kwargs, popen_kwargs)
        self.assertEqual(calls[1].kwargs, popen_kwargs)

        self.assertEqual(devices['eth0']['BIOS device'],
                         {'all_ethN': 'eth0', 'physical': 'em1'})
