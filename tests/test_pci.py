#!/usr/bin/env python

import unittest, sys, os, os.path as path

try:
    import xcp
except ImportError:
    print >>sys.stderr, "Must run with run-test.sh to bind mount 'xcp'"
    sys.exit(1)

from xcp.pci import PCI

class TestInvalid(unittest.TestCase):

    def test_invalid_types(self):

        self.assertRaises(TypeError, PCI, 0)
        self.assertRaises(TypeError, PCI, 0L)
        self.assertRaises(TypeError, PCI, (0,))
        self.assertRaises(TypeError, PCI, [])
        self.assertRaises(TypeError, PCI, {})

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


    def test_null_with_segment(self):

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


if __name__ == "__main__":
    unittest.main()
