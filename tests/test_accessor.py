import unittest
import hashlib
from tempfile import NamedTemporaryFile

from parameterized import parameterized_class

import xcp.accessor

@parameterized_class([{"url": "file://tests/data/repo/"},
                      {"url": "https://updates.xcp-ng.org/netinstall/8.2.1"}])
class TestAccessor(unittest.TestCase):
    url = ""

    def setup_accessor(self, arg0):
        result = xcp.accessor.createAccessor(self.url, True)
        result.start()
        self.assertTrue(result.access(arg0))
        return result

    def test_access(self):
        a = self.setup_accessor('.treeinfo')
        self.assertFalse(a.access('no_such_file'))
        self.assertEqual(a.lastError, 404)
        a.finish()

    def test_file_binfile(self):
        binary_file_in_repo = "boot/isolinux/mboot.c32"
        a = self.setup_accessor(binary_file_in_repo)
        inf = a.openAddress(binary_file_in_repo)
        with NamedTemporaryFile("wb") as outf:
            while True:
                data = inf.read()
                if not data: # EOF
                    break
                outf.write(data)
            outf.flush()
            hasher = hashlib.md5()
            with open(outf.name, "rb") as bincontents:
                while True:
                    data = bincontents.read()
                    if not data: # EOF
                        break
                    hasher.update(data)
                csum = hasher.hexdigest()
                self.assertEqual(csum, "eab52cebc3723863432dc672360f6dac")
        a.finish()
