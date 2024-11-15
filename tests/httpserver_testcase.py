import os
import sys
import unittest
from typing import Callable, Optional

import pytest

# Skip the tests in this module if Python <= 3.6 (pytest_httpserver requires Python >= 3.7):
try:
    from http.client import HTTPResponse

    from pytest_httpserver import HTTPServer
    from werkzeug.wrappers import Request, Response

    ErrorHandler = Optional[Callable[[Request], Response]]
except ImportError:
    pytest.skip(allow_module_level=True)
    sys.exit(0)  # Let pyright know that this is a dead end


class HTTPServerTestCase(unittest.TestCase):
    HTTPResponse = HTTPResponse  # pyright: ignore[reportUnboundVariable]
    httpserver = HTTPServer()  # pyright: ignore[reportUnboundVariable]

    @classmethod
    def setUpClass(cls):
        cls.httpserver.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpserver.check_assertions()
        cls.httpserver.stop()

    @classmethod
    def serve_file(cls, root, file_path, error_handler=None, real_path=None):
        # type:(str, str, ErrorHandler, Optional[str]) -> None
        """Expect a GET request and handle it using the local pytest_httpserver.HTTPServer"""

        def handle_get(request):
            # type:(Request) -> Response
            """Handle a GET request for the local pytest_httpserver.HTTPServer fixture"""
            if error_handler:
                response = error_handler(request)
                if response:
                    return response
            filepath = root + (real_path or file_path)
            assert os.path.exists(path=filepath)
            with open(file=filepath, mode="rb") as local_testdata_file:
                return Response(local_testdata_file.read())

        cls.httpserver.expect_request(uri="/" + file_path).respond_with_handler(func=handle_get)
