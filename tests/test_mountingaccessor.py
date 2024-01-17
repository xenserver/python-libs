"""pytest tests testing subclasses of xcp.accessor.MountingAccessor using pyfakefs"""
import sys
from io import BytesIO
from typing import TYPE_CHECKING, cast

from mock import patch
from pyfakefs.fake_filesystem import FakeFileOpen, FakeFilesystem

import xcp.accessor
import xcp.mount

from .test_httpaccessor import UTF8TEXT_LITERAL

if sys.version_info >= (3, 6):
    from pytest_subprocess.fake_process import FakeProcess

    if TYPE_CHECKING:
        from typing_extensions import Literal
else:
    import pytest

    pytest.skip(allow_module_level=True)

binary_data = b"\x00\x1b\x5b\x95\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xcc\xdd\xee\xff"


def expect(fp, mount):
    fp.register_subprocess(mount)  # type: ignore[arg-type]


def test_device_accessor(fs, fp):
    # type: (FakeFilesystem, FakeProcess) -> None
    assert isinstance(fp, FakeProcess)

    # Test xcp.mount.bindMount()
    mount = [b"/bin/mount", b"--bind", b"src", b"mountpoint_dest"]
    fp.register_subprocess(mount)  # type: ignore[arg-type]
    assert xcp.mount.bindMount("src", "mountpoint_dest") is None

    expect(fp, [b"/bin/mount", b"-t", b"iso9660", b"-o", b"ro", b"/dev/device", b"/tmp"])
    accessor = xcp.accessor.createAccessor("dev:///dev/device", False)

    assert isinstance(accessor, xcp.accessor.MountingAccessorTypes)
    check_mounting_accessor(accessor, fs, fp)


def test_nfs_accessor(fs, fp):
    # type: (FakeFilesystem, FakeProcess) -> None
    assert isinstance(fp, FakeProcess)
    mount = [
        b"/bin/mount",
        b"-t",
        b"nfs",
        b"-o",
        b"tcp,timeo=100,retrans=1,retry=0",
        b"server/path",
        b"/tmp",
    ]
    expect(fp, mount)
    accessor = xcp.accessor.createAccessor("nfs://server/path", False)
    assert isinstance(accessor, xcp.accessor.NFSAccessor)
    check_mounting_accessor(accessor, fs, fp)


def check_mounting_accessor(accessor, fs, fp):
    # type: (Literal[False] | xcp.accessor.Mount, FakeFilesystem, FakeProcess) -> None
    """Test subclasses of MountingAccessor (with xcp.cmd.runCmd in xcp.mount mocked)"""

    assert isinstance(accessor, xcp.accessor.MountingAccessorTypes)
    with patch("tempfile.mkdtemp") as tempfile_mkdtemp:
        tempfile_mkdtemp.return_value = "/tmp"
        accessor.start()

    assert accessor.location
    assert fs.isdir(accessor.location)

    location = accessor.location

    if sys.version_info.major >= 3:
        fs.add_mount_point(location)

    assert check_binary_read(accessor, location, fs)
    assert check_binary_write(accessor, location, fs)
    assert open_text(accessor, location, fs, UTF8TEXT_LITERAL) == UTF8TEXT_LITERAL

    if sys.version_info.major >= 3:
        fs.mount_points.pop(location)

    umount = [b"/bin/umount", b"-d", b"/tmp"]
    fp.register_subprocess(umount)  # type: ignore[arg-type]
    accessor.finish()

    assert not fs.exists(location)

    assert not accessor.location


def check_binary_read(accessor, location, fs):
    # type: (Literal[False] | xcp.accessor.AnyAccessor, str, FakeFilesystem) -> bool
    """Test the openAddress() method of different types of local Accessor classes"""

    assert isinstance(accessor, xcp.accessor.LocalTypes)
    name = "binary_file"
    path = location + "/" + name

    assert fs.create_file(path, contents=cast(str, binary_data))

    assert accessor.access(name)
    assert accessor.access("nonexisting filename") is False
    assert accessor.lastError == 404

    binary_file = accessor.openAddress(name)
    assert not isinstance(binary_file, bool)

    fs.remove(path)
    return cast(bytes, binary_file.read()) == binary_data


def check_binary_write(accessor, location, fs):
    # type: (Literal[False] | xcp.accessor.AnyAccessor, str, FakeFilesystem) -> bool
    """Test the writeFile() method of different types of local Accessor classes"""

    assert isinstance(accessor, xcp.accessor.LocalTypes)
    name = "binary_file_written_by_accessor"
    accessor.writeFile(BytesIO(binary_data), name)

    assert accessor.access(name)

    with FakeFileOpen(fs, delete_on_close=True)(location + "/" + name, "rb") as written:
        return cast(bytes, written.read()) == binary_data


def open_text(accessor, location, fs, text):
    # type: (Literal[False] | xcp.accessor.AnyAccessor, str, FakeFilesystem, str) -> str
    """Test the openText() method of subclasses of xcp.accessor.MountingAccessor"""

    assert isinstance(accessor, xcp.accessor.MountingAccessorTypes)
    name = "textfile"
    path = location + "/" + name
    assert fs.create_file(path, contents=text)
    assert accessor.access(name)
    with accessor.openText(name) as textfile:
        assert not isinstance(textfile, bool)
        fs.remove(path)
        return textfile.read()
