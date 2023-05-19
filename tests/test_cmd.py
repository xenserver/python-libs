import unittest

from mock import patch, Mock, DEFAULT, mock_open

from xcp.cmd import OutputCache
from xcp.compat import open_utf8

class TestCache(unittest.TestCase):
    def setUp(self):
        self.c = OutputCache()

    def check_fileContents(self, read_data, *args, **kwargs):
        expected_kwargs = kwargs.pop("expected_kwargs", {})
        with patch("xcp.cmd.open", mock_open(read_data=read_data)) as open_mock:
            # uncached fileContents
            data = self.c.fileContents('/tmp/foo')
            open_mock.assert_called_once_with("/tmp/foo", *args, **expected_kwargs)
            self.assertEqual(data, read_data)

            # rerun as cached
            open_mock.reset_mock()
            data = self.c.fileContents('/tmp/foo')
            open_mock.assert_not_called()
            self.assertEqual(data, read_data)

            # rerun after clearing cache
            open_mock.reset_mock()
            self.c.clearCache()
            data = self.c.fileContents('/tmp/foo')
            open_mock.assert_called_once_with("/tmp/foo", *args, **expected_kwargs)
            self.assertEqual(data, read_data)

    def test_fileContents_mock_string(self):
        self.check_fileContents("line1\nline2\n", expected_kwargs=open_utf8)

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
            data = self.c.runCmd(['ls', '/tmp'], True)
            popen_mock.assert_called_once()
            self.assertEqual(data, (42, output_data))

            # rerun as cached
            popen_mock.reset_mock()
            data = self.c.runCmd(['ls', '/tmp'], True)
            popen_mock.assert_not_called()
            self.assertEqual(data, (42, output_data))
