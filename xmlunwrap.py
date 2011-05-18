#!/usr/bin/env python
# Copyright (c) 2011 Citrix Systems, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; version 2.1 only. with the special
# exception on linking described in file LICENSE.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

"""xmlunwrap - general methods to unwrap XML elements & attributes"""

import xml.dom.minidom


class XmlUnwrapError(Exception):
    pass

def getText(nodelist):
    rc = ""

    for node in nodelist.childNodes:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc.encode().strip()

def getElementsByTagName(el, tags, mandatory = False):
    matching = []
    for tag in tags:
        matching.extend(el.getElementsByTagName(tag))
    if mandatory and len(matching) == 0:
        raise XmlUnwrapError, "Missing mandatory element %s" % tags[0]
    return matching

def getStrAttribute(el, attrs, default = '', mandatory = False):
    matching = []
    for attr in attrs:
        val = el.getAttribute(attr).encode()
        if val != '':
            matching.append(val)
    if len(matching) == 0:
        if mandatory:
            raise XmlUnwrapError, "Missing mandatory attribute %s" % attrs[0]
        return default
    return matching[0]

def getBoolAttribute(el, attrs, default = None):
    mandatory = (default == None)
    val = getStrAttribute(el, attrs, '', mandatory).lower()
    if val == '':
        return default
    return val in ['yes', 'true']

def getIntAttribute(el, attrs, default = None):
    mandatory = (default == None)
    val = getStrAttribute(el, attrs, '', mandatory)
    if val == '':
        return default
    try:
        int_val = int(val, 0)
    except:
        raise XmlUnwrapError, "Invalid integer value for %s" % attrs[0]
    return int_val

def getMapAttribute(el, attrs, mapping, default = None):
    mandatory = (default == None)
    k, v = zip(*mapping)
    key = getStrAttribute(el, attrs, default, mandatory)

    if key not in k:
        raise XmlUnwrapError, "Unexpected key %s for attribute" % key

    k_list = list(k)
    return v[k_list.index(key)]

if __name__ == '__main__':

    a_text = """<installation mode='test'>
    <fred>text1</fred>
    <fred>text2</fred>
    </installation>"""
    xmldoc = xml.dom.minidom.parseString(a_text)
    top_el = xmldoc.documentElement

    print top_el.tagName

    for el in getElementsByTagName(top_el, ["fred"]):
        print getText(el)

    print getMapAttribute(top_el, ["mode"], [('test', 42), ('stuff', 77)])
    print getMapAttribute(top_el, ["made"], [('test', 42), ('stuff', 77)], default = 'stuff')
    
    print getStrAttribute(top_el, ["mode"])
    print getStrAttribute(top_el, ["made"])
    print getStrAttribute(top_el, ["made"], None)
    print getStrAttribute(top_el, ["made"], mandatory = True)
