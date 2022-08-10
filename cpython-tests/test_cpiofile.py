import sys
import os
import shutil
import tempfile
import StringIO

import unittest
import cpiofile

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

    def test_old_dirtype(self):
        """Test old style dirtype member (bug #1336623).
        """
        # Old cpios create directory members using a REGTYPE
        # header with a "/" appended to the filename field.

        # Create an old cpio style directory entry.
        filename = tmpname()
        cpioinfo = cpiofile.CpioInfo("directory/")
        cpioinfo.type = cpiofile.REGTYPE

        fobj = open(filename, "w")
        fobj.write(cpioinfo.tobuf())
        fobj.close()

        try:
            # Test if it is still a directory entry when
            # read back.
            cpio = cpiofile.open(filename)
            cpioinfo = cpio.getmembers()[0]
            cpio.close()

            self.assert_(cpioinfo.type == cpiofile.DIRTYPE)
            self.assert_(cpioinfo.name.endswith("/"))
        finally:
            try:
                os.unlink(filename)
            except:
                pass

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

            if t2.islnk() or t2.issym():
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

    def test_posix(self):
        self.dst.posix = 1
        self._test()

    def test_nonposix(self):
        self.dst.posix = 0
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
            if self.dst.posix and len(cpioinfo.name) > cpiofile.LENGTH_NAME and "/" not in cpioinfo.name:
                self.assertRaises(ValueError, self.dst.addfile,
                                 cpioinfo, f)
            else:
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


class Write100Test(BaseTest):
    # The name field in a cpio header stores strings of at most 100 chars.
    # If a string is shorter than 100 chars it has to be padded with '\0',
    # which implies that a string of exactly 100 chars is stored without
    # a trailing '\0'.

    def setUp(self):
        self.name = "01234567890123456789012345678901234567890123456789"
        self.name += "01234567890123456789012345678901234567890123456789"

        self.cpio = cpiofile.open(tmpname(), "w")
        t = cpiofile.CpioInfo(self.name)
        self.cpio.addfile(t)
        self.cpio.close()

        self.cpio = cpiofile.open(tmpname())

    def tearDown(self):
        self.cpio.close()

    def test(self):
        self.assertEqual(self.cpio.getnames()[0], self.name,
                "failed to store 100 char filename")


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

    def test_padding(self):
        self.dst.close()

        if self.comp == "gz":
            f = gzip.GzipFile(self.dstname)
            s = f.read()
            f.close()
        elif self.comp == "bz2":
            f = bz2.BZ2Decompressor()
            s = file(self.dstname).read()
            s = f.decompress(s)
            self.assertEqual(len(f.unused_data), 0, "trailing data")
        else:
            f = file(self.dstname)
            s = f.read()
            f.close()

        self.assertEqual(s.count("\0"), cpiofile.RECORDSIZE,
                         "incorrect zero padding")


class WriteGNULongTest(unittest.TestCase):
    """This testcase checks for correct creation of GNU Longname
       and Longlink extensions.

       It creates a cpiofile and adds empty members with either
       long names, long linknames or both and compares the size
       of the cpiofile with the expected size.

       It checks for SF bug #812325 in CpioFile._create_gnulong().

       While I was writing this testcase, I noticed a second bug
       in the same method:
       Long{names,links} weren't null-terminated which lead to
       bad cpiofiles when their length was a multiple of 512. This
       is tested as well.
    """

    def _length(self, s):
        blocks, remainder = divmod(len(s) + 1, 512)
        if remainder:
            blocks += 1
        return blocks * 512

    def _calc_size(self, name, link=None):
        # initial cpio header
        count = 512

        if len(name) > cpiofile.LENGTH_NAME:
            # gnu longname extended header + longname
            count += 512
            count += self._length(name)

        if link is not None and len(link) > cpiofile.LENGTH_LINK:
            # gnu longlink extended header + longlink
            count += 512
            count += self._length(link)

        return count

    def _test(self, name, link=None):
        cpioinfo = cpiofile.CpioInfo(name)
        if link:
            cpioinfo.linkname = link
            cpioinfo.type = cpiofile.LNKTYPE

        cpio = cpiofile.open(tmpname(), "w")
        cpio.posix = False
        cpio.addfile(cpioinfo)

        v1 = self._calc_size(name, link)
        v2 = cpio.offset
        self.assertEqual(v1, v2, "GNU longname/longlink creation failed")

        cpio.close()

        cpio = cpiofile.open(tmpname())
        member = cpio.next()
        self.failIf(member is None, "unable to read longname member")
        self.assert_(cpioinfo.name == member.name and \
                     cpioinfo.linkname == member.linkname, \
                     "unable to read longname member")

    def test_longname_1023(self):
        self._test(("longnam/" * 127) + "longnam")

    def test_longname_1024(self):
        self._test(("longnam/" * 127) + "longname")

    def test_longname_1025(self):
        self._test(("longnam/" * 127) + "longname_")

    def test_longlink_1023(self):
        self._test("name", ("longlnk/" * 127) + "longlnk")

    def test_longlink_1024(self):
        self._test("name", ("longlnk/" * 127) + "longlink")

    def test_longlink_1025(self):
        self._test("name", ("longlnk/" * 127) + "longlink_")

    def test_longnamelink_1023(self):
        self._test(("longnam/" * 127) + "longnam",
                   ("longlnk/" * 127) + "longlnk")

    def test_longnamelink_1024(self):
        self._test(("longnam/" * 127) + "longname",
                   ("longlnk/" * 127) + "longlink")

    def test_longnamelink_1025(self):
        self._test(("longnam/" * 127) + "longname_",
                   ("longlnk/" * 127) + "longlink_")

class ReadGNULongTest(unittest.TestCase):

    def setUp(self):
        self.cpio = cpiofile.open(cpioname())

    def tearDown(self):
        self.cpio.close()

    def test_1471427(self):
        """Test reading of longname (bug #1471427).
        """
        name = "test/" * 20 + "0-REGTYPE"
        try:
            cpioinfo = self.cpio.getmember(name)
        except KeyError:
            cpioinfo = None
        self.assert_(cpioinfo is not None, "longname not found")
        self.assert_(cpioinfo.type != cpiofile.DIRTYPE, "read longname as dirtype")

    def test_read_name(self):
        name = ("0-LONGNAME-" * 10)[:101]
        try:
            cpioinfo = self.cpio.getmember(name)
        except KeyError:
            cpioinfo = None
        self.assert_(cpioinfo is not None, "longname not found")

    def test_read_link(self):
        link = ("1-LONGLINK-" * 10)[:101]
        name = ("0-LONGNAME-" * 10)[:101]
        try:
            cpioinfo = self.cpio.getmember(link)
        except KeyError:
            cpioinfo = None
        self.assert_(cpioinfo is not None, "longlink not found")
        self.assert_(cpioinfo.linkname == name, "linkname wrong")

    def test_truncated_longname(self):
        f = open(cpioname())
        fobj = StringIO.StringIO(f.read(1024))
        f.close()
        cpio = cpiofile.open(name="foo.cpio", fileobj=fobj)
        self.assert_(len(cpio.getmembers()) == 0, "")
        cpio.close()


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
        self.assertEqual(cpioinfo.type, cpiofile.REGTYPE,
                "add file as regular failed")

    def test_add_hardlink(self):
        # If st_nlink > 1 then the same file will be added as
        # LNKTYPE.
        os.link(self.foo, self.bar)
        cpioinfo = self.cpio.getcpioinfo(self.foo)
        self.assertEqual(cpioinfo.type, cpiofile.LNKTYPE,
                "add file as hardlink failed")

        cpioinfo = self.cpio.getcpioinfo(self.bar)
        self.assertEqual(cpioinfo.type, cpiofile.LNKTYPE,
                "add file as hardlink failed")

    def test_dereference_hardlink(self):
        self.cpio.dereference = True
        os.link(self.foo, self.bar)
        cpioinfo = self.cpio.getcpioinfo(self.bar)
        self.assertEqual(cpioinfo.type, cpiofile.REGTYPE,
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

class HeaderErrorTest(unittest.TestCase):

    def test_truncated_header(self):
        self.assertRaises(cpiofile.HeaderError, cpiofile.CpioInfo.frombuf, "")
        self.assertRaises(cpiofile.HeaderError, cpiofile.CpioInfo.frombuf, "filename\0")
        self.assertRaises(cpiofile.HeaderError, cpiofile.CpioInfo.frombuf, "\0" * 511)
        self.assertRaises(cpiofile.HeaderError, cpiofile.CpioInfo.frombuf, "\0" * 513)

    def test_empty_header(self):
        self.assertRaises(cpiofile.HeaderError, cpiofile.CpioInfo.frombuf, "\0" * 512)

    def test_invalid_header(self):
        buf = cpiofile.CpioInfo("filename").tobuf()
        buf = buf[:148] + "foo\0\0\0\0\0" + buf[156:] # invalid number field.
        self.assertRaises(cpiofile.HeaderError, cpiofile.CpioInfo.frombuf, buf)

    def test_bad_checksum(self):
        buf = cpiofile.CpioInfo("filename").tobuf()
        b = buf[:148] + "        " + buf[156:] # clear the checksum field.
        self.assertRaises(cpiofile.HeaderError, cpiofile.CpioInfo.frombuf, b)
        b = "a" + buf[1:] # manipulate the buffer, so checksum won't match.
        self.assertRaises(cpiofile.HeaderError, cpiofile.CpioInfo.frombuf, b)

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
        HeaderErrorTest,
        OpenFileobjTest,
        ReadTest,
        ReadStreamTest,
        ReadDetectTest,
        ReadDetectFileobjTest,
        ReadAsteriskTest,
        ReadStreamAsteriskTest,
        WriteTest,
        Write100Test,
        WriteSize0Test,
        WriteStreamTest,
        WriteGNULongTest,
        ReadGNULongTest,
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
