import unittest
from parameterized import parameterized_class

import xcp.accessor
from xcp import repository
from xcp.version import Version

@parameterized_class([{"url": "file://tests/data/repo/"},
                      {"url": "https://updates.xcp-ng.org/netinstall/8.2.1"}])
class TestRepository(unittest.TestCase):
    def test_basicinfo(self):
        a = xcp.accessor.createAccessor(self.url, True)
        repo_ver = repository.BaseRepository.getRepoVer(a)
        self.assertEqual(repo_ver, Version([3, 2, 1]))
        product_ver = repository.BaseRepository.getProductVersion(a)
        self.assertEqual(product_ver, Version([8, 2, 1]))
        repos = repository.BaseRepository.findRepositories(a)
        self.assertEqual(len(repos), 1)
