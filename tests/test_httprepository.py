"""Test xcp.repository using a local pure-Python http(s)server fixture"""
from contextlib import contextmanager

from xcp.accessor import HTTPAccessor, createAccessor
from xcp.repository import BaseRepository, YumRepository
from xcp.version import Version

from .httpserver_testcase import HTTPServerTestCase


class HTTPRepositoryTestCase(HTTPServerTestCase):
    document_root = "tests/data/repo/"

    @contextmanager
    def get_httpaccessor(self, url):
        """Serve a GET request, assert that the accessor returns the content of the GET Request"""
        httpaccessor = createAccessor(url, True)
        assert isinstance(httpaccessor, HTTPAccessor)
        yield httpaccessor
        httpaccessor.finish()

    def test_xenserver_yum_repo(self):
        """Test a combined Yum and XenSource repository"""
        yum_repo_files = [
            YumRepository.TREEINFO_FILENAME,
            YumRepository.REPOMD_FILENAME,
        ]
        xensource_repo_files = [
            "XS-REPOSITORY",
            "XS-PACKAGES",
            "XS-REPOSITORY-LIST",
        ]
        repofiles = yum_repo_files + xensource_repo_files
        # sourcery skip: no-loop-in-tests
        for subdir in ("", ".main", ".linux", ".site"):
            for file in xensource_repo_files:
                name = "packages" + subdir + "/" + file
                repofiles += [name]
        with self.get_httpaccessor(url=self.httpserver.url_for(suffix="")) as httpaccessor:
            for path in repofiles:
                realpath = path.split(sep="/")[1] if path.startswith("packages") else path
                self.serve_file(
                    root=self.document_root,
                    file_path=path,
                    error_handler=None,
                    real_path=realpath,
                )
            assert BaseRepository.getRepoVer(access=httpaccessor) == Version(ver=[3, 2, 1])
            assert BaseRepository.getProductVersion(access=httpaccessor) == Version(ver=[8, 2, 1])
            assert len(BaseRepository.findRepositories(access=httpaccessor)) == 6
