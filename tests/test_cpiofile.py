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

from xcp.cpiofile import CpioFile

from .test_mountingaccessor import binary_data


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
        import StringIO

        stringio = StringIO.StringIO()
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


def check_archive_mode(archive_mode, fs):
    # type: (str, FakeFilesystem) -> None
    """
    Test CpioFile in the given archive mode with verification of the archive contents.

    :param archive_mode: The archive mode is a string parameter that specifies the mode
    in which the CpioFile object should be opened.
    :param fs: `FakeFilesystem` fixture representing a simulated file system for testing
    """
    # Step 1: Create and populate a cpio archive in a BytesIO buffer
    bytesio = io.BytesIO()
    archive = CpioFile.open(fileobj=bytesio, mode="w" + archive_mode)
    pyfakefs_populate_archive(archive, fs)
    if archive_mode == "|gz":
        archive.list(verbose=True)
    archive.close()

    # Step 2: Extract the archive in a clean filesystem and verify the extracted contents
    fs.reset()
    bytesio.seek(0)
    archive = CpioFile.open(fileobj=bytesio, mode="r" + archive_mode)
    archive.extractall()
    pyfakefs_verify_filesystem(fs)
    assert archive.getnames() == ["dirname", "dirname/filename", "dir2/symlink"]
    dirs = [cpioinfo.name for cpioinfo in archive.getmembers() if cpioinfo.isdir()]
    files = [cpioinfo.name for cpioinfo in archive.getmembers() if cpioinfo.isreg()]
    symlinks = [cpioinfo.name for cpioinfo in archive.getmembers() if cpioinfo.issym()]
    assert dirs == ["dirname"]
    assert files == ["dirname/filename"]
    assert symlinks == ["dir2/symlink"]
    assert archive.getmember(symlinks[0]).linkname == "symlink_target"
    archive.close()

    # Step 3: Extract the archive a second time using another method
    fs.reset()
    bytesio.seek(0)
    archive = CpioFile.open(fileobj=bytesio, mode="r" + archive_mode)
    if archive_mode[0] != "|":
        for cpioinfo in archive:
            archive.extract(cpioinfo)
        pyfakefs_verify_filesystem(fs)
    if archive_mode == "|xz":
        archive.list(verbose=True)
    archive.close()
    bytesio.close()


def pyfakefs_populate_archive(archive, fs):
    # type: (CpioFile, FakeFilesystem) -> None
    """
    Populate a CpioFile archive with files and directories from a FakeFilesystem.

    :param archive: Instance of the CpioFile class to create a new cpio archive
    :param fs: `FakeFilesystem` fixture representing a simulated file system for testing
    """
    fs.reset()

    fs.create_file("dirname/filename", contents=cast(str, binary_data))
    archive.add("dirname", recursive=True)
    fs.create_symlink("directory/symlink", "symlink_target")

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
    assert fs.islink("dir2/symlink")
    assert fs.isfile("dirname/filename")
    with FakeFileOpen(fs)("dirname/filename", "rb") as contents:
        assert contents.read() == binary_data
