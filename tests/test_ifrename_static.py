from __future__ import unicode_literals
import logging
import unittest
from copy import deepcopy

from io import StringIO

from xcp.net.ifrename.static import StaticRules
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
        sr = StaticRules()

        self.assertEqual(sr.path, None)
        self.assertEqual(sr.fd, None)
        self.assertEqual(sr.formulae, {})
        self.assertEqual(sr.rules, [])

        self.assertFalse(sr.load_and_parse())
        self.assertEqual(sr.formulae, {})
        self.assertEqual(sr.rules, [])

    def test_empty(self):

        fd = StringIO("")
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {})
        self.assertEqual(sr.rules, [])

    def test_comment(self):

        fd = StringIO("#comment")
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {})
        self.assertEqual(sr.rules, [])

    def test_comment_and_empty(self):

        fd = StringIO("\n # Another Comment\n ")
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {})
        self.assertEqual(sr.rules, [])

    def test_single_incorrect_mac(self):

        fd = StringIO('eth0:mac="foo"')
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {})
        self.assertEqual(sr.rules, [])

    def test_single_mac(self):

        fd = StringIO('eth0:mac="AB:CD:EF:AB:CD:EF"')
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {'eth0': ('mac', 'AB:CD:EF:AB:CD:EF')})
        self.assertEqual(sr.rules, [])

    def test_single_invalid_pci(self):

        fd = StringIO('eth0:pci="bar"')
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {})
        self.assertEqual(sr.rules, [])

    def test_single_pci(self):

        fd = StringIO('eth0:pci="0000:00:00.1"')
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("pci", "0000:00:00.1")})
        self.assertEqual(sr.rules, [])

    def test_single_pci_0index(self):

        fd = StringIO('eth0:pci="0000:00:00.1[0]"')
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("pci", "0000:00:00.1[0]")})
        self.assertEqual(sr.rules, [])

    def test_single_invalid_ppn(self):

        fd = StringIO('eth0:ppn="baz"')
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {})
        self.assertEqual(sr.rules, [])

    def test_single_ppn_embedded(self):

        fd = StringIO('eth0:ppn="em2"')
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("ppn", "em2")})
        self.assertEqual(sr.rules, [])

    def test_single_ppn_slot(self):

        fd = StringIO('eth0:ppn="p2p3"')
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("ppn", "p2p3")})
        self.assertEqual(sr.rules, [])

    def test_single_oldsytle_ppn_slot(self):
        # CA-82901 - Accept old-style PPNs but translate them to new-style
        fd = StringIO('eth0:ppn="pci2p3"')
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("ppn", "p2p3")})
        self.assertEqual(sr.rules, [])

    def test_single_label(self):

        fd = StringIO('eth0:label="somestring"')
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("label", "somestring")})
        self.assertEqual(sr.rules, [])

class TestLoadAndParseGuess(unittest.TestCase):

    def setUp(self):
        self.logbuf = StringIO()
        openLog(self.logbuf, logging.NOTSET)

    def tearDown(self):

        closeLogs()
        self.logbuf.close()

    def test_single_explicit_label(self):

        fd = StringIO("eth0=\"foo\"")
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("label", "foo")})
        self.assertEqual(sr.rules, [])

    def test_single_implicit_label(self):

        fd = StringIO("eth0=foo")
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("label", "foo")})
        self.assertEqual(sr.rules, [])

    def test_single_mac(self):

        fd = StringIO("eth0=00:00:00:00:00:00")
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("mac", "00:00:00:00:00:00")})
        self.assertEqual(sr.rules, [])

    def test_single_pci(self):

        fd = StringIO("eth0=0000:00:00.0")
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("pci", "0000:00:00.0")})
        self.assertEqual(sr.rules, [])

    def test_single_pci_index(self):

        fd = StringIO("eth0=0000:00:00.0[1]")
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("pci", "0000:00:00.0[1]")})
        self.assertEqual(sr.rules, [])

    def test_single_ppn_embedded(self):

        fd = StringIO("eth0=em4")
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("ppn", "em4")})
        self.assertEqual(sr.rules, [])

    def test_single_ppn_slot(self):

        fd = StringIO("eth0=p1p2")
        sr = StaticRules(fd = fd)

        self.assertTrue(sr.load_and_parse())
        self.assertEqual(sr.formulae, {"eth0": ("ppn", "p1p2")})
        self.assertEqual(sr.rules, [])


class TestGenerate(unittest.TestCase):

    def setUp(self):
        self.logbuf = StringIO()
        openLog(self.logbuf, logging.NOTSET)

        self.state = [
            MACPCI("01:23:45:67:89:0a", "0000:00:01.0", kname="side-11-eth2",
                   ppn="p1p1", label="Ethernet1"),
            MACPCI("03:23:45:67:89:0a", "0000:00:10.0", kname="side-12-eth34",
                   ppn="p2p1", label=""),
            MACPCI("03:23:45:67:89:0a", "0000:00:02.0", kname="side-4-eth23",
                   ppn="em1", label=""),
            MACPCI("04:23:45:67:89:0a", "0000:00:10.1", kname="side-123-eth23",
                   ppn="p2p2", label="")
            ]

    def tearDown(self):

        closeLogs()
        self.logbuf.close()

    def test_null(self):

        fd = StringIO('eth0:label="somestring"')
        sr = StaticRules(fd = fd)
        self.assertTrue(sr.load_and_parse())
        sr.generate([])

        self.assertEqual(sr.rules, [])

    def test_single_not_matching_state(self):

        fd = StringIO('eth0:label="somestring"')
        sr = StaticRules(fd = fd)
        self.assertTrue(sr.load_and_parse())
        sr.generate(self.state)

        self.assertEqual(sr.rules, [])

    def test_single_mac_matching(self):

        fd = StringIO('eth0:mac="01:23:45:67:89:0a"')
        sr = StaticRules(fd = fd)
        self.assertTrue(sr.load_and_parse())

        sr.generate(self.state)

        self.assertEqual(sr.rules,[
                MACPCI("01:23:45:67:89:0a", "0000:00:01.0", tname="eth0")
                ])

    def test_single_pci_matching(self):

        fd = StringIO('eth0:pci="0000:00:10.0"')
        sr = StaticRules(fd = fd)
        self.assertTrue(sr.load_and_parse())

        sr.generate(self.state)

        self.assertEqual(sr.rules,[
                MACPCI("03:23:45:67:89:0a", "0000:00:10.0", tname="eth0")
                ])

    def test_single_ppn_embedded_matching(self):

        fd = StringIO('eth0:ppn="em1"')
        sr = StaticRules(fd = fd)
        self.assertTrue(sr.load_and_parse())

        sr.generate(self.state)

        self.assertEqual(sr.rules,[
                MACPCI("03:23:45:67:89:0a", "0000:00:02.0", tname="eth0")
                ])

    def test_single_ppn_slot_matching(self):

        fd = StringIO('eth0:ppn="p2p2"')
        sr = StaticRules(fd = fd)
        self.assertTrue(sr.load_and_parse())

        sr.generate(self.state)

        self.assertEqual(sr.rules,[
                MACPCI("04:23:45:67:89:0a", "0000:00:10.1", tname="eth0")
                ])

    def test_single_label_matching(self):

        fd = StringIO('eth0:label="Ethernet1"')
        sr = StaticRules(fd = fd)
        self.assertTrue(sr.load_and_parse())

        sr.generate(self.state)

        self.assertEqual(sr.rules,[
                MACPCI("01:23:45:67:89:0a", "0000:00:01.0", tname="eth0")
                ])

    def test_ppn_quirks(self):
        # Test case taken from example on CA-75599

        fd = StringIO('eth0:ppn="em1"\n'
                      'eth1:ppn="em2"')
        sr = StaticRules(fd = fd)
        self.assertTrue(sr.load_and_parse())

        sr.generate([
                MACPCI("00:1E:67:31:59:89", "0000:00:19.0", kname="eth0",
                       ppn="em1", label="Intel 82579LM VPRO"),
                MACPCI("00:1E:67:31:59:88", "0000:02:00.0", kname="eth1",
                       ppn="em1", label="Intel 82574L")
                ])

        # The quirks test should kick in and prevent any ppn rules from
        # being generated
        self.assertEqual(sr.rules, [])


class TestMultiplePCI(unittest.TestCase):

    def setUp(self):
        self.logbuf = StringIO()
        openLog(self.logbuf, logging.NOTSET)
        self.state = [
            MACPCI("c8:cb:b8:d3:0c:ca", "0000:03:00.0", kname="eth0",
                   ppn="em1", label=""),
            MACPCI("c8:cb:b8:d3:0c:cb", "0000:03:00.1", kname="eth1",
                   ppn="em2", label=""),
            MACPCI("c8:cb:b8:d3:0c:ce", "0000:04:00.0", kname="eth2",
                   ppn="em3", label=""),
            MACPCI("c8:cb:b8:d3:0c:cf", "0000:04:00.0", kname="eth3",
                   ppn="", label="")
            ]

    def tearDown(self):

        closeLogs()
        self.logbuf.close()

    def test_pci_matching(self):

        fd = StringIO('eth0:pci="0000:04:00.0"\n'
                      'eth1:pci="0000:04:00.0[1]"')
        sr = StaticRules(fd = fd)
        self.assertTrue(sr.load_and_parse())

        sr.generate(self.state)

        self.assertEqual(set(sr.rules), set([
            MACPCI("c8:cb:b8:d3:0c:cf", "0000:04:00.0", tname="eth1"),
            MACPCI("c8:cb:b8:d3:0c:ce", "0000:04:00.0", tname="eth0")
        ]))

    def test_pci_matching_invert(self):

        fd = StringIO('eth0:pci="0000:04:00.0[1]"\n'
                      'eth1:pci="0000:04:00.0[0]"')
        sr = StaticRules(fd = fd)
        self.assertTrue(sr.load_and_parse())

        sr.generate(self.state)

        self.assertEqual(set(sr.rules), set([
            MACPCI("c8:cb:b8:d3:0c:ce", "0000:04:00.0", tname="eth1"),
            MACPCI("c8:cb:b8:d3:0c:cf", "0000:04:00.0", tname="eth0")
        ]))

    def test_pci_matching_mixed(self):

        fd = StringIO('eth0:ppn="em3"\n'
                      'eth1:pci="0000:04:00.0[1]"')
        sr = StaticRules(fd = fd)
        self.assertTrue(sr.load_and_parse())

        sr.generate(self.state)

        self.assertEqual(set(sr.rules), set([
            MACPCI("c8:cb:b8:d3:0c:cf", "0000:04:00.0", tname="eth0"),
            MACPCI("c8:cb:b8:d3:0c:ce", "0000:04:00.0", tname="eth1")
        ]))

    def test_pci_missing(self):

        fd = StringIO('eth0:pci="0000:03:00.0"\n'
                      'eth4:pci="0000:05:00.0"')
        sr = StaticRules(fd = fd)
        self.assertTrue(sr.load_and_parse())

        sr.generate(self.state)

        self.assertEqual(sr.rules,[
                MACPCI("c8:cb:b8:d3:0c:ca", "0000:03:00.0", tname="eth0")
                ])


class TestSave(unittest.TestCase):

    def setUp(self):
        self.logbuf = StringIO()
        openLog(self.logbuf, logging.NOTSET)

    def tearDown(self):

        closeLogs()
        self.logbuf.close()

    def test_empty(self):

        sr = StaticRules()
        self.assertEqual(sr.write(False), "")

    def test_one_valid(self):

        sr = StaticRules()
        sr.formulae = {"eth0": ("ppn", "p1p1"),
                       }

        desired_result = "eth0:ppn=\"p1p1\"\n"

        self.assertEqual(sr.write(False), desired_result)

    def test_one_invalid_method(self):

        sr = StaticRules()
        sr.formulae = {"eth0": ("ppf", "foobaz"),
                       }

        self.assertEqual(sr.write(False), "")


    def test_two_valid(self):

        sr = StaticRules()
        sr.formulae = {"eth0": ("ppn", "p1p1"),
                       "eth1": ("label", "Ethernet1"),
                       }

        desired_result = (
            "eth0:ppn=\"p1p1\"\n"
            "eth1:label=\"Ethernet1\"\n"
            )

        self.assertEqual(sr.write(False), desired_result)
