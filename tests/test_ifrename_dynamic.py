#!/usr/bin/env python

import unittest, sys, os, os.path as path, logging, json
from copy import deepcopy

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

try:
    import xcp
except ImportError:
    print >>sys.stderr, "Must run with run-test.sh to bind mount 'xcp'"


from xcp.net.ifrename.dynamic import DynamicRules
from xcp.net.ifrename.macpci import MACPCI
from xcp.logger import LOG, openLog, closeLogs


class TestLoadAndParse(unittest.TestCase):

    def setUp(self):
        self.logbuf = StringIO.StringIO()
        openLog(self.logbuf, logging.NOTSET)

    def tearDown(self):

        closeLogs()
        self.logbuf.close()

    def test_null(self):

        fd = StringIO.StringIO("")
        dr = DynamicRules(fd=fd)

        self.assertTrue(dr.load_and_parse())

        self.assertEqual(dr.lastboot, [])
        self.assertEqual(dr.old, [])

    def test_empty(self):

        fd = StringIO.StringIO(
            '{"lastboot":[],"old":[]}'
            )
        dr = DynamicRules(fd=fd)

        self.assertTrue(dr.load_and_parse())

        self.assertEqual(dr.lastboot, [])
        self.assertEqual(dr.old, [])

    def test_one_invalid(self):

        fd = StringIO.StringIO(
            '{"lastboot":[["","",""]],"old":[]}'
            )
        dr = DynamicRules(fd=fd)

        self.assertTrue(dr.load_and_parse())

        self.assertEqual(dr.lastboot, [])
        self.assertEqual(dr.old, [])

    def test_one_valid_lastboot(self):

        fd = StringIO.StringIO(
            '{"lastboot":[["01:23:45:67:89:0a","00:10.2","eth2"]],"old":[]}'
            )
        dr = DynamicRules(fd=fd)

        self.assertTrue(dr.load_and_parse())

        self.assertEqual(dr.lastboot,
                         [MACPCI("01:23:45:67:89:0a","00:10.2", tname="eth2")])
        self.assertEqual(dr.old, [])


    def test_one_valid_lastboot(self):

        fd = StringIO.StringIO(
            '{"lastboot":[],"old":[["01:23:45:67:89:0a","00:10.2","eth2"]]}'
            )
        dr = DynamicRules(fd=fd)

        self.assertTrue(dr.load_and_parse())

        self.assertEqual(dr.lastboot, [])
        self.assertEqual(dr.old,
                         [MACPCI("01:23:45:67:89:0a","00:10.2", tname="eth2")])


class TestSave(unittest.TestCase):

    def setUp(self):
        self.logbuf = StringIO.StringIO()
        openLog(self.logbuf, logging.NOTSET)

    def tearDown(self):

        closeLogs()
        self.logbuf.close()

    def test_one_invalid_lastboot(self):

        dr = DynamicRules()
        dr.lastboot = [["foo", "bar", "baz"]]

        try:
            json.loads(dr.write(False))
        except Exception:
            self.fail()


if __name__ == "__main__":
    unittest.main()
