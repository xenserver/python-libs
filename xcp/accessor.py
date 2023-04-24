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

"""accessor - provide common interface to access methods"""

# pylint: disable=wrong-import-position,wrong-import-order
from future import standard_library
standard_library.install_aliases()

import ftplib
import os
import tempfile
import urllib.request           # pylint: disable=import-error
import urllib.error             # pylint: disable=import-error
import urllib.parse             # pylint: disable=import-error
import errno

import xcp.mount as mount
import xcp.logger as logger

# maps errno codes to HTTP error codes
# needed for error code consistency
def mapError(errorCode):
    if errorCode == errno.EPERM:
        return 401
    elif errorCode == errno.ENOENT:
        return 404
    elif errorCode == errno.EACCES:
        return 403
    else:
        return 500

class Accessor(object):

    def __init__(self, ro):
        self.read_only = ro
        self.lastError = 0

    def access(self, name):
        """ Return boolean determining where 'name' is an accessible object
        in the target. """
        try:
            f = self.openAddress(name)
            if not f:
                return False
            f.close()
        except Exception as e:
            return False

        return True

    def openAddress(self, address):
        """should be overloaded"""
        pass

    def canEject(self):
        return False

    def start(self):
        pass

    def finish(self):
        pass

    @staticmethod
    def _writeFile(in_fh, out_fh):
        while out_fh:
            data = in_fh.read(256 * 512)
            if len(data) == 0:
                break
            out_fh.write(data)
        out_fh.close()
        return True

class FilesystemAccessor(Accessor):
    def __init__(self, location, ro):
        super(FilesystemAccessor, self).__init__(ro)
        self.location = location

    def openAddress(self, address):
        try:
            filehandle = open(os.path.join(self.location, address), 'rb')
        except OSError as e:
            if e.errno == errno.EIO:
                self.lastError = 5
            else:
                self.lastError = mapError(e.errno)
            return False
        except IOError as e:
            if e.errno == errno.EIO:
                self.lastError = 5
            else:
                self.lastError = mapError(e.errno)
            return False
        except Exception as e:
            self.lastError = 500
            return False
        return filehandle

class MountingAccessor(FilesystemAccessor):
    def __init__(self, mount_types, mount_source, mount_options=None):
        ro = isinstance(mount_options, list) and 'ro' in mount_options
        super(MountingAccessor, self).__init__(None, ro)

        self.mount_types = mount_types
        self.mount_source = mount_source
        self.mount_options = mount_options
        self.start_count = 0

    def start(self):
        if self.start_count == 0:
            self.location = tempfile.mkdtemp(prefix="media-", dir="/tmp")
            # try each filesystem in turn:
            success = False
            for fs in self.mount_types:
                try:
                    opts = self.mount_options
                    if fs == 'iso9660':
                        if isinstance(opts, list):
                            if 'ro' not in opts:
                                opts.append('ro')
                        else:
                            opts = ['ro']
                    mount.mount(self.mount_source, self.location,
                                options = opts,
                                fstype = fs)
                except mount.MountException:
                    continue
                else:
                    success = True
                    break
            if not success:
                os.rmdir(self.location)
                raise mount.MountException
        self.start_count += 1

    def finish(self):
        if self.start_count == 0:
            return
        self.start_count -= 1
        if self.start_count == 0:
            mount.umount(self.location)
            os.rmdir(self.location)
            self.location = None

    def writeFile(self, in_fh, out_name):
        logger.info("Copying to %s" % os.path.join(self.location, out_name))
        out_fh = open(os.path.join(self.location, out_name), "wb")
        return self._writeFile(in_fh, out_fh)

    def __del__(self):
        while self.start_count > 0:
            self.finish()

class DeviceAccessor(MountingAccessor):
    def __init__(self, device, ro, fs = None):
        """ Return a MountingAccessor for a device 'device', which should
        be a fully qualified path to a device node. """
        if device.startswith('dev://'):
            device = device[6:]
        if fs is None:
            fs = ['iso9660', 'vfat', 'ext3']
        opts = None
        if ro:
            opts = ['ro']
        super(DeviceAccessor, self).__init__(fs, device, opts)
        self.device = device

    def __repr__(self):
        return "<DeviceAccessor: %s>" % self.device

#    def canEject(self):
#        return diskutil.removable(self.device):

#    def eject(self):
#        assert self.canEject()
#        self.finish()
#        util.runCmd2(['/usr/bin/eject', self.device])

class NFSAccessor(MountingAccessor):
    def __init__(self, nfspath, ro):
        if nfspath.startswith('nfs://'):
            nfspath = nfspath[6:]
        opts = ['tcp,timeo=100,retrans=1,retry=0']
        if ro:
            opts.append('ro')
        super(NFSAccessor, self).__init__(['nfs'], nfspath, opts)
        self.nfspath = nfspath

    def __repr__(self):
        return "<NFSAccessor: %s>" % self.nfspath

class FileAccessor(Accessor):
    def __init__(self, baseAddress, ro):
        if baseAddress.startswith('file://'):
            baseAddress = baseAddress[7:]
        assert baseAddress.endswith('/')
        super(FileAccessor, self).__init__(ro)
        self.baseAddress = baseAddress

    def openAddress(self, address):
        try:
            file = open(os.path.join(self.baseAddress, address), "rb")
        except IOError as e:
            if e.errno == errno.EIO:
                self.lastError = 5
            else:
                self.lastError = mapError(e.errno)
            return False
        except OSError as e:
            if e.errno == errno.EIO:
                self.lastError = 5
            else:
                self.lastError = mapError(e.errno)
            return False
        except Exception as e:
            self.lastError = 500
            return False
        return file

    def writeFile(self, in_fh, out_name):
        logger.info("Copying to %s" % os.path.join(self.baseAddress, out_name))
        out_fh = open(os.path.join(self.baseAddress, out_name), "wb" )
        return self._writeFile(in_fh, out_fh)

    def __repr__(self):
        return "<FileAccessor: %s>" % self.baseAddress

def rebuild_url(url_parts):
    '''Rebuild URL without auth components'''

    host = url_parts.hostname
    if url_parts.port:
        host += ':' + str(url_parts.port)
    return urllib.parse.urlunsplit(
        (url_parts.scheme, host,
         url_parts.path, '', ''))

class FTPAccessor(Accessor):
    def __init__(self, baseAddress, ro):
        super(FTPAccessor, self).__init__(ro)
        self.url_parts = urllib.parse.urlsplit(baseAddress, allow_fragments=False)
        self.start_count = 0
        self.cleanup = False
        self.ftp = None
        self.baseAddress = rebuild_url(self.url_parts)

    def _cleanup(self):
        if self.cleanup:
            # clean up after RETR
            self.ftp.voidresp()
            self.cleanup = False

    def start(self):
        if self.start_count == 0:
            self.ftp = ftplib.FTP()
            #self.ftp.set_debuglevel(1)
            port = ftplib.FTP_PORT
            if self.url_parts.port:
                port = self.url_parts.port
            self.ftp.connect(self.url_parts.hostname, port)
            username = self.url_parts.username
            password = self.url_parts.password
            if username:
                username = urllib.parse.unquote(username)
            if password:
                password = urllib.parse.unquote(password)
            self.ftp.login(username, password)

            directory = urllib.parse.unquote(self.url_parts.path[1:])
            if directory != '':
                logger.debug("Changing to " + directory)
                self.ftp.cwd(directory)

        self.start_count += 1

    def finish(self):
        if self.start_count == 0:
            return
        self.start_count -= 1
        if self.start_count == 0:
            self.ftp.quit()
            self.cleanup = False
            self.ftp = None

    def access(self, path):
        try:
            logger.debug("Testing "+path)
            self._cleanup()
            url = urllib.parse.unquote(path)

            if self.ftp.size(url) is not None:
                return True
            lst = self.ftp.nlst(os.path.dirname(url))
            return os.path.basename(url) in list(map(os.path.basename, lst))
        except IOError as e:
            if e.errno == errno.EIO:
                self.lastError = 5
            else:
                self.lastError = mapError(e.errno)
            return False
        except OSError as e:
            if e.errno == errno.EIO:
                self.lastError = 5
            else:
                self.lastError = mapError(e.errno)
            return False
        except Exception as e:
            self.lastError = 500
            return False

    def openAddress(self, address):
        logger.debug("Opening "+address)
        self._cleanup()
        url = urllib.parse.unquote(address)

        self.ftp.voidcmd('TYPE I')
        s = self.ftp.transfercmd('RETR ' + url).makefile('rb')
        self.cleanup = True
        return s

    def writeFile(self, in_fh, out_name):
        self._cleanup()
        fname = urllib.parse.unquote(out_name)

        logger.debug("Storing as " + fname)
        self.ftp.storbinary('STOR ' + fname, in_fh)

    def __repr__(self):
        return "<FTPAccessor: %s>" % self.baseAddress

class HTTPAccessor(Accessor):
    def __init__(self, baseAddress, ro):
        assert ro
        super(HTTPAccessor, self).__init__(ro)
        self.url_parts = urllib.parse.urlsplit(baseAddress, allow_fragments=False)

        if self.url_parts.username:
            username = self.url_parts.username
            if username is not None:
                username = urllib.parse.unquote(self.url_parts.username)
            password = self.url_parts.password
            if password is not None:
                password = urllib.parse.unquote(self.url_parts.password)
            self.passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            self.passman.add_password(None, self.url_parts.hostname,
                                      username, password)
            self.authhandler = urllib.request.HTTPBasicAuthHandler(self.passman)
            self.opener = urllib.request.build_opener(self.authhandler)
            urllib.request.install_opener(self.opener)

        self.baseAddress = rebuild_url(self.url_parts)

    def openAddress(self, address):
        try:
            urlFile = urllib.request.urlopen(os.path.join(self.baseAddress, address))
        except urllib.error.HTTPError as e:
            self.lastError = e.code
            return False
        return urlFile

    def __repr__(self):
        return "<HTTPAccessor: %s>" % self.baseAddress

SUPPORTED_ACCESSORS = {'nfs': NFSAccessor,
                       'http': HTTPAccessor,
                       'https': HTTPAccessor,
                       'ftp': FTPAccessor,
                       'file': FileAccessor,
                       'dev': DeviceAccessor,
                       }

def createAccessor(baseAddress, *args):
    url_parts = urllib.parse.urlsplit(baseAddress, allow_fragments=False)

    assert url_parts.scheme in SUPPORTED_ACCESSORS
    return SUPPORTED_ACCESSORS[url_parts.scheme](baseAddress, *args)
