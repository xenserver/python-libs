import unittest

import xcp.accessor

class TestAccessor(unittest.TestCase):
    def check_repo_access(self, a):
        """Common helper function for testing Accessor.access() with repo files"""
        a.start()
        self.assertTrue(a.access('.treeinfo'))
        self.assertFalse(a.access('no_such_file'))
        self.assertEqual(a.lastError, 404)
        a.finish()

    def test_http_accessor_access(self):
        """Test HTTPAccessor.access()"""

        # Temporary: To be obsoleted by a dedicated test case using a pytest-native
        # httpd which will cover code paths like HTTP Basic Auth in an upcoming commit:
        a = xcp.accessor.createAccessor("https://updates.xcp-ng.org/netinstall/8.2.1", True)
        self.check_repo_access(a)

    def test_file(self):
        """Test FileAccessor.access()"""

        a = xcp.accessor.createAccessor("file://tests/data/repo/", True)
        self.check_repo_access(a)

    def test_filesystem_accessor_access(self):
        """Test FilesystemAccessor.access()"""

        a = xcp.accessor.FilesystemAccessor("tests/data/repo/", True)
        self.check_repo_access(a)
