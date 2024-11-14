import unittest
from typing import TYPE_CHECKING

import xcp.accessor

from .test_mountingaccessor import check_binary_read, check_binary_write

if TYPE_CHECKING:
    import pyfakefs
    import pytest


def test_file_accessor(fs, caplog):
    # type(pyfakefs.fake_filesystem.FakeFilesystem, pytest.LogCaptureFixture) -> None
    """Test FileAccessor.writeFile(), .openAddress and .access using pyfakefs"""
    accessor = xcp.accessor.createAccessor("file://repo/", False)
    assert isinstance(accessor, xcp.accessor.FileAccessor)
    check_binary_read(accessor, "/repo", fs)
    check_binary_write(accessor, "/repo", fs, caplog)


class TestAccessor(unittest.TestCase):
    def setUp(self):
        """Provide the reference content of the repo/.treeinfo file for check_repo_access()"""
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
        a.finish()  # Test and cover already finished accessors

    def test_filesystem_accessor_access(self):
        """Test FilesystemAccessor.access()"""

        a = xcp.accessor.FilesystemAccessor("tests/data/repo/", True)
        self.check_repo_access(a)


def test_access_handles_exception():
    class AccessorHandlesException(xcp.accessor.Accessor):
        def openAddress(self, address):
            raise IOError("Test Accessor.access returning False on Exception to cove code")

    assert AccessorHandlesException(True).access("filename") is False
