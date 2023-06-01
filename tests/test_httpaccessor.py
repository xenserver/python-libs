"""Test xcp.accessor.HTTPAccessor using a local pure-Python http(s)server fixture"""
import base64
import sys
import unittest

import pytest

from xcp.accessor import HTTPAccessor, createAccessor

# Skip the tests in this module if Python <= 3.6 (pytest_httpserver requires Python >= 3.7):
try:
    from http.client import HTTPResponse

    from pytest_httpserver import HTTPServer
    from werkzeug.wrappers import Response
except ImportError:
    pytest.skip(allow_module_level=True)


class HTTPAccessorTestCase(unittest.TestCase):
    document_root = "tests/"
    httpserver = HTTPServer()  # pyright: ignore[reportUnboundVariable]

    @classmethod
    def setUpClass(cls):
        cls.httpserver.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpserver.check_assertions()
        cls.httpserver.stop()

    def test_404(self):
        self.httpserver.expect_request("/404").respond_with_data("", status=404)
        httpaccessor = createAccessor(self.httpserver.url_for("/"), True)
        self.assertFalse(httpaccessor.access("404"))
        self.httpserver.check_assertions()
        self.assertEqual(httpaccessor.lastError, 404)

    @classmethod
    def serve_a_get_request(cls, testdata_repo_subdir, read_file, error_handler):
        """Expect a GET request and handle it using the local pytest_httpserver.HTTPServer"""

        def handle_get(request):
            """Handle a GET request for the local pytest_httpserver.HTTPServer fixture"""
            if error_handler:
                response = error_handler(request)
                if response:
                    return response
            with open(testdata_repo_subdir + read_file, "rb") as local_testdata_file:
                return Response(local_testdata_file.read())

        cls.httpserver.expect_request("/" + read_file).respond_with_handler(handle_get)

    def assert_http_get_request_data(self, url, read_file, error_handler):
        """Serve a GET request, assert that the accessor returns the content of the GET Request"""
        self.serve_a_get_request(self.document_root, read_file, error_handler)

        httpaccessor = createAccessor(url, True)
        self.assertEqual(type(httpaccessor), HTTPAccessor)

        with open(self.document_root + read_file, "rb") as ref:
            http_accessor_filehandle = httpaccessor.openAddress(read_file)
            if sys.version_info >= (3, 0):
                assert isinstance(http_accessor_filehandle, HTTPResponse)

            self.assertEqual(http_accessor_filehandle.read(), ref.read())
            self.httpserver.check_assertions()
            http_accessor_filehandle.close()

        return httpaccessor

    @staticmethod
    def httpserver_basic_auth_handler(login):
        def basic_auth_handler_func(request):
            key = base64.b64encode(login.encode()).decode()
            authorization = request.headers.get("Authorization", None)
            # When no valid Authorization header is received, tell the client the ream for it:
            if not authorization or authorization != "Basic " + key:
                basic_realm = {"WWW-Authenticate": 'Basic realm="BasicAuthTestRealm"'}
                return Response("not authorized", status=401, headers=basic_realm)
            return None

        return basic_auth_handler_func

    def test_access_repo_treeinfo(self):
        """Assert that the accessor has access to the .treeinfo file of the repo"""
        access = self.assert_http_get_request_data(
            self.httpserver.url_for(""), "data/repo/.treeinfo", None
        )
        self.assertTrue(access.access("data/repo/.treeinfo"))

    def test_basic_auth(self):
        login = "user:passwd"

        # Insert the login into the URL for the test server: http://user:passwd@localhost/path
        url = self.httpserver.url_for("").split("//")
        url_with_login = url[0] + "//" + login + "@" + url[1]

        # Test that a GET Request with the auth handler returns the served file:
        basic_auth = self.httpserver_basic_auth_handler(login)
        self.assert_http_get_request_data(url_with_login, "data/repo/.treeinfo", basic_auth)

    def test_get_binary(self):
        binary = (
            "__pycache__/__init__.cpython-"
            + str(sys.version_info.major)
            + str(sys.version_info.minor)
            + ".pyc"
        )
        self.assert_http_get_request_data(self.httpserver.url_for(""), binary, None)
