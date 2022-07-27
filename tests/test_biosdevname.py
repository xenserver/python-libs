import unittest

from xcp.net.biosdevname import has_ppn_quirks

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

