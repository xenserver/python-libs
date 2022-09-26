import unittest
import hashlib
from tempfile import NamedTemporaryFile

from parameterized import parameterized_class

import xcp.accessor

@parameterized_class([{"url": "file://tests/data/repo/"},
                      {"url": "https://updates.xcp-ng.org/netinstall/8.2.1"}])
class TestAccessor(unittest.TestCase):
    def test_access(self):
        a = xcp.accessor.createAccessor(self.url, True)
        a.start()
        self.assertTrue(a.access('.treeinfo'))
        self.assertFalse(a.access('no_such_file'))
        self.assertEqual(a.lastError, 404)
        a.finish()

    def test_file_binfile(self):
        BINFILE = "boot/isolinux/mboot.c32"
        a = xcp.accessor.createAccessor(self.url, True)
        a.start()
        self.assertTrue(a.access(BINFILE))
        inf = a.openAddress(BINFILE)
        with NamedTemporaryFile("w") as outf:
            outf.writelines(inf)
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
