#!/usr/bin/env python

import unittest, sys

try:
    import xcp
except ImportError:
    print >>sys.stderr, "Must run with run-test.sh to bind mount 'xcp'"
    sys.exit(1)

from xcp.dom0_memory import default_dom0_memory

class TestDom0Memory(unittest.TestCase):

    def test_default_dom0_memory(self):
        test_values = [
            (0, 752),         # Special case: zero
            (1, 752),         # Below min
            (2, 752),         # Min
            (23, 752),        # Below 2 GiB threshold
            (24, 2*1024),     # 2 GiB Threshold
            (47, 2*1024),     # Below 3 GiB threshold
            (48, 3*1024),     # 3 GiB threshold
            (63, 3*1024),     # Below 4 GiB threshold
            (64, 4*1024),     # 4 GiB threshold
            (1024, 4*1024),   # Max
            (2*1024, 4*1024), # Above max
            ]

        for host_gib, dom0_mib in test_values:
            expected = dom0_mib * 1024;
            calculated = default_dom0_memory(host_gib * 1024 * 1024)
            self.assertEqual(calculated, expected)

if __name__ == "__main__":
    unittest.main()
