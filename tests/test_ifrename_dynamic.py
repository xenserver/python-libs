from __future__ import unicode_literals
import json
import logging
import unittest
from copy import deepcopy

from io import StringIO

from xcp.net.ifrename.dynamic import DynamicRules
from xcp.net.ifrename.macpci import MACPCI
from xcp.logger import LOG, openLog, closeLogs


class TestLoadAndParse(unittest.TestCase):

    def setUp(self):
        self.logbuf = StringIO()
        openLog(self.logbuf, logging.NOTSET)

    def tearDown(self):

        closeLogs()
        self.logbuf.close()

    def test_null(self):

        fd = StringIO("")
        dr = DynamicRules(fd=fd)

        self.assertTrue(dr.load_and_parse())

        self.assertEqual(dr.lastboot, [])
        self.assertEqual(dr.old, [])

    def test_empty(self):

        fd = StringIO(
            '{"lastboot":[],"old":[]}'
            )
        dr = DynamicRules(fd=fd)

        self.assertTrue(dr.load_and_parse())

        self.assertEqual(dr.lastboot, [])
        self.assertEqual(dr.old, [])

    def test_one_invalid(self):

        fd = StringIO(
            '{"lastboot":[["","",""]],"old":[]}'
            )
        dr = DynamicRules(fd=fd)

        self.assertTrue(dr.load_and_parse())

        self.assertEqual(dr.lastboot, [])
        self.assertEqual(dr.old, [])

    def test_one_valid_lastboot(self):

        fd = StringIO(
            '{"lastboot":[["01:23:45:67:89:0a","00:10.2","eth2"]],"old":[]}'
            )
        dr = DynamicRules(fd=fd)

        self.assertTrue(dr.load_and_parse())

        self.assertEqual(dr.lastboot,
                         [MACPCI("01:23:45:67:89:0a","00:10.2", tname="eth2")])
        self.assertEqual(dr.old, [])


    def test_one_valid_lastboot2(self):

        fd = StringIO(
            '{"lastboot":[],"old":[["01:23:45:67:89:0a","00:10.2","eth2"]]}'
            )
        dr = DynamicRules(fd=fd)

        self.assertTrue(dr.load_and_parse())

        self.assertEqual(dr.lastboot, [])
        self.assertEqual(dr.old,
                         [MACPCI("01:23:45:67:89:0a","00:10.2", tname="eth2")])

class TestGenerate(unittest.TestCase):

    def setUp(self):
        self.logbuf = StringIO()
        openLog(self.logbuf, logging.NOTSET)

    def tearDown(self):

        closeLogs()
        self.logbuf.close()

    def test_ppn_quirks(self):
        # Test case taken from example on CA-75599

        dr = DynamicRules()
        dr.formulae = { "eth0" : ("ppn", "em1"),
                        "eth1" : ("ppn", "em2")
                        }

        dr.generate([
                MACPCI("00:1E:67:31:59:89", "0000:00:19.0", kname="eth0",
                       ppn="em1", label="Intel 82579LM VPRO"),
                MACPCI("00:1E:67:31:59:88", "0000:02:00.0", kname="eth1",
                       ppn="em1", label="Intel 82574L")
                ])

        # The quirks test should kick in and prevent any ppn rules from
        # being generated
        self.assertEqual(dr.rules, [])

    def test_pci_matching_invert(self):

        dr = DynamicRules()
        dr.formulae = { "eth0" : ("pci", "0000:04:00.0[1]"),
                        "eth1" : ("pci", "0000:04:00.0")
                        }

        dr.generate([MACPCI("c8:cb:b8:d3:0c:ce", "0000:04:00.0", kname="eth0",
                            ppn="em1", label=""),
                     MACPCI("c8:cb:b8:d3:0c:cf", "0000:04:00.0", kname="eth1",
                            ppn="", label="")])

        self.assertEqual(set(dr.rules), set([
                MACPCI("c8:cb:b8:d3:0c:ce", "0000:04:00.0", tname="eth1"),
                MACPCI("c8:cb:b8:d3:0c:cf", "0000:04:00.0", tname="eth0")
        ]))

    def test_pci_missing(self):

        dr = DynamicRules()
        dr.formulae = {"eth0" : ("pci", "0000:04:00.0"),
                       "eth1" : ("pci", "0000:05:00.0")}

        dr.generate([MACPCI("c8:cb:b8:d3:0c:ce", "0000:04:00.0", kname="eth0",
                            ppn="em1", label="")])

        self.assertEqual(dr.rules, [
                MACPCI("c8:cb:b8:d3:0c:ce", "0000:04:00.0", tname="eth0")
                ])


class TestSave(unittest.TestCase):

    def setUp(self):
        self.logbuf = StringIO()
        openLog(self.logbuf, logging.NOTSET)

    def tearDown(self):

        closeLogs()
        self.logbuf.close()

    def test_one_invalid_lastboot(self):

        dr = DynamicRules()
        dr.lastboot = [["foo", "bar", "baz"]]

        json.loads(dr.write(False))

    def test_one_ibft_lastboot(self):

        dr = DynamicRules()
        dr.lastboot = [["00:1E:67:31:59:89", "0000:00:19.0", None]]

        self.assertEqual(json.loads(dr.write(False)), {'lastboot': [],
                                                       'old': []})
