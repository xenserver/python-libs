import unittest
from mock import patch, Mock

from xcp.dom0 import default_memory, parse_mem, default_vcpus

class TestDom0(unittest.TestCase):

    def test_default_memory(self):
        def mock_version(open_mock, version):
            file_mock = Mock()
            file_mock.readlines.return_value = iter(["PLATFORM_VERSION='%s'\n" % (version,)])
            open_mock.return_value.__enter__.return_value = file_mock

        # There are two possible sets of memory value.
        # test_values below is in layout: host_gib, scheme1, scheme2.
        # Scheme 1 has thresholds, described next to table lines,
        # while scheme 2 is continues from 1024 -> 8*1024.

        test_values = [
            (0, 752, 1024),           # Special case: zero
            (1, 752, 1088),           # Below min
            (2, 752, 1136),           # Min
            (23, 752, 2208),          # Below 2 GiB threshold
            (24, 2*1024, 2256),       # 2 GiB Threshold
            (47, 2*1024, 3440),       # Below 3 GiB threshold
            (48, 3*1024, 3488),       # 3 GiB threshold
            (63, 3*1024, 4256),       # Below 4 GiB threshold
            (64, 4*1024, 4304),       # 4 GiB threshold
            (1024, 4*1024, 8*1024),   # Max
            (2*1024, 4*1024, 8*1024), # Above max
            ]

        with patch("xcp.dom0.open") as open_mock:
            for host_gib, dom0_mib, _ in test_values:
                mock_version(open_mock, '2.8.0')
                expected = dom0_mib * 1024;
                calculated = default_memory(host_gib * 1024 * 1024)
                self.assertEqual(calculated, expected)

            open_mock.assert_called_with("/etc/xensource-inventory")

        with patch("xcp.dom0.open") as open_mock:
            for host_gib, _, dom0_mib in test_values:
                mock_version(open_mock, '2.9.0')
                expected = dom0_mib * 1024;
                calculated = default_memory(host_gib * 1024 * 1024)
                self.assertEqual(calculated, expected)

            open_mock.assert_called_with("/etc/xensource-inventory")

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
        G = 1024
        test_values = [
            (0, None, 1), # Special case: Zero
            (1, None, 1), # Minimum
            (4, None, 4),
            (8, None, 8),
            (8, 1*G, 4),
            (8, 3*G, 8),
            (8, 5*G, 8),
            (16, None, 16), # 16 vCPUs threshold
            (16, 1*G, 4),
            (16, 3*G, 8),
            (16, 5*G, 16),
            (17, None, 16), # Above threshold
            (24, None, 16),
            ]

        for host_pcpus, mem, expected in test_values:
            calculated = default_vcpus(host_pcpus, mem)
            self.assertEqual(calculated, expected)
