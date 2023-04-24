# Copyright (c) 2013, Citrix Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""xmlunwrap - general methods to unwrap XML elements & attributes"""

import six

class XmlUnwrapError(Exception):
    pass

def getText(nodelist):
    rc = ""

    for node in nodelist.childNodes:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    if not isinstance(rc, str):  # Python 2 only, otherwise it would return unicode
        rc = rc.encode()
    return rc.strip()

def getElementsByTagName(el, tags, mandatory = False):
    matching = []
    for tag in tags:
        matching.extend(el.getElementsByTagName(tag))
    if mandatory and len(matching) == 0:
        raise XmlUnwrapError("Missing mandatory element %s" % tags[0])
    return matching

def getStrAttribute(el, attrs, default = '', mandatory = False):
    matching = []
    for attr in attrs:
        val = el.getAttribute(attr)
        if not isinstance(val, str):  # Python 2 only, otherwise it would return unicode
            val = val.encode()
        if val != '':
            matching.append(val)
    if len(matching) == 0:
        if mandatory:
            raise XmlUnwrapError("Missing mandatory attribute %s" % attrs[0])
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
    except Exception as e:
        six.raise_from(XmlUnwrapError("Invalid integer value for %s" % attrs[0]), e)
    return int_val

def getMapAttribute(el, attrs, mapping, default = None):
    mandatory = (default == None)
    k, v = zip(*mapping)
    key = getStrAttribute(el, attrs, default, mandatory)

    if key not in k:
        raise XmlUnwrapError("Unexpected key %s for attribute" % key)

    k_list = list(k)
    return v[k_list.index(key)]
