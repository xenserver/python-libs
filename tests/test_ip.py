"""tests/test_ip.py: Unit test for xcp/net/ip.py"""
import ctypes
import os
import unittest
from subprocess import PIPE

import pytest
import pytest_forked  # pylint: disable=unused-import # Ensure pytest-forked is installed
from mock import Mock, patch

import xcp.net.ip

CLONE_NEWUSER = 0x10000000
CLONE_NEWNET = 0x40000000


def libc_unshare_syscall(flags):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.unshare.argtypes = [ctypes.c_int]
    rc = libc.unshare(flags)
    if rc != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno), flags)


def use_new_user_network_namespaces():
    uidmap = b"0 %d 1" % os.getuid()  # uidmap for the current uid in the new namespace
    libc_unshare_syscall(CLONE_NEWUSER | CLONE_NEWNET)
    with open("/proc/self/uid_map", "wb") as file_:
        file_.write(uidmap)  #  Switch to uid=0 in the new namespace to test ip_link_set_name()


class TestIp(unittest.TestCase):
    iproute2_check = os.system("ip address show lo")

    @unittest.skipIf(iproute2_check, "requires the ip command to set interface names")
    @pytest.mark.forked  # The isolated network namespace would cause issues for other test cases
    @patch("xcp.net.ip.LOG.info")
    def test_ip_link_set_name_in_netns(self, mock):
        """Check that the "ip" calls of ip_link_set_name() actually work (in a network namespace)"""
        use_new_user_network_namespaces()
        xcp.net.ip.ip_link_set_name("lo", "lo0")
        mock.assert_called_with("Succesfully renamed link lo to lo0")

    def test_ip_link_set_name_mock(self):
        """Check using "mock" that ip_link_set_name() calls "ip" with the expected arguments"""
        with patch("xcp.net.ip.Popen") as popen_mock:
            # Setup the return values and return codes returned by popen_mock:
            ip_link_show_lo_stdout = (
                "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state"
                "UNKNOWN mode DEFAULT group default qlen 1000"
            )
            communicate_mock = Mock(
                side_effect=iter([(ip_link_show_lo_stdout, ""), ("", "")])
            )
            popen_mock.return_value.communicate = communicate_mock
            popen_mock.return_value.returncode = 0

            # Call the testee function with xcp.net.ip.Popen() mocked using popen_mock:
            xcp.net.ip.ip_link_set_name("lo", "lo0")

        # check the number or calls to Popen() by done by ip_link_set_name()
        self.assertEqual(popen_mock.call_count, 4)

        # check the captured regular arguments passed to Popen() by ip_link_set_name()
        calls = popen_mock.call_args_list
        self.assertEqual(calls[0].args, (["ip", "link", "show", "lo"],))
        self.assertEqual(calls[1].args, (["ip", "link", "set", "lo", "down"],))
        self.assertEqual(calls[2].args, (["ip", "link", "set", "lo", "name", "lo0"],))
        self.assertEqual(calls[3].args, (["ip", "link", "set", "lo0", "up"],))

        # check the captured keyword arguments passed to Popen() by ip_link_set_name()
        expected_kwargs = {"universal_newlines": True}  # type: dict[str, bool | int]
        self.assertEqual(calls[1].kwargs, expected_kwargs)
        self.assertEqual(calls[2].kwargs, expected_kwargs)
        self.assertEqual(calls[3].kwargs, expected_kwargs)
        expected_kwargs["stdout"] = PIPE
        self.assertEqual(calls[0].kwargs, expected_kwargs)
