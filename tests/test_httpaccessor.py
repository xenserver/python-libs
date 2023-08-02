"""Test xcp.accessor.HTTPAccessor using a local pure-Python http(s)server fixture"""
# -*- coding: utf-8 -*-
import base64
import sys
from contextlib import contextmanager
from typing import IO, Generator, Tuple

from six.moves import urllib  # pyright: ignore

from xcp.accessor import HTTPAccessor, createAccessor

from .httpserver_testcase import ErrorHandler, HTTPServerTestCase, Response

HTTPAccessorGenerator = Generator[Tuple[HTTPAccessor, IO[bytes]], None, None]

UTF8TEXT_LITERAL = "✋Hello accessor from the 🗺, download and verify me! ✅"


class HTTPAccessorTestCase(HTTPServerTestCase):
    document_root = "tests/"

    def test_404(self):
        self.httpserver.expect_request("/404").respond_with_data("", status=404)
        httpaccessor = createAccessor(self.httpserver.url_for("/"), True)
        self.assertFalse(httpaccessor.access("404"))
        self.httpserver.check_assertions()
        self.assertEqual(httpaccessor.lastError, 404)

    @contextmanager
    def http_get_request_data(self, url, read_file, error_handler):
        # type:(str, str, ErrorHandler) -> HTTPAccessorGenerator
        """Serve a GET request, assert that the accessor returns the content of the GET Request"""
        self.serve_file(self.document_root, read_file, error_handler)

        httpaccessor = createAccessor(url, True)
        self.assertEqual(type(httpaccessor), HTTPAccessor)

        with open(self.document_root + read_file, "rb") as ref:
            yield httpaccessor, ref

    def assert_http_get_request_data(self, url, read_file, error_handler):
        # type:(str, str, ErrorHandler) -> HTTPAccessor
        with self.http_get_request_data(url, read_file, error_handler) as (httpaccessor, ref):
            http_accessor_filehandle = httpaccessor.openAddress(read_file)
            if sys.version_info >= (3, 0):
                assert isinstance(http_accessor_filehandle, self.HTTPResponse)

            self.assertEqual(http_accessor_filehandle.read(), ref.read())
            self.httpserver.check_assertions()
            http_accessor_filehandle.close()

        return httpaccessor

    @staticmethod
    def httpserver_basic_auth_handler(login):
        # type(str) -> Callable[[Request], Response | None]
        def basic_auth_handler_func(request):
            # type(Request) -> Response | None
            key = base64.b64encode(urllib.parse.unquote(login).encode()).decode()
            authorization = request.headers.get("Authorization", None)
            # If the client didn't send the "Authorization: Basic" header, tell it to use Basic Auth
            if not authorization or authorization != "Basic " + key:
                # Hint: The realm is an ID for the pages for which the same login is valid:
                basic_realm = {"WWW-Authenticate": 'Basic realm="Realm"'}
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
        login = "Tan%u0131m:%E4%B8%8A%E6%B5%B7%2B%E4%B8%AD%E5%9C%8B"  # URL-encoded Unicode

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

    def test_httpaccessor_open_text(self):
        """Get text containing UTF-8 and compare the returned decoded string contents"""
        self.httpserver.expect_request("/textfile").respond_with_data(UTF8TEXT_LITERAL)
        accessor = createAccessor(self.httpserver.url_for("/"), True)
        with accessor.openText("textfile") as textfile:
            assert textfile.read() == UTF8TEXT_LITERAL
