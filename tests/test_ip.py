# Unit test for xcp/net/ip.py
import unittest
from subprocess import PIPE

from mock import Mock, patch

import xcp.net.ip
from xcp import xcp_popen_text_kwargs


class TestIp(unittest.TestCase):
    def test_ip_link_set_name(self):
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
        xcp_popen_text_kwargs_stdout = xcp_popen_text_kwargs.copy()
        xcp_popen_text_kwargs_stdout["stdout"] = PIPE
        self.assertEqual(calls[0].kwargs, xcp_popen_text_kwargs_stdout)
        self.assertEqual(calls[1].kwargs, xcp_popen_text_kwargs)
        self.assertEqual(calls[2].kwargs, xcp_popen_text_kwargs)
        self.assertEqual(calls[3].kwargs, xcp_popen_text_kwargs)
