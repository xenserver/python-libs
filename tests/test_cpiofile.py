# suppress false positive on pytest missing pytest.raises():
# pyre-ignore-all-errors[16]
"""
Test various modes of creating and extracting CpioFile using different compression
types, opening the archive as stream and as file, using pyfakefs as filesystem without
ever touching any real real file. pyfakefs was developed by Google and is in wide use.
https://pytest-pyfakefs.readthedocs.io/en/latest/intro.html
"""
import io
import os
import sys
from typing import cast

import pytest
from pyfakefs.fake_filesystem import FakeFileOpen, FakeFilesystem

from xcp.cpiofile import CpioFile, StreamError

binary_data = b"\x00\x1b\x5b\x95\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xcc\xdd\xee\xff"


def test_cpiofile_modes(fs):
    # type: (FakeFilesystem) -> None
    """
    Test various modes of creating and extracting CpioFile using different compression
    types, opening the archive as stream and as file.

    :param fs: `FakeFilesystem` fixture representing a simulated file system for testing
    """
    with pytest.raises(TypeError) as exc_info:
        CpioFile.open(fileobj=io.StringIO())  # type: ignore[arg-type]
    assert exc_info.type == TypeError
    if sys.version_info < (3, 0):
        # Test Python2 pattern from host-upgrade-plugin:/etc/xapi.d/plugins/prepare_host_upgrade.py
        # Import the Python2-only StringIO.StringIO module, imported as Py2StringIO:
        # pylint: disable-next=import-outside-toplevel
        from StringIO import StringIO as Py2StringIO

        stringio = Py2StringIO()
        archive = CpioFile.open(fileobj=stringio, mode="w|gz")  # type: ignore[arg-type]
        archive.hardlinks = False
        archive.close()
        stringio.seek(0)
        assert stringio.read()

    for comp in ["cpio", "gz", "bz2", "xz"]:
        for filetype in [":", "|"]:
            if comp == "xz" and filetype == ":":
                continue  # streaming xz is not implemented (supported only as file)
            check_archive_mode(filetype + comp, fs)
            if filetype == "|":
                check_archive_mode(filetype + comp, fs, filename="archive." + comp)


def create_cpio_archive(fs, archive_mode, filename=None):
    # type: (FakeFilesystem, str, str | None) -> io.BytesIO | None
    """
    Create a CpioFile archive with files and directories from a FakeFilesystem.

    :param fs: `FakeFilesystem` fixture representing a simulated file system for testing
    :param archive_mode: The archive mode is a string parameter that specifies the mode
    in which the CpioFile object should be opened.
    :param filename: The name of the file to create the cpio archive
    """
    cpiofile = None if filename else io.BytesIO()
    fs.reset()
    cpio = CpioFile.open(name=filename, fileobj=cpiofile, mode="w" + archive_mode)
    pyfakefs_populate_archive(cpio, fs)
    if archive_mode == "|gz":
        cpio.list(verbose=True)
    cpio.close()
    if not cpiofile:
        cpio_data = FakeFileOpen(fs)(filename, "rb").read()
        fs.reset()
        fs.create_file(filename, contents=cast(str, cpio_data))
        return None
    fs.reset()
    cpiofile.seek(0)
    return cpiofile


def check_archive_mode(archive_mode, fs, filename=None):
    # type: (str, FakeFilesystem, str | None) -> None
    """
    Test CpioFile in the given archive mode with verification of the archive contents.

    :param archive_mode: The archive mode is a string parameter that specifies the mode
    in which the CpioFile object should be opened.
    :param fs: `FakeFilesystem` fixture representing a simulated file system for testing
    """
    # Step 2: Extract the archive in a clean filesystem and verify the extracted contents
    cpiofile = create_cpio_archive(fs, archive_mode, filename)
    archive = CpioFile.open(name=filename, fileobj=cpiofile, mode="r" + archive_mode)
    archive.extractall()
    pyfakefs_verify_filesystem(fs)
    assert archive.getnames() == ["dirname", "dirname/filename", "symlink", "dir2/file_2"]
    dirs = [cpioinfo.name for cpioinfo in archive.getmembers() if cpioinfo.isdir()]
    files = [cpioinfo.name for cpioinfo in archive.getmembers() if cpioinfo.isreg()]
    symlinks = [cpioinfo.name for cpioinfo in archive.getmembers() if cpioinfo.issym()]
    assert dirs == ["dirname"]
    assert files == ["dirname/filename", "dir2/file_2"]
    assert symlinks == ["symlink"]
    assert archive.getmember(symlinks[0]).linkname == "dirname/filename"

    # Test extracting a symlink to a file object:
    if archive_mode.startswith("|"):  # Non-seekable streams raise StreamError
        with pytest.raises(StreamError):
            archive.extractfile("symlink")
    else:  # Expect a seekable fileobj for this test (not a stream) to work:
        fileobj = archive.extractfile("symlink")
        assert fileobj and fileobj.read() == binary_data
    archive.close()

    # Step 3: Extract the archive a second time using another method
    cpiofile = create_cpio_archive(fs, archive_mode, filename)
    archive = CpioFile.open(name=filename, fileobj=cpiofile, mode="r" + archive_mode)
    if archive_mode[0] != "|":
        for cpioinfo in archive:
            archive.extract(cpioinfo)
        pyfakefs_verify_filesystem(fs)
    if archive_mode == "|xz":
        archive.list(verbose=True)
    archive.close()


def pyfakefs_populate_archive(archive, fs):
    # type: (CpioFile, FakeFilesystem) -> None
    """
    Populate a CpioFile archive with files and directories from a FakeFilesystem.

    :param archive: Instance of the CpioFile class to create a new cpio archive
    :param fs: `FakeFilesystem` fixture representing a simulated file system for testing
    """

    fs.create_file("dirname/filename", contents=cast(str, binary_data))
    archive.add("dirname", recursive=True)
    fs.create_file("directory/file_2", contents=cast(str, binary_data))
    fs.create_symlink("symlink", "dirname/filename")
    archive.add("symlink")

    # Test special code path of archive.add(".", ...):
    os.chdir("directory")
    archive.add(".", "dir2", recursive=True)  # Test adding . as dir2
    os.chdir("..")
    os.rename("directory", "dir2")

    pyfakefs_verify_filesystem(fs)


def pyfakefs_verify_filesystem(fs):
    # type: (FakeFilesystem) -> None
    """
    Verify the contents of the fake filesystem populated by pyfakefs_populate_archive()
    and it is called again after a CpioFile.extractall() extracted the populated files
    from the cpio archive.

    :param fs: `FakeFilesystem` fixture representing a simulated file system for testing
    """
    assert fs.islink("symlink")
    assert fs.isfile("dirname/filename")
    assert fs.isfile("dir2/file_2")
    with FakeFileOpen(fs)("dirname/filename", "rb") as contents:
        assert contents.read() == binary_data
    with FakeFileOpen(fs)("dir2/file_2", "rb") as contents:
        assert contents.read() == binary_data
