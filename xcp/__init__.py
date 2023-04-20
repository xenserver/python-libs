#!/usr/bin/env python

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

import sys

# Introduction on making the popen() calls compatible with Python3:
# =================================================================
#
# The xcp-python library uses popen() at nine occasions and in contrast
# to open() which has io.open(file, encoding="utf-8", errors="replace"),
# for compatible support for both Python2 and Python3, there does not
# appear to be a similar common function for subprocess.Popen*() which
# has these characteristics:
#
# Python2:
# --------
# On Python2, "str" is the same as bytes. Thus, there is no conversion,
# and no issue. It just passes data in and out unmodified.
#
# Python3:
# --------
# Unless enabled by extra arguments, Popen() operates in binary mode.
# In binary mode, it expects bytes for stdin, and returns bytes from stdout and stderr.
#
# Thus, bytes need to be converted to strings at some point:
#
# The simplest way to do this is to let Popen() do the encoding and decoding
# of stdin, stdout and stderr. It does this when text mode is enabled using
# the encoding parameter. Since XCP uses LANG=en_US.UTF-8, encoding="utf-8".
#
# Also, when input or output bytes to/from the Pipes are malformed, this needs
# to be handled. Instead of terminating the program by raising UnicodeDecodeError
# or removing malformed bytes during conversion, replace them with question marks.
#

#
# popen_utf8_text_kwargs is used as **xcp.popen_utf8_text_kwargs in the lib and tests
# as well as for mocking of the calls and verification of the expected calls.
# In total, it has to be used 9 times x 3 occurences, so 27 times in total.#
#
# For more information on Unicode handling and codec errors see:
# https://www.honeybadger.io/blog/python-character-encoding/
# https://johnlekberg.com/blog/2020-04-03-codec-errors.html
#
if sys.version_info.major > 2:
    xcp_popen_text_kwargs = {"encoding": "utf-8", "errors": "replace"}
else:
    xcp_popen_text_kwargs = {}

# This can then be used like this: Popen(exe, ..., **xcp.open_utf8_test_kwargs)