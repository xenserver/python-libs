#!/usr/bin/env python

import unittest, sys

try:
    import xcp
except ImportError:
    print >>sys.stderr, "Must run with run-test.sh"
    sys.exit(1)

from xcp.dom0 import default_memory, parse_mem, default_vcpus

class TestDom0(unittest.TestCase):

    def test_default_memory(self):
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
            calculated = default_memory(host_gib * 1024 * 1024)
            self.assertEqual(calculated, expected)

    def test_parse_mem_arg(self):
        k = 1024
        M = 1024*1024
        G = 1024*1024*1024

        test_args = [
            # Invalid options
            ("", (None, None, None)),
            ("option", (None, None, None)),
            ("option=123", (None, None, None)),
            ("dom0_mem", (None, None, None)),
            ("dom0_mem=bad", (None, None, None)),
            # Values and units
            ("dom0_mem=100", (100*k, None, None)), # defaults to KiB
            ("dom0_mem=-100", (-100*k, None, None)), # negative
            ("dom0_mem=100b", (100, None, None)),
            ("dom0_mem=100B", (100, None, None)),
            ("dom0_mem=100k", (100*k, None, None)),
            ("dom0_mem=100K", (100*k, None, None)),
            ("dom0_mem=100m", (100*M, None, None)),
            ("dom0_mem=100M", (100*M, None, None)),
            ("dom0_mem=100g", (100*G, None, None)),
            ("dom0_mem=100G", (100*G, None, None)),
            # Combinations
            ("dom0_mem=100,min:200,max:300", (100*k, 200*k, 300*k)),
            ("dom0_mem=min:100,200,max:300", (200*k, 100*k, 300*k)),
            # Bad prefixes etc.  Some of these look odd but this is
            # the behaviour of Xen itself.
            ("dom0_mem=bad:100,200", (200*k, None, None)),
            ("dom0_mem=100,bad", (None, None, None)),
            ("dom0_mem=bad,100", (100*k, None, None)),
            ("dom0_mem=bad,max:100", (None, None, 100*k)),
            # Typical values
            ("dom0_mem=752M", (752*M, None, None)),
            ("dom0_mem=752M,max:752M", (752*M, None, 752*M)),
            ]

        for arg, expected in test_args:
            calculated = parse_mem(arg)
            self.assertEqual(calculated, expected)

    def test_default_vcpus(self):
        test_values = [
            (0, 1), # Special case: Zero
            (1, 1), # Minimum
            (4, 4),
            (8, 8),
            (16, 16), # 16 vCPUs threshold
            (17, 16), # Above threshold
            (24, 16),
            ]

        for host_pcpus, expected in test_values:
            calculated = default_vcpus(host_pcpus)
            self.assertEqual(calculated, expected)

if __name__ == "__main__":
    sys.exit(unittest.main())
