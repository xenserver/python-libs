import unittest

from xcp.net.mac import MAC


class TestInvalidMAC(unittest.TestCase):
    """
    Due to the classmethod predicate is_valid, we must test
    both the normal constructor and the result from is_valid
    """

    def test_null_str(self):
        val = ""
        with self.assertRaises(ValueError):
            MAC(val)
        self.assertFalse(MAC.is_valid(val))

    def test_non_str(self):

        for val in [None, [], {}]:
            with self.assertRaises(TypeError):
                MAC(val)
            self.assertFalse(MAC.is_valid(val))

    def test_colon_too_few_octets(self):
        val = "00:00:00:00:00"
        with self.assertRaises(ValueError):
            MAC(val)
        self.assertFalse(MAC.is_valid(val))

    def test_colon_invalid_octets(self):

        for val in [ "12:34:56:78:90:abc",
                     "-12:34:56:78:90:AB",
                     "12:34:56g:78:90:ab"
                     "12:34::78:90:ab"
                     ]:
            with self.assertRaises(ValueError):
                MAC(val)
            self.assertFalse(MAC.is_valid(val))

    def test_colon_too_many_octets(self):
        val = "00:00:00:00:00:00:00"
        with self.assertRaises(ValueError):
            MAC(val)
        self.assertFalse(MAC.is_valid(val))

    def test_dash_too_few_octets(self):
        val = "00-00-00-00-00"
        with self.assertRaises(ValueError):
            MAC(val)
        self.assertFalse(MAC.is_valid(val))

    def test_dash_too_many_octets(self):
        val = "00-00-00-00-00-00-00"
        with self.assertRaises(ValueError):
            MAC(val)
        self.assertFalse(MAC.is_valid(val))

    def test_dotquad_too_few_quads(self):
        val = "0000.0000"
        with self.assertRaises(ValueError):
            MAC(val)
        self.assertFalse(MAC.is_valid(val))

    def test_dotquad_invalid_quads(self):

        for val in [ "0123.4567.89abc",
                     ".4567.89AB",
                     "abcd.efgh.ijkl",
                     "1234.-5678.90Ab"
                     ]:
            with self.assertRaises(ValueError):
                MAC(val)
            self.assertFalse(MAC.is_valid(val))

    def test_dotquad_too_many_quads(self):
        val = "0000.0000.0000.0000"
        with self.assertRaises(ValueError):
            MAC(val)
        self.assertFalse(MAC.is_valid(val))

class TestValidMAC(unittest.TestCase):

    def test_unicast_global(self):

        for val in [ "00:00:00:00:00:00",
                     "00-00-00-00-00-00",
                     "0000.0000.0000"
                     ]:

            mac = MAC(val)

            self.assertEqual(mac.octets, [0, 0, 0, 0, 0, 0])
            self.assertEqual(mac.integer, 0)

            self.assertTrue(mac.is_unicast())
            self.assertFalse(mac.is_multicast())
            self.assertTrue(mac.is_global())
            self.assertFalse(mac.is_local())

            self.assertEqual(mac.as_string(":"), "00:00:00:00:00:00")
            self.assertEqual(mac.as_string("-"), "00-00-00-00-00-00")
            self.assertEqual(mac.as_string("."), "0000.0000.0000")

    def test_multicast_global(self):

        for val in [ "01:00:00:00:00:00",
                     "01-00-00-00-00-00",
                     "0100.0000.0000"
                     ]:

            mac = MAC(val)

            self.assertEqual(mac.octets, [1, 0, 0, 0, 0, 0])
            self.assertEqual(mac.integer, 0x010000000000)

            self.assertFalse(mac.is_unicast())
            self.assertTrue(mac.is_multicast())
            self.assertTrue(mac.is_global())
            self.assertFalse(mac.is_local())

            self.assertEqual(mac.as_string(":"), "01:00:00:00:00:00")
            self.assertEqual(mac.as_string("-"), "01-00-00-00-00-00")
            self.assertEqual(mac.as_string("."), "0100.0000.0000")
    def test_unicast_local(self):

        for val in [ "02:00:00:00:00:00",
                     "02-00-00-00-00-00",
                     "0200.0000.0000"
                     ]:

            mac = MAC(val)

            self.assertEqual(mac.octets, [2, 0, 0, 0, 0, 0])
            self.assertEqual(mac.integer, 0x020000000000)

            self.assertTrue(mac.is_unicast())
            self.assertFalse(mac.is_multicast())
            self.assertFalse(mac.is_global())
            self.assertTrue(mac.is_local())

            self.assertEqual(mac.as_string(":"), "02:00:00:00:00:00")
            self.assertEqual(mac.as_string("-"), "02-00-00-00-00-00")
            self.assertEqual(mac.as_string("."), "0200.0000.0000")

    def test_multicast_local(self):

        for val in [ "03:00:00:00:00:00",
                     "03-00-00-00-00-00",
                     "0300.0000.0000"
                     ]:

            mac = MAC(val)

            self.assertEqual(mac.octets, [3, 0, 0, 0, 0, 0])
            self.assertEqual(mac.integer, 0x030000000000)

            self.assertFalse(mac.is_unicast())
            self.assertTrue(mac.is_multicast())
            self.assertFalse(mac.is_global())
            self.assertTrue(mac.is_local())

            self.assertEqual(mac.as_string(":"), "03:00:00:00:00:00")
            self.assertEqual(mac.as_string("-"), "03-00-00-00-00-00")
            self.assertEqual(mac.as_string("."), "0300.0000.0000")


    def test_random(self):

        for val in [ "15:52:4a:b4:c:FF",
                     "15-52-4a-b4-c-FF",
                     "1552.4ab4.cFF",
                     ]:

            mac = MAC(val)

            self.assertEqual(mac.octets, [0x15, 0x52, 0x4a, 0xb4, 0x0c, 0xff])
            self.assertEqual(mac.integer, 0x15524ab40cff)

            self.assertFalse(mac.is_unicast())
            self.assertTrue(mac.is_multicast())
            self.assertTrue(mac.is_global())
            self.assertFalse(mac.is_local())

            self.assertEqual(mac.as_string(":"), "15:52:4a:b4:0c:ff")
            self.assertEqual(mac.as_string("-"), "15-52-4a-b4-0c-ff")
            self.assertEqual(mac.as_string("."), "1552.4ab4.0cff")
            self.assertEqual(mac.as_string(":", True), "15:52:4A:B4:0C:FF")
            self.assertEqual(mac.as_string("-", True), "15-52-4A-B4-0C-FF")
            self.assertEqual(mac.as_string(".", True), "1552.4AB4.0CFF")

class TestComparisons(unittest.TestCase):

    def test_equal(self):

        m1 = MAC("12:34:56:78:90:ab")
        m2 = MAC("1234.5678.90AB")

        self.assertTrue( m1 == m2)
        self.assertFalse(m1 != m2)

        self.assertFalse(m1 <  m2)
        self.assertTrue( m1 <= m2)
        self.assertFalse(m1 >  m2)
        self.assertTrue( m1 >= m2)

    def test_unequal(self):

        m1 = MAC("12:34:56:78:90:ab")
        m2 = MAC("abcd.EFFE.0987")

        self.assertFalse(m1 == m2)
        self.assertTrue( m1 != m2)

        self.assertTrue( m1 <  m2)
        self.assertTrue( m1 <= m2)
        self.assertFalse(m1 >  m2)
        self.assertFalse(m1 >= m2)

class TestHashability(unittest.TestCase):

    def test_keys(self):

        m1 = MAC("00:00:00:00:00:00")
        m2 = MAC("12:34:56:78:90:ab")
        m3 = MAC("38:65:aC:b4:b4:b4")

        d = dict({ m1: "zero",
                   m2: "ascending",
                   m3: "random"
                   })

        self.assertEqual(len(d), 3)

        self.assertTrue( m1 in d )
        self.assertTrue( m2 in d )
        self.assertTrue( m3 in d )
        self.assertTrue( MAC("0000.0000.0000") in d )

        self.assertFalse( MAC("ab:12:56:78:23:90") in d)

        self.assertEqual(d[m1], "zero")
        self.assertEqual(d[m2], "ascending")
        self.assertEqual(d[m3], "random")
