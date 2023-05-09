import unittest

from xcp.version import Version


class TestVersion(unittest.TestCase):
    def test_ver_as_string(self):
        version = Version([1, 2, 3])
        self.assertEqual(str(version), "1.2.3")
        version = Version([2, 3, 4], "build1")
        self.assertEqual(str(version), "2.3.4-build1")

    def test_build_as_string(self):
        version = Version([1, 2, 3], "build123")
        self.assertEqual(version.build_as_string(), "build123")

    def test_from_string(self):
        version = Version.from_string("1.2.3-build123")
        self.assertEqual(version.ver, [1, 2, 3])
        self.assertEqual(version.build, "build123")

    def test_eq(self):
        version1 = Version([1, 2, 3], "build123")
        version2 = Version([1, 2, 3], "build456")
        self.assertTrue(version1 == version2)

    def test_ne(self):
        version1 = Version([1, 2, 3], "build123")
        version2 = Version([1, 2, 4], "build123")
        self.assertTrue(version1 != version2)

    def test_lt(self):
        version1 = Version([1, 2, 3], "build123")
        version2 = Version([1, 2, 4], "build123")
        self.assertTrue(version1 < version2)

    def test_gt(self):
        version1 = Version([1, 2, 4], "build123")
        version2 = Version([1, 2, 3], "build123")
        self.assertTrue(version1 > version2)

    def test_le(self):
        version1 = Version([1, 2, 3], "build123")
        version2 = Version([1, 2, 3], "build456")
        self.assertTrue(version1 <= version2)

    def test_ge(self):
        version1 = Version([1, 2, 3], "build456")
        version2 = Version([1, 2, 3], "build123")
        self.assertTrue(version1 >= version2)

    def test_hash(self):
        version1 = Version([1, 2, 3])
        verhash1 = hash(version1)
        self.assertIsNotNone(verhash1)
        version2 = Version([1, 2, 4])
        verhash2 = hash(version2)
        self.assertIsNotNone(verhash2)
        self.assertNotEqual(verhash2, verhash1, 1)

    def test_intify(self):
        self.assertTrue(Version.intify("1"), 1)
        self.assertTrue(Version.intify("a"), "a")
        self.assertTrue(Version.intify("1a"), "1a")


class TestVersionEdgeCases(unittest.TestCase):
    def test_ver_as_string_empty(self):
        version = Version([])
        self.assertEqual(version.ver_as_string(), "")

    def test_build_as_string_empty(self):
        version = Version([1, 2, 3])
        self.assertEqual(version.build_as_string(), "")

    def test_from_string_no_build(self):
        version = Version.from_string("1.2.3")
        self.assertEqual(version.ver, [1, 2, 3])
        self.assertIsNone(version.build)

    def test_ver_cmp_empty(self):
        version1 = Version([])
        version2 = Version([1, 2, 3])
        self.assertEqual(version1.ver_cmp(version1.ver, version2.ver), -3)

    def test_ver_cmp_different_lengths(self):
        version1 = Version([1, 2, 3])
        version2 = Version([1, 2])
        self.assertEqual(version1.ver_cmp(version1.ver, version2.ver), 1)

    def test_ver_cmp_different_values(self):
        version1 = Version([1, 2, 3])
        version2 = Version([1, 2, 4])
        self.assertEqual(version1.ver_cmp(version1.ver, version2.ver), -1)
