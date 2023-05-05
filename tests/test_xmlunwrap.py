import unittest
import xml.dom.minidom

from xcp.xmlunwrap import (getElementsByTagName, getText, getMapAttribute,
                           getStrAttribute, getIntAttribute, XmlUnwrapError)

class TestXmlUnwrap(unittest.TestCase):
    def setUp(self):
        a_text = """<installation mode='test' integer='1'>
        <fred>text1</fred>
        <fred>text2</fred>
        </installation>"""
        xmldoc = xml.dom.minidom.parseString(a_text)
        self.top_el = xmldoc.documentElement

    def test(self):
        self.assertEqual(self.top_el.tagName, "installation")

        self.assertEqual([getText(el)
                          for el in getElementsByTagName(self.top_el, ["fred"])],
                         ["text1", "text2"])

        # Test xcp.xmlunwrap.getIntAttribute()
        self.assertEqual(getIntAttribute(self.top_el, ["integer"], 5), 1)
        self.assertEqual(getIntAttribute(self.top_el, ["noexist"], 5), 5)
        with self.assertRaises(XmlUnwrapError):
            getIntAttribute(self.top_el, ["nonexisting-attribute"])

        # Test xcp.xmlunwrap.getMapAttribute()
        x = getMapAttribute(self.top_el, ["mode"], [('test', 42), ('stuff', 77)])
        self.assertEqual(x, 42)
        x = getMapAttribute(self.top_el, ["made"], [('test', 42), ('stuff', 77)],
                            default='stuff')
        self.assertEqual(x, 77)

        # Test xcp.xmlunwrap.getIntAttribute()
        x = getStrAttribute(self.top_el, ["mode"])
        self.assertEqual(x, "test")
        x = getStrAttribute(self.top_el, ["made"])
        self.assertEqual(x, "")
        x = getStrAttribute(self.top_el, ["made"], None)  # pyright: ignore
        self.assertEqual(x, None)

        with self.assertRaises(XmlUnwrapError):
            x = getStrAttribute(self.top_el, ["made"], mandatory=True)
