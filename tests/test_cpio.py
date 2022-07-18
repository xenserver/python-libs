from __future__ import print_function
from hashlib import md5
import os
import shutil
import subprocess
import unittest
import warnings

from xcp.cpiofile import CpioFile, CpioInfo, CpioFileCompat, CPIO_PLAIN, CPIO_GZIPPED

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
        with open('archive/data') as fd:
            self.md5data = md5(fd.read()).hexdigest()
        check_call("find archive | cpio -o -H newc > archive.cpio")
        check_call("gzip -c < archive.cpio > archive.cpio.gz")
        check_call("bzip2 -c < archive.cpio > archive.cpio.bz2")
        try:
            import lzma         # pylint: disable=unused-variable
            self.doXZ = subprocess.call("xz --check=crc32 --lzma2=dict=1MiB"
                                        " < archive.cpio > archive.cpio.xz", shell=True) == 0
        except Exception as ex:
            # FIXME will issue warning even if test_xz is not requested
            warnings.warn("will not test cpio.xz: %s" % ex)
            self.doXZ = False

    def tearDown(self):
        check_call("rm -rf archive archive.cpio* archive2")

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
        arc.close()
        self.assertTrue(found)
        # extract with extractall and compare
        arc = CpioFile.open(fn, fmt)
        check_call("rm -rf archive2")
        os.rename('archive', 'archive2')
        arc.extractall()
        check_call("diff -rq archive2 archive")
        arc.close()

    def archiveCreate(self, fn, fmt='w'):
        os.unlink(fn)
        arc = CpioFile.open(fn, fmt)
        f = arc.getcpioinfo('archive/data')
        with open('archive/data') as fd:
            arc.addfile(f, fd)
        # test recursively add "."
        os.chdir('archive')
        arc.add(".")
        os.chdir("..")
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
            raise unittest.SkipTest("lzma package or xz tool not available")
        print('Running test for XZ')
        self.doArchive('archive.cpio.xz', 'xz')

    # CpioFileCompat testing

    def archiveExtractCompat(self, fn, comp):
        arc = CpioFileCompat(fn, mode="r", compression={"": CPIO_PLAIN,
                                                        "gz": CPIO_GZIPPED}[comp])
        found = False
        for f in arc.namelist():
            info = arc.getinfo(f)
            if info.isfile():
                data = arc.read(f)
                self.assertEqual(len(data), info.size)
                self.assertEqual(self.md5data, md5(data).hexdigest())
                found = True
        arc.close()
        self.assertTrue(found)

    def archiveCreateCompat(self, fn, comp):
        if os.path.exists(fn):
            os.unlink(fn)
        arc = CpioFileCompat(fn, mode="w", compression={"": CPIO_PLAIN,
                                                        "gz": CPIO_GZIPPED}[comp])
        arc.write('archive/data')
        arc.close()
        self.archiveExtract(fn)

    def doArchiveCompat(self, fn, fmt):
        self.archiveExtractCompat(fn, fmt)

        fn2 = "archive2" + fn[len("archive"):]
        self.archiveCreateCompat(fn2, fmt)
        self.archiveExtractCompat(fn2, fmt)

    def test_compat_plain(self):
        self.doArchiveCompat('archive.cpio', '')

    def test_compat_gz(self):
        # FIXME: this test exhibits "unclosed file" warnings when run
        # under `-Wd`
        self.doArchiveCompat('archive.cpio.gz', 'gz')
