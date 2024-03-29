from __future__ import print_function
from hashlib import md5
import lzma
import os
import sys
import shutil
import subprocess
import tempfile
import unittest
import warnings
from typing import cast

import xcp.cpiofile
from xcp.cpiofile import CpioFile, CpioFileCompat, CPIO_PLAIN, CPIO_GZIPPED

def writeRandomFile(fn, size, start=b'', add=b'a'):
    "Create a pseudo-random reproducible file from seeds `start` amd `add`"
    with open(fn, 'wb') as f:
        m = md5()
        m.update(start)
        assert add
        while size > 0:
            d = m.digest()
            if size < len(d):
                d = d[:size]
            f.write(d)
            size -= len(d)
            m.update(add)


def check_call(cmd):
    r = subprocess.call(cmd, shell=True)
    if r != 0:
        raise RuntimeError('error executing command')

class TestCpio(unittest.TestCase):
    orig_dir = os.getcwd()
    work_dir = ""

    @classmethod
    def setUpClass(cls):
        cls.work_dir = tempfile.mkdtemp()
        os.chdir(cls.work_dir)

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.orig_dir)
        shutil.rmtree(cls.work_dir)

    def setUp(self):
        self.doXZ = True
        self.md5data = ''

        # create some archive from scratch
        shutil.rmtree('archive', True)
        os.mkdir('archive')
        writeRandomFile('archive/data', 10491)
        with open('archive/data', 'rb') as fd:
            self.md5data = md5(fd.read()).hexdigest()
        os.symlink("data", "archive/linkname")
        # fixed timestamps for cpio reproducibility
        os.utime('archive/linkname', (0, 0))
        os.utime('archive/data', (0, 0))
        os.utime('archive', (0, 0))

        try:
            check_call("find archive | cpio --reproducible -o -H newc > archive.cpio")
        except:
            raise unittest.SkipTest("cpio tool not available")
        check_call("gzip -c < archive.cpio > archive.cpio.gz")
        check_call("bzip2 -c < archive.cpio > archive.cpio.bz2")
        try:
            self.doXZ = subprocess.call("xz --check=crc32 --lzma2=dict=1MiB"
                                        " < archive.cpio > archive.cpio.xz", shell=True) == 0
        except Exception as ex:
            warnings.warn("will not test cpio.xz: %s" % ex)
            self.doXZ = False

    def tearDown(self):
        check_call("rm -rf archive archive.cpio* archive2 archive2.cpio*")

    def archiveExtract(self, fn, fmt='r|*'):
        arc = CpioFile.open(fn, fmt)
        names = []
        for f in arc:
            if f.issym():
                assert f.name == "archive/linkname"
                assert f.linkname == "data"
                cpio_header = f.tobuf()
                # CpioInfo.frombuf() returns a CpioInfo obj but does not set names from the header:
                assert cpio_header[:100] == xcp.cpiofile.CpioInfo.frombuf(cpio_header).tobuf()[:100]
                names.append(f.name)

            if f.isfile():
                assert f.name == "archive/data"
                data = cast(xcp.cpiofile.ExFileObject, arc.extractfile(f)).read()
                self.assertEqual(len(data), f.size)
                self.assertEqual(self.md5data, md5(data).hexdigest())
                names.append(f.name)
        arc.close()
        assert sorted(names) == ["archive/data", "archive/linkname"]
        # extract with extractall and compare
        arc = CpioFile.open(fn, fmt)
        shutil.rmtree('archive2', True)
        os.rename('archive', 'archive2')
        arc.extractall()
        check_call("diff -rq archive2 archive")
        arc.close()

    def archiveCreate(self, fn, fmt='w'):
        if os.path.exists(fn):
            os.unlink(fn)
        arc = CpioFile.open(fn, fmt)
        # Recursively add "." as directory "archive"
        os.chdir('archive')
        arc.add(".", "archive")
        os.chdir("..")
        arc.close()
        # special case for XZ, test check type (crc32)
        if fmt.endswith('xz'):
            with open(fn, 'rb') as f:
                # check xz magic
                self.assertEqual(f.read(6), b"\xfd7zXZ\0")
                # check stream flags
                if sys.version_info < (3, 0):
                    expected_flags = b'\x00\x01' # pylzma defaults to CRC32
                else:
                    expected_flags = b'\x00\x04' # python3 defaults to CRC64
                self.assertEqual(f.read(2), expected_flags)
        self.archiveExtract(fn)

    def doArchive(self, fn, fmt=None):
        self.archiveExtract(fn)
        fn2 = "archive2" + fn[len("archive"):]
        print("creating %s" % fn2)
        self.archiveCreate(fn2, fmt is None and "w" or "w:%s" % fmt)
        if fmt is not None:
            self.archiveExtract(fn2, "r:%s" % fmt)

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

    def test_cover_xzopen_pass_fileobj(self):
        """Cover CpioFile.xzopen() not supporting receiving a fileobj argument"""
        class MockCpioFile(CpioFile):
            def __init__(self):  # pylint: disable=super-init-not-called
                pass
        with self.assertRaises(xcp.cpiofile.CompressionError):
            MockCpioFile.xzopen(name="", mode="r", fileobj=lzma.LZMAFile("/dev/null"))
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
        arc.write('archive/linkname')
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
        self.doArchiveCompat('archive.cpio.gz', 'gz')
