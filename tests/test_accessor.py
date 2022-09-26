import unittest
from parameterized import parameterized_class

import xcp.accessor

@parameterized_class([{"url": "file://tests/data/repo/"},
                      {"url": "https://updates.xcp-ng.org/netinstall/8.2.1"}])
class TestAccessor(unittest.TestCase):
    def test_access(self):
        a = xcp.accessor.createAccessor(self.url, True)
        a.start()
        self.assertTrue(a.access('.treeinfo'))
        self.assertFalse(a.access('no_such_file'))
        self.assertEqual(a.lastError, 404)
        a.finish()
