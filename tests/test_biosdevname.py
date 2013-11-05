#!/usr/bin/env python

import unittest, sys, os, os.path as path

try:
    import xcp
except ImportError:
    print >>sys.stderr, "Must run with run-test.sh"
    sys.exit(1)


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


if __name__ == "__main__":
    sys.exit(unittest.main())
