# -*- coding: utf-8 -*-
# sourcery skip: extract-duplicate-method,no-conditionals-in-tests,no-loop-in-tests
import sys
import unittest
from typing import cast, Type

import six
from mock import patch, Mock, DEFAULT, mock_open

from xcp.cmd import OutputCache, runCmd
from xcp.compat import open_utf8

class TestCache(unittest.TestCase):
    def setUp(self):
        self.c = OutputCache()

    def check_fileContents(self, read_data, *args, **kwargs):
        expected_kwargs = kwargs.pop("expected_kwargs", {})
        with patch("xcp.cmd.open", mock_open(read_data=read_data)) as open_mock:
            # uncached fileContents
            self.c.clearCache()
            data = self.c.fileContents("/tmp/foo", *args, **kwargs)
            open_mock.assert_called_once_with("/tmp/foo", *args, **expected_kwargs)
            self.assertEqual(data, read_data)

            # rerun as cached
            open_mock.reset_mock()
            data = self.c.fileContents("/tmp/foo", *args, **kwargs)
            open_mock.assert_not_called()
            self.assertEqual(data, read_data)

            # rerun after clearing cache
            open_mock.reset_mock()
            self.c.clearCache()
            data = self.c.fileContents("/tmp/foo", *args, **kwargs)
            open_mock.assert_called_once_with("/tmp/foo", *args, **expected_kwargs)
            self.assertEqual(data, read_data)

    def test_fileContents_mock_string(self):
        expected = open_utf8.copy()
        expected["mode"] = "r"
        self.check_fileContents("line1\nline2\n", mode="r", expected_kwargs=expected)

    def test_fileContents_mock_binary(self):
        self.check_fileContents(b"line1\nline2\n", "rb")

    def test_fileContents_mock_mode_b(self):
        self.check_fileContents(b"line1\nline2\n", mode="rb", expected_kwargs={"mode": "rb"})

    def test_fileContents_FileNotFound(self):
        try:
            FileNotFound = FileNotFoundError
        except NameError:
            FileNotFound = cast(Type["FileNotFoundError"], IOError)
        self.assertRaises(FileNotFound, self.c.fileContents, "You-dont-exist-to-me!.txt", mode="r")

    def test_fileContents_pciids_bytes(self):
        bytes_call_1 = self.c.fileContents("tests/data/pci.ids", "rb")
        bytes_cached = self.c.fileContents("tests/data/pci.ids", mode="rb")
        self.assertIsInstance(bytes_call_1, bytes)
        self.assertIsInstance(bytes_cached, bytes)
        self.assertGreater(len(bytes_cached), 788)
        self.assertEqual(bytes_call_1, bytes_cached)

    def test_fileContents_pciids_binstr(self):
        contents_bytes = self.c.fileContents("tests/data/pci.ids", mode="rb")
        contents_string = self.c.fileContents("tests/data/pci.ids", mode="r")
        self.assertIsInstance(contents_bytes, bytes)
        self.assertIsInstance(contents_string, str)
        self.assertEqual(contents_bytes, six.ensure_binary(contents_string))
        self.assertEqual(contents_string, six.ensure_str(contents_bytes))

    def test_runCmd(self):
        output_data = "line1\nline2\n"
        with patch("xcp.cmd.subprocess.Popen") as popen_mock:
            # mock Popen .communicate and .returncode for
            # `output_data`on stdout, nothing on stderr, and exit
            # value of 42
            communicate_mock = Mock(return_value=(output_data, ""))
            popen_mock.return_value.communicate = communicate_mock
            def communicate_side_effect(_input_text):
                popen_mock.return_value.returncode = 42
                return DEFAULT
            communicate_mock.side_effect = communicate_side_effect

            # uncached runCmd
            data = self.c.runCmd(["ls", "/tmp"], True, mode="t")
            popen_mock.assert_called_once()
            self.assertEqual(data, (42, output_data))

            # rerun as cached
            popen_mock.reset_mock()
            data = self.c.runCmd(["ls", "/tmp"], True, mode="t")
            popen_mock.assert_not_called()
            self.assertEqual(data, (42, output_data))

            # run a binary read and expect a cache miss
            popen_mock.reset_mock()
            data = self.c.runCmd(["ls", "/tmp"], True, mode="b")
            popen_mock.assert_called_once()
            self.assertEqual(data, (42, output_data))

            # rerun as cached
            popen_mock.reset_mock()
            data = self.c.runCmd(["ls", "/tmp"], True, mode="b")
            popen_mock.assert_not_called()
            self.assertEqual(data, (42, output_data))

            # Call cached function with no output
            popen_mock.reset_mock()
            self.assertEqual(self.c.runCmd(["ls", "/"]), 42)
            popen_mock.assert_called_once()

            # rerun as cached
            popen_mock.reset_mock()
            self.assertEqual(self.c.runCmd(["ls", "/"]), 42)
            popen_mock.assert_not_called()

            # Call uncached function with no output
            popen_mock.reset_mock()
            self.assertEqual(runCmd(["ls", "/"]), 42)
            popen_mock.assert_called_once()

    def test_nocache_runCmd_unicode_out(self):
        stdin = "✋➔Hello 🔛 uncached stdout ✅ World(🗺)"
        return_values = runCmd(["cat"], True, False, inputtext=stdin)
        self.assertEqual(return_values, (0, stdin))

    def test_nocache_runCmd_binary_err(self):
        stdin = b"Run uncached with a malformed non-UTF-8 char \xb2 in a bytes type!"
        return_values = runCmd("cat >&2", False, True, inputtext=stdin)
        self.assertEqual(return_values, (0, stdin))

    def test_runCmd_tee_unicode_outerr(self):
        stdin = "✋➔Hello World(🗺)‼"
        for _ in [1, 2]:  # 1st for running, 2nd for using the cache
            return_values = self.c.runCmd(
                "bash -c 'tee /dev/stderr'", True, True, inputtext=stdin
            )
            self.assertEqual(return_values, (0, stdin, stdin))

    def test_runCmd_cat_unicode_stdout(self):
        stdin = "✋➔Hello 🔛 stdout ✅ World(🗺)‼"
        for _ in [1, 2]:  # 1st for running, 2nd for using the cache
            return_values = self.c.runCmd(["cat"], True, False, inputtext=stdin)
            self.assertEqual(return_values, (0, stdin))

    def test_runCmd_cat_unicode_stderr(self):
        stdin = "✋➔Hello 🔛 stderr ❎ World(🗺)‼"
        for _ in [1, 2]:  # 1st for running, 2nd for using the cache
            return_values = self.c.runCmd("cat >&2", False, True, stdin, mode="t")
            self.assertEqual(return_values, (0, stdin))

    def test_runCmd_42_not_a_valid_command(self):
        self.assertRaises(TypeError, self.c.runCmd, 42)

    def test_runCmd_cat_binary(self):
        stdin = b"\x80\x91\xaa\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xcc\xdd\xee\xff"
        self.assertRaises(UnicodeDecodeError, stdin.decode)
        for _ in [1, 2]:  # rerun as cached
            return_values = self.c.runCmd("cat >&2", False, True, inputtext=stdin)
            self.assertEqual(return_values, (0, stdin))

    def test_runCmd_echo_stdout_list(self):
        text = "✋➔Hello 🔛 stdout ✅ World(🗺) with a Unicode string in the cmd list"
        kwargs = {}
        if sys.version_info >= (3, 0):
            kwargs["mode"] = "t"
        return_values = self.c.runCmd(["echo", "-n", text], with_stdout=True, **kwargs)
        self.assertEqual(return_values, (0, text))

    def test_runCmd_echo_stdout_shell(self):
        text = "✋➔Hello 🔛 stdout ✅ World(🗺) with a Unicode string as the command"
        kwargs = {}
        if sys.version_info >= (3, 0):
            kwargs["mode"] = "t"
        return_values = self.c.runCmd("echo -n '" + text + "'", with_stdout=True, **kwargs)
        self.assertEqual(return_values, (0, text))
