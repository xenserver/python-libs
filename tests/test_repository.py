import unittest

import xcp.accessor
from xcp import repository
from xcp.version import Version

class TestRepository(unittest.TestCase):
    def test_http(self):
        raise unittest.SkipTest("comment out if you really mean it")
        a = xcp.accessor.createAccessor("https://updates.xcp-ng.org/netinstall/8.2.1", True)
        repo_ver = repository.BaseRepository.getRepoVer(a)
        self.assertEqual(repo_ver, Version([3, 2, 1]))
        product_ver = repository.BaseRepository.getProductVersion(a)
        self.assertEqual(product_ver, Version([8, 2, 1]))
        repos = repository.BaseRepository.findRepositories(a)
        self.assertEqual(len(repos), 1)

    def test_file(self):
        a = xcp.accessor.createAccessor("file://tests/data/repo/", True)
        repo_ver = repository.BaseRepository.getRepoVer(a)
        self.assertEqual(repo_ver, Version([3, 2, 1]))
        product_ver = repository.BaseRepository.getProductVersion(a)
        self.assertEqual(product_ver, Version([8, 2, 1]))
        repos = repository.BaseRepository.findRepositories(a)
        self.assertEqual(len(repos), 1)
