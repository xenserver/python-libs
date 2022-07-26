import unittest

import xcp.accessor

class TestAccessor(unittest.TestCase):
    def test_http(self):
        #raise unittest.SkipTest("comment out if you really mean it")
        a = xcp.accessor.createAccessor("https://updates.xcp-ng.org/netinstall/8.2.1", True)
        a.start()
        self.assertTrue(a.access('.treeinfo'))
        self.assertFalse(a.access('no_such_file'))
        self.assertEqual(a.lastError, 404)
        a.finish()

    def test_file(self):
        a = xcp.accessor.createAccessor("file://tests/data/repo/", True)
        a.start()
        self.assertTrue(a.access('.treeinfo'))
        self.assertFalse(a.access('no_such_file'))
        self.assertEqual(a.lastError, 404)
        a.finish()
