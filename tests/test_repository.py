import unittest

import xcp.accessor
from xcp import repository
from xcp.version import Version

class TestRepository(unittest.TestCase):
    def test_file_and_basic_unittest(self):
        unittest_driver_rpm_package()
        # Contains an XS-PACKAGES file to cover _create_package() for supp-pack-build
        assert len(self.check_repo_tree("file://tests/data/repo/")) == 2

    def check_repo_tree(self, url):
        a = xcp.accessor.createAccessor(url, True)
        repo_ver = repository.BaseRepository.getRepoVer(a)
        self.assertEqual(repo_ver, Version([3, 2, 1]))
        product_ver = repository.BaseRepository.getProductVersion(a)
        self.assertEqual(product_ver, Version([8, 2, 1]))
        return repository.BaseRepository.findRepositories(a)


def unittest_driver_rpm_package():
    repo = "test_repo"
    label = "test_label"
    size = 1024
    md5sum = "test_md5sum"
    fname = "test_fname"
    kernel = "test_kernel"
    options = "test_options"
    pkg = repository.DriverRPMPackage(repo, label, size, md5sum, fname, kernel, options)
    assert pkg.repository == repo
    assert pkg.label == label
    assert pkg.size == size
    assert pkg.md5sum == md5sum
    assert pkg.filename == fname
    assert pkg.kernel == kernel
    assert pkg.options == options
    assert str(pkg) == "<DriverRPMPackage 'test_label', kernel 'test_kernel'>"
