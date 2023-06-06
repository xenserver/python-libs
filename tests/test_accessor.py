import unittest

import xcp.accessor

class TestAccessor(unittest.TestCase):
    def setUp(self):
        """Provide the refrence content of the repo/.treeinfo file for check_repo_access()"""
        with open("tests/data/repo/.treeinfo", "rb") as dot_treeinfo:
            self.reference_treeinfo = dot_treeinfo.read()

    def check_repo_access(self, a):
        """Common helper function for testing Accessor.access() with repo files"""
        a.start()

        treeinfo_file = a.openAddress('.treeinfo')
        assert not isinstance(treeinfo_file, bool)  # check to not return False, pytype alerts on it
        assert treeinfo_file.read() == self.reference_treeinfo
        treeinfo_file.close()

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
