#!/usr/bin/env python

import unittest, sys, os, os.path as path

try:
    import xcp
except ImportError:
    print >>sys.stderr, "Must run with run-tests.sh"
    sys.exit(1)

from xcp.cpiofile import CpioFile, CpioInfo
import subprocess, shutil

try:
    from hashlib import md5
except:
    from md5 import md5

def writeRandomFile(fn, size, start='', add='a'):
    f = open(fn, 'wb')
    m = md5()
    m.update(start)
    assert(len(add) != 0)
    while size > 0:
        d = m.digest()
        if size < len(d):
            d=d[:size]
        f.write(d)
        size -= len(d)
        m.update(add)
    f.close()


def check_call(cmd):
    r = subprocess.call(cmd, shell=True)
    if r != 0:
        raise Exception('error executing command')

class TestCpio(unittest.TestCase):
    def setUp(self):
        self.doXZ = False
        self.md5data = ''

        # create some archive from scratch
        shutil.rmtree('archive', True)
        os.mkdir('archive')
        writeRandomFile('archive/data', 10491)
        self.md5data = md5(open('archive/data').read()).hexdigest()
        check_call("find archive | cpio -o -H newc > archive.cpio")
        check_call("gzip -c < archive.cpio > archive.cpio.gz")
        check_call("bzip2 -c < archive.cpio > archive.cpio.bz2")
        try:
            import lzma
            self.doXZ = subprocess.call("xz --check=crc32 --lzma2=dict=1MiB < archive.cpio > archive.cpio.xz", shell=True) == 0
        except:
            self.doXZ = False

    def tearDown(self):
        check_call("rm -rf archive archive.cpio*")

    # TODO check with file (like 'r:*')
    # TODO use cat to check properly for pipes
    def archiveExtract(self, fn, fmt='r|*'):
        arc = CpioFile.open(fn, fmt)
        found = False
        for f in arc:
            if f.isfile():
                data = arc.extractfile(f).read()
                self.assertEqual(len(data), f.size)
                self.assertEqual(self.md5data, md5(data).hexdigest())
                found = True
        self.assertTrue(found)

    def archiveCreate(self, fn, fmt='w'):
        os.unlink(fn)
        arc = CpioFile.open(fn, fmt)
        f = arc.getcpioinfo('archive/data')
        arc.addfile(f, open('archive/data'))
        # TODO add self crafted file
        arc.close()
        # special case for XZ, test check type (crc32)
        if fmt.endswith('xz'):
            f = open(fn, 'rb')
            f.seek(6)
            self.assertEqual(f.read(2), '\x00\x01')
            f.close()
        self.archiveExtract(fn)

    def doArchive(self, fn, fmt=None):
        self.archiveExtract(fn)
        self.archiveCreate(fn, fmt is None and 'w' or 'w|%s' % fmt )
        if not fmt is None:
            self.archiveExtract(fn, 'r|%s' % fmt)

    def test_plain(self):
        self.doArchive('archive.cpio')

    def test_gz(self):
        self.doArchive('archive.cpio.gz', 'gz')

    def test_bz2(self):
        self.doArchive('archive.cpio.bz2', 'bz2')

    def test_xz(self):
        if not self.doXZ:
            return
        print 'Running test for XZ'
        self.doArchive('archive.cpio.xz', 'xz')

if __name__ == "__main__":
    unittest.main()
