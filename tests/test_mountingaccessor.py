"""pytest tests testing subclasses of xcp.accessor.MountingAccessor using pyfakefs"""
import sys
from io import BytesIO
from typing import cast

from mock import patch
from pyfakefs.fake_filesystem import FakeFileOpen, FakeFilesystem

import xcp.accessor

binary_data = b"\x00\x1b\x5b\x95\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xcc\xdd\xee\xff"


def test_device_accessor(fs):
    # type: (FakeFilesystem) -> None
    accessor = xcp.accessor.createAccessor("dev:///dev/device", False)
    check_mounting_accessor(accessor, fs)


def test_nfs_accessor(fs):
    # type: (FakeFilesystem) -> None
    accessor = xcp.accessor.createAccessor("nfs://server/path", False)
    check_mounting_accessor(accessor, fs)


def check_mounting_accessor(accessor, fs):
    # type: (xcp.accessor.MountingAccessor, FakeFilesystem) -> None
    """Test subclasses of MountingAccessor (with xcp.cmd.runCmd in xcp.mount mocked)"""

    with patch("xcp.cmd.runCmd") as mount_runcmd:
        mount_runcmd.return_value = (0, "", "")
        accessor.start()

    assert accessor.location
    assert fs.isdir(accessor.location)

    location = accessor.location

    if sys.version_info.major >= 3:
        fs.add_mount_point(location)

    assert check_binary_read(accessor, location, fs)
    assert check_binary_write(accessor, location, fs)

    if sys.version_info.major >= 3:
        fs.mount_points.pop(location)

    with patch("xcp.cmd.runCmd"):
        accessor.finish()

    assert not fs.exists(location)

    assert not accessor.location


def check_binary_read(accessor, location, fs):
    # type: (xcp.accessor.MountingAccessor, str, FakeFilesystem) -> bool
    """Test the openAddress() method of subclasses of xcp.accessor.MountingAccessor"""

    name = "binary_file"
    path = location + "/" + name

    assert fs.create_file(path, contents=cast(str, binary_data))

    assert accessor.access(name)

    binary_file = accessor.openAddress(name)
    assert not isinstance(binary_file, bool)

    fs.remove(path)
    return cast(bytes, binary_file.read()) == binary_data


def check_binary_write(accessor, location, fs):
    # type: (xcp.accessor.MountingAccessor, str, FakeFilesystem) -> bool
    """Test the writeFile() method of subclasses of xcp.accessor.MountingAccessor"""

    name = "binary_file_written_by_accessor"
    accessor.writeFile(BytesIO(binary_data), name)

    assert accessor.access(name)

    with FakeFileOpen(fs, delete_on_close=True)(location + "/" + name, "rb") as written:
        return cast(bytes, written.read()) == binary_data
