# -*- coding: utf-8 -*-
"""
Test module of xcp.accessor.FTPAccessor

This Test module uses the pytest plugin pytest-localftpserver providing the ftpserver
fixture which provides a local pure-Python FTP server for testing xcp.accessor.FTPAccessor.

This avoids the dependency on a reliable Internet FTP service and a reliable Internet
connection and is self-contained.

While it is possible to forward the fixture to a unittest class as a class property,
it would create an extra indirection. It would also require many asserts and checks
to pacify static type checkers:

Because pytest is already needed and pytest wraps "assert" to behave like the unittest
asserts, by implementing the tests using pytest is a lot easer. The plain asserts
(which get wrapped) are much easier to read and we dont need "self.", making pytest
a pleasure to use. This is the result of these lessons learnt.
"""
import ftplib
from io import BytesIO

import pytest
import pytest_localftpserver  # Ensure that it is installed
from six import ensure_binary, ensure_str

import xcp.accessor

binary_data = b"\x80\x91\xaa\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xcc\xdd\xee\xff"
text_data = "✋➔Hello Accessor from the 🗺, download and verify ✅ me!"
assert pytest_localftpserver


def upload_textfile(ftpserver, accessor):
    accessor.writeFile(BytesIO(ensure_binary(text_data)), "textfile")
    assert accessor.access("textfile")
    assert text_data == ensure_str(ftpserver_content(ftpserver, "testdir/textfile"))

def upload_binary_file(ftpserver, accessor):
    """Upload a binary file and compare the uploaded file content with the local content"""
    accessor.writeFile(BytesIO(binary_data), "filename")
    assert accessor.access("filename")
    assert binary_data == ftpserver_content(ftpserver, "testdir/filename")


def ftpserver_content(ftpserver, path):
    ftp_content_generator = ftpserver.get_file_contents(path, read_mode="rb")
    return next(ftp_content_generator)["content"]


@pytest.fixture
def ftp_accessor(ftpserver):
    upload = {"src": "tests/test_ftpaccessor.py", "dest": "testdir/dummy-file-to-create-testdir"}
    ftpserver.put_files(upload, anon=False, overwrite=True)
    url = ftpserver.get_login_data(style="url", anon=False)

    accessor = xcp.accessor.FTPAccessor(url + "/testdir", False)
    accessor.start()
    upload_binary_file(ftpserver, accessor)
    upload_textfile(ftpserver, accessor)
    # This leaves ftp_accessor.finish() to each test to because disconnecting from the
    # ftpserver after the test in the fixture would cause the formatting of the pytest
    # live log to be become less readable:
    return accessor


# pylint: disable=redefined-outer-name  # The argument ftp_accessor is the fixture above
def test_repr_dunder(ftp_accessor):
    """Test the custom repr function FTPAccessor.__repr__() for code coverage and content"""
    accessorclass = ftp_accessor.__class__.__name__
    expected_repr = "<" + accessorclass + ": " + ftp_accessor.baseAddress + ">"
    assert str(ftp_accessor) == expected_repr
    ftp_accessor.finish()


def test_file_not_found(ftp_accessor):
    """Cover the failure code path of FTPAccessor.access() and check ftp_accessor.lastError"""
    assert not ftp_accessor.access("no_such_file")
    assert ftp_accessor.lastError == 500
    pytest.raises(ftplib.error_perm, ftp_accessor.openAddress, "no_such_file")
    ftp_accessor.finish()


def test_download_binary_file(ftp_accessor):
    """Download a binary file and compare the returned file content"""
    remote_ftp_filehandle = ftp_accessor.openAddress("filename")
    assert remote_ftp_filehandle.read() == binary_data
    assert ftp_accessor.access("filename") is True  # covers FTPAccessor._cleanup()
    ftp_accessor.finish()


def test_download_textfile(ftp_accessor):
    """Download a text file containing UTF-8 and compare the returned decoded string contents"""
    with ftp_accessor.openText("textfile") as remote_ftp_filehandle:
        assert remote_ftp_filehandle.read() == text_data
    ftp_accessor.finish()
