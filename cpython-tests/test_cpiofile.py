import sys
import os
import shutil
import tempfile
import StringIO

import unittest
from xcp import cpiofile

from test import test_support

# Check for our compression modules.
try:
    import gzip
    gzip.GzipFile
except (ImportError, AttributeError):
    gzip = None
try:
    import bz2
except ImportError:
    bz2 = None

def path(path):
    return test_support.findfile(path)

testcpio = path("testcpio.cpio")
tempdir = os.path.join(tempfile.gettempdir(), "testcpio" + os.extsep + "dir")
tempname = test_support.TESTFN
membercount = 12

def cpioname(comp=""):
    if not comp:
        return testcpio
    return os.path.join(tempdir, "%s%s%s" % (testcpio, os.extsep, comp))

def dirname():
    if not os.path.exists(tempdir):
        os.mkdir(tempdir)
    return tempdir

def tmpname():
    return tempname


class BaseTest(unittest.TestCase):
    comp = ''
    mode = 'r'
    sep = ':'

    def setUp(self):
        mode = self.mode + self.sep + self.comp
        self.cpio = cpiofile.open(cpioname(self.comp), mode)

    def tearDown(self):
        self.cpio.close()

class ReadTest(BaseTest):

    def test(self):
        """Test member extraction.
        """
        members = 0
        for cpioinfo in self.cpio:
            members += 1
            if not cpioinfo.isreg():
                continue
            f = self.cpio.extractfile(cpioinfo)
            self.assert_(len(f.read()) == cpioinfo.size,
                         "size read does not match expected size")
            f.close()

        self.assert_(members == membercount,
                     "could not find all members")

    def test_sparse(self):
        """Test sparse member extraction.
        """
        if self.sep != "|":
            f1 = self.cpio.extractfile("S-SPARSE")
            f2 = self.cpio.extractfile("S-SPARSE-WITH-NULLS")
            self.assert_(f1.read() == f2.read(),
                         "_FileObject failed on sparse file member")

    def test_readlines(self):
        """Test readlines() method of _FileObject.
        """
        if self.sep != "|":
            filename = "0-REGTYPE-TEXT"
            self.cpio.extract(filename, dirname())
            f = open(os.path.join(dirname(), filename), "rU")
            lines1 = f.readlines()
            f.close()
            lines2 = self.cpio.extractfile(filename).readlines()
            self.assert_(lines1 == lines2,
                         "_FileObject.readline() does not work correctly")

    def test_iter(self):
        # Test iteration over ExFileObject.
        if self.sep != "|":
            filename = "0-REGTYPE-TEXT"
            self.cpio.extract(filename, dirname())
            f = open(os.path.join(dirname(), filename), "rU")
            lines1 = f.readlines()
            f.close()
            lines2 = [line for line in self.cpio.extractfile(filename)]
            self.assert_(lines1 == lines2,
                         "ExFileObject iteration does not work correctly")

    def test_seek(self):
        """Test seek() method of _FileObject, incl. random reading.
        """
        if self.sep != "|":
            filename = "0-REGTYPE-TEXT"
            self.cpio.extract(filename, dirname())
            f = open(os.path.join(dirname(), filename), "rb")
            data = f.read()
            f.close()

            cpioinfo = self.cpio.getmember(filename)
            fobj = self.cpio.extractfile(cpioinfo)

            text = fobj.read()
            fobj.seek(0)
            self.assert_(0 == fobj.tell(),
                         "seek() to file's start failed")
            fobj.seek(2048, 0)
            self.assert_(2048 == fobj.tell(),
                         "seek() to absolute position failed")
            fobj.seek(-1024, 1)
            self.assert_(1024 == fobj.tell(),
                         "seek() to negative relative position failed")
            fobj.seek(1024, 1)
            self.assert_(2048 == fobj.tell(),
                         "seek() to positive relative position failed")
            s = fobj.read(10)
            self.assert_(s == data[2048:2058],
                         "read() after seek failed")
            fobj.seek(0, 2)
            self.assert_(cpioinfo.size == fobj.tell(),
                         "seek() to file's end failed")
            self.assert_(fobj.read() == "",
                         "read() at file's end did not return empty string")
            fobj.seek(-cpioinfo.size, 2)
            self.assert_(0 == fobj.tell(),
                         "relative seek() to file's start failed")
            fobj.seek(512)
            s1 = fobj.readlines()
            fobj.seek(512)
            s2 = fobj.readlines()
            self.assert_(s1 == s2,
                         "readlines() after seek failed")
            fobj.seek(0)
            self.assert_(len(fobj.readline()) == fobj.tell(),
                         "tell() after readline() failed")
            fobj.seek(512)
            self.assert_(len(fobj.readline()) + 512 == fobj.tell(),
                         "tell() after seek() and readline() failed")
            fobj.seek(0)
            line = fobj.readline()
            self.assert_(fobj.read() == data[len(line):],
                         "read() after readline() failed")
            fobj.close()

class ReadStreamTest(ReadTest):
    sep = "|"

    def test(self):
        """Test member extraction, and for StreamError when
           seeking backwards.
        """
        ReadTest.test(self)
        cpioinfo = self.cpio.getmembers()[0]
        f = self.cpio.extractfile(cpioinfo)
        self.assertRaises(cpiofile.StreamError, f.read)

    def test_stream(self):
        """Compare the normal cpio and the stream cpio.
        """
        stream = self.cpio
        cpio = cpiofile.open(cpioname(), 'r')

        while 1:
            t1 = cpio.next()
            t2 = stream.next()
            if t1 is None:
                break
            self.assert_(t2 is not None, "stream.next() failed.")

            if t2.issym():
                self.assertRaises(cpiofile.StreamError, stream.extractfile, t2)
                continue
            v1 = cpio.extractfile(t1)
            v2 = stream.extractfile(t2)
            if v1 is None:
                continue
            self.assert_(v2 is not None, "stream.extractfile() failed")
            self.assert_(v1.read() == v2.read(), "stream extraction failed")

        cpio.close()
        stream.close()

class ReadDetectTest(ReadTest):

    def setUp(self):
        self.cpio = cpiofile.open(cpioname(self.comp), self.mode)

class ReadDetectFileobjTest(ReadTest):

    def setUp(self):
        name = cpioname(self.comp)
        self.cpio = cpiofile.open(name, mode=self.mode,
                                fileobj=open(name, "rb"))

class ReadAsteriskTest(ReadTest):

    def setUp(self):
        mode = self.mode + self.sep + "*"
        self.cpio = cpiofile.open(cpioname(self.comp), mode)

class ReadStreamAsteriskTest(ReadStreamTest):

    def setUp(self):
        mode = self.mode + self.sep + "*"
        self.cpio = cpiofile.open(cpioname(self.comp), mode)

class WriteTest(BaseTest):
    mode = 'w'

    def setUp(self):
        mode = self.mode + self.sep + self.comp
        self.src = cpiofile.open(cpioname(self.comp), 'r')
        self.dstname = tmpname()
        self.dst = cpiofile.open(self.dstname, mode)

    def tearDown(self):
        self.src.close()
        self.dst.close()

    def test(self):
        self._test()

    def test_small(self):
        self.dst.add(os.path.join(os.path.dirname(__file__),"cfgparser.1"))
        self.dst.close()
        self.assertNotEqual(os.stat(self.dstname).st_size, 0)

    def _test(self):
        for cpioinfo in self.src:
            if not cpioinfo.isreg():
                continue
            f = self.src.extractfile(cpioinfo)
            self.dst.addfile(cpioinfo, f)

    def test_add_self(self):
        dstname = os.path.abspath(self.dstname)

        self.assertEqual(self.dst.name, dstname, "archive name must be absolute")

        self.dst.add(dstname)
        self.assertEqual(self.dst.getnames(), [], "added the archive to itself")

        cwd = os.getcwd()
        os.chdir(dirname())
        self.dst.add(dstname)
        os.chdir(cwd)
        self.assertEqual(self.dst.getnames(), [], "added the archive to itself")


class WriteSize0Test(BaseTest):
    mode = 'w'

    def setUp(self):
        self.tmpdir = dirname()
        self.dstname = tmpname()
        self.dst = cpiofile.open(self.dstname, "w")

    def tearDown(self):
        self.dst.close()

    def test_file(self):
        path = os.path.join(self.tmpdir, "file")
        f = open(path, "w")
        f.close()
        cpioinfo = self.dst.getcpioinfo(path)
        self.assertEqual(cpioinfo.size, 0)
        f = open(path, "w")
        f.write("aaa")
        f.close()
        cpioinfo = self.dst.getcpioinfo(path)
        self.assertEqual(cpioinfo.size, 3)

    def test_directory(self):
        path = os.path.join(self.tmpdir, "directory")
        if os.path.exists(path):
            # This shouldn't be necessary, but is <wink> if a previous
            # run was killed in mid-stream.
            shutil.rmtree(path)
        os.mkdir(path)
        cpioinfo = self.dst.getcpioinfo(path)
        self.assertEqual(cpioinfo.size, 0)

    def test_symlink(self):
        if hasattr(os, "symlink"):
            path = os.path.join(self.tmpdir, "symlink")
            os.symlink("link_target", path)
            cpioinfo = self.dst.getcpioinfo(path)
            self.assertEqual(cpioinfo.size, 0)


class WriteStreamTest(WriteTest):
    sep = '|'

    # FIXME could have a test_trailer()

class ExtractHardlinkTest(BaseTest):

    def test_hardlink(self):
        """Test hardlink extraction (bug #857297)
        """
        # Prevent errors from being caught
        self.cpio.errorlevel = 1

        self.cpio.extract("0-REGTYPE", dirname())
        try:
            # Extract 1-LNKTYPE which is a hardlink to 0-REGTYPE
            self.cpio.extract("1-LNKTYPE", dirname())
        except EnvironmentError, e:
            import errno
            if e.errno == errno.ENOENT:
                self.fail("hardlink not extracted properly")

class CreateHardlinkTest(BaseTest):
    """Test the creation of LNKTYPE (hardlink) members in an archive.
       In this respect cpiofile.py mimics the behaviour of GNU cpio: If
       a file has a st_nlink > 1, it will be added a REGTYPE member
       only the first time.
    """

    def setUp(self):
        self.cpio = cpiofile.open(tmpname(), "w")

        self.foo = os.path.join(dirname(), "foo")
        self.bar = os.path.join(dirname(), "bar")

        if os.path.exists(self.foo):
            os.remove(self.foo)
        if os.path.exists(self.bar):
            os.remove(self.bar)

        f = open(self.foo, "w")
        f.write("foo")
        f.close()
        self.cpio.add(self.foo)

    def test_add_twice(self):
        # If st_nlink == 1 then the same file will be added as
        # REGTYPE every time.
        cpioinfo = self.cpio.getcpioinfo(self.foo)
        self.assertTrue(cpioinfo.isreg(),
                "add file as regular failed")

    def test_add_hardlink(self):
        # If st_nlink > 1 then the same file will be added as
        # LNKTYPE.
        os.link(self.foo, self.bar)
        cpioinfo = self.cpio.getcpioinfo(self.foo)
        self.assertTrue(cpioinfo.islnk(),
                "add file as hardlink failed")

        cpioinfo = self.cpio.getcpioinfo(self.bar)
        self.assertTrue(cpioinfo.islnk(),
                "add file as hardlink failed")

    def test_dereference_hardlink(self):
        self.cpio.dereference = True
        os.link(self.foo, self.bar)
        cpioinfo = self.cpio.getcpioinfo(self.bar)
        self.assertTrue(cpioinfo.isreg(),
                "dereferencing hardlink failed")


# Gzip TestCases
class ReadTestGzip(ReadTest):
    comp = "gz"
class ReadStreamTestGzip(ReadStreamTest):
    comp = "gz"
class WriteTestGzip(WriteTest):
    comp = "gz"
class WriteStreamTestGzip(WriteStreamTest):
    comp = "gz"
class ReadDetectTestGzip(ReadDetectTest):
    comp = "gz"
class ReadDetectFileobjTestGzip(ReadDetectFileobjTest):
    comp = "gz"
class ReadAsteriskTestGzip(ReadAsteriskTest):
    comp = "gz"
class ReadStreamAsteriskTestGzip(ReadStreamAsteriskTest):
    comp = "gz"

# Filemode test cases

class FileModeTest(unittest.TestCase):
    def test_modes(self):
        self.assertEqual(cpiofile.filemode(0755), '-rwxr-xr-x')
        self.assertEqual(cpiofile.filemode(07111), '---s--s--t')

class OpenFileobjTest(BaseTest):
    # Test for SF bug #1496501.

    def test_opener(self):
        fobj = StringIO.StringIO("foo\n")
        try:
            cpiofile.open("", "r", fileobj=fobj)
        except cpiofile.ReadError:
            self.assertEqual(fobj.tell(), 0, "fileobj's position has moved")

if bz2:
    # Bzip2 TestCases
    class ReadTestBzip2(ReadTestGzip):
        comp = "bz2"
    class ReadStreamTestBzip2(ReadStreamTestGzip):
        comp = "bz2"
    class WriteTestBzip2(WriteTest):
        comp = "bz2"
    class WriteStreamTestBzip2(WriteStreamTestGzip):
        comp = "bz2"
    class ReadDetectTestBzip2(ReadDetectTest):
        comp = "bz2"
    class ReadDetectFileobjTestBzip2(ReadDetectFileobjTest):
        comp = "bz2"
    class ReadAsteriskTestBzip2(ReadAsteriskTest):
        comp = "bz2"
    class ReadStreamAsteriskTestBzip2(ReadStreamAsteriskTest):
        comp = "bz2"

# If importing gzip failed, discard the Gzip TestCases.
if not gzip:
    del ReadTestGzip
    del ReadStreamTestGzip
    del WriteTestGzip
    del WriteStreamTestGzip

def test_main():
    # Create archive.
    f = open(cpioname(), "rb")
    fguts = f.read()
    f.close()
    if gzip:
        # create testcpio.cpio.gz
        cpio = gzip.open(cpioname("gz"), "wb")
        cpio.write(fguts)
        cpio.close()
    if bz2:
        # create testcpio.cpio.bz2
        cpio = bz2.BZ2File(cpioname("bz2"), "wb")
        cpio.write(fguts)
        cpio.close()

    tests = [
        FileModeTest,
        OpenFileobjTest,
        ReadTest,
        ReadStreamTest,
        ReadDetectTest,
        ReadDetectFileobjTest,
        ReadAsteriskTest,
        ReadStreamAsteriskTest,
        WriteTest,
        WriteSize0Test,
        WriteStreamTest,
    ]

    if hasattr(os, "link"):
        tests.append(ExtractHardlinkTest)
        tests.append(CreateHardlinkTest)

    if gzip:
        tests.extend([
            ReadTestGzip, ReadStreamTestGzip,
            WriteTestGzip, WriteStreamTestGzip,
            ReadDetectTestGzip, ReadDetectFileobjTestGzip,
            ReadAsteriskTestGzip, ReadStreamAsteriskTestGzip
        ])

    if bz2:
        tests.extend([
            ReadTestBzip2, ReadStreamTestBzip2,
            WriteTestBzip2, WriteStreamTestBzip2,
            ReadDetectTestBzip2, ReadDetectFileobjTestBzip2,
            ReadAsteriskTestBzip2, ReadStreamAsteriskTestBzip2
        ])
    try:
        test_support.run_unittest(*tests)
    finally:
        if gzip:
            os.remove(cpioname("gz"))
        if bz2:
            os.remove(cpioname("bz2"))
        if os.path.exists(dirname()):
            shutil.rmtree(dirname())
        if os.path.exists(tmpname()):
            os.remove(tmpname())

if __name__ == "__main__":
    test_main()
