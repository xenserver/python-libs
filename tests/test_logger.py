"""Test xcp.logger.openLog()"""
import os
import sys
from io import StringIO
from pty import openpty

from mock import mock_open, patch

from xcp.compat import open_utf8
from xcp.logger import openLog


def test_openLog_mock_open():
    """Cover xcp.logger.openLog.open_with_codec_handling and check the arguments used for open()"""
    fh = StringIO()
    with patch("xcp.compat.open", mock_open()) as open_mock:
        open_mock.return_value = fh
        assert openLog("test.log") is True
        if sys.version_info >= (3, 0):
            assert open_utf8 == {"encoding": "utf-8", "errors": "replace"}
        else:
            assert not open_utf8
        open_mock.assert_called_once_with("test.log", "a", **open_utf8)


def test_openLog_mock_stdin():
    """Cover xcp.logger.openLog calling logging.StreamHandler(h) when h is a tty"""
    with patch("xcp.compat.open", mock_open()) as open_mock:
        master_fd, slave_fd = openpty()
        open_mock.return_value = os.fdopen(slave_fd)
        assert openLog("test.log") is True
        os.close(slave_fd)
        os.close(master_fd)
