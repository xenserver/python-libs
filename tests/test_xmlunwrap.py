import unittest
import xml.dom.minidom

from xcp.xmlunwrap import (getElementsByTagName, getText, getMapAttribute,
                           getStrAttribute, XmlUnwrapError)

class TestXmlUnwrap(unittest.TestCase):
    def setUp(self):
        a_text = """<installation mode='test'>
        <fred>text1</fred>
        <fred>text2</fred>
        </installation>"""
        xmldoc = xml.dom.minidom.parseString(a_text)
        self.top_el = xmldoc.documentElement

    def test(self):
        self.assertEqual(self.top_el.tagName, "installation")

        self.assertEqual([getText(el)
                          for el in getElementsByTagName(self.top_el, ["fred"])],
                         [b"text1", b"text2"])

        x = getMapAttribute(self.top_el, ["mode"], [(b'test', 42), (b'stuff', 77)])
        self.assertEqual(x, 42)
        x = getMapAttribute(self.top_el, ["made"], [(b'test', 42), (b'stuff', 77)],
                            default=b'stuff')
        self.assertEqual(x, 77)

        x = getStrAttribute(self.top_el, ["mode"])
        self.assertEqual(x, b"test")
        x = getStrAttribute(self.top_el, ["made"])
        self.assertEqual(x, b"")
        x = getStrAttribute(self.top_el, ["made"], None)
        self.assertEqual(x, None)

        with self.assertRaises(XmlUnwrapError):
            x = getStrAttribute(self.top_el, ["made"], mandatory=True)
