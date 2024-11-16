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

import errno
import ftplib
import io
import os
import sys
import tempfile
from contextlib import contextmanager
from typing import TYPE_CHECKING, Union, cast

from six.moves import urllib  # pyright: ignore

from xcp import logger, mount

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import IO, List, Tuple

    from typing_extensions import Literal

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
            f.close()  # pylint: disable=no-member
        except Exception:
            return False

        return True

    @contextmanager
    def openText(self, address):
        # type:(str) -> Generator[IO[str] | Literal[False], None, None]
        """Context manager to read text from address using 'with'. Yields IO[str] or False"""
        readbuffer = self.openAddress(address)

        if readbuffer and sys.version_info >= (3, 0):
            textiowrapper = io.TextIOWrapper(readbuffer, encoding="utf-8")
            yield textiowrapper
            textiowrapper.close()
        else:
            yield cast(io.TextIOWrapper, readbuffer)

        if readbuffer:
            readbuffer.close()

    def openAddress(self, address):
        # type:(str) -> IO[bytes] | Literal[False]
        """must be overloaded"""
        return False  # pragma: no cover

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
            filehandle = open(os.path.join(self.location, address), "rb")
        except (IOError, OSError) as e:
            if e.errno == errno.EIO:
                self.lastError = 5
            else:
                self.lastError = mapError(e.errno)
            return False
        except Exception:
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
            assert self.location
            mount.umount(self.location)
            os.rmdir(self.location)
            self.location = None

    def writeFile(self, in_fh, out_name):
        assert self.location
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
            reader = open(os.path.join(self.baseAddress, address), "rb")
        except (IOError, OSError) as e:
            if e.errno == errno.EIO:
                self.lastError = 5
            else:
                self.lastError = mapError(e.errno)
            return False
        except Exception:
            self.lastError = 500
            return False
        return reader

    def writeFile(self, in_fh, out_name):
        logger.info("Copying to %s" % os.path.join(self.baseAddress, out_name))
        out_fh = open(os.path.join(self.baseAddress, out_name), "wb")
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
            cast(ftplib.FTP, self.ftp).voidresp()
            self.cleanup = False

    def start(self):
        if self.start_count == 0:
            self.ftp = ftplib.FTP()
            #self.ftp.set_debuglevel(1)
            port = ftplib.FTP_PORT
            if self.url_parts.port:
                port = self.url_parts.port
            self.ftp.connect(cast(str, self.url_parts.hostname), port)
            username = cast(str, self.url_parts.username)
            password = cast(str, self.url_parts.password)
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
            cast(ftplib.FTP, self.ftp).quit()
            self.cleanup = False
            self.ftp = None

    # pylint: disable-next=arguments-differ,arguments-renamed
    def access(self, path):  # pyright: ignore[reportIncompatibleMethodOverride]
        try:
            logger.debug("Testing "+path)
            self._cleanup()
            url = urllib.parse.unquote(path)

            assert self.ftp
            if self.ftp.size(url) is not None:
                return True
            lst = self.ftp.nlst(os.path.dirname(url))
            return os.path.basename(url) in list(map(os.path.basename, lst))
        except (IOError, OSError) as e:
            if e.errno == errno.EIO:
                self.lastError = 5
            else:
                self.lastError = mapError(e.errno)
            return False
        except Exception:
            self.lastError = 500
            return False

    def openAddress(self, address):
        logger.debug("Opening "+address)
        self._cleanup()
        url = urllib.parse.unquote(address)

        assert self.ftp
        self.ftp.voidcmd('TYPE I')
        socket = self.ftp.transfercmd('RETR ' + url)
        buffered_reader = socket.makefile('rb')
        # See https://github.com/xenserver/python-libs/pull/49#discussion_r1212794936:
        socket.close()
        self.cleanup = True
        return buffered_reader

    def writeFile(self, in_fh, out_name):
        self._cleanup()
        fname = urllib.parse.unquote(out_name)

        logger.debug("Storing as " + fname)
        cast(ftplib.FTP, self.ftp).storbinary('STOR ' + fname, in_fh)

    def __repr__(self):
        return "<FTPAccessor: %s>" % self.baseAddress

class HTTPAccessor(Accessor):
    def __init__(self, baseAddress, ro):
        assert ro
        super(HTTPAccessor, self).__init__(ro)
        self.url_parts = urllib.parse.urlsplit(baseAddress, allow_fragments=False)

        assert self.url_parts.hostname
        if self.url_parts.username:
            username = self.url_parts.username
            if username is not None:
                username = urllib.parse.unquote(self.url_parts.username)
            password = self.url_parts.password
            if password is not None:
                password = urllib.parse.unquote(password)
            self.passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            self.passman.add_password(None, self.url_parts.hostname,
                                      username, password or "")
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


# Tuple passed in tests to isinstance(val, ...Types) to check types:
MountingAccessorTypes = (DeviceAccessor, NFSAccessor)
"""Tuple for type checking in unit tests testing subclasses of MountingAccessor"""

# Tuple passed in tests to isinstance(val, ...Types) to check types:
LocalTypes = (DeviceAccessor, NFSAccessor, FileAccessor)


Mount = Union[DeviceAccessor, NFSAccessor]
"""Type alias for static typing or unit tests testing subclasses of MountingAccessor"""

AnyAccessor = Union[
    HTTPAccessor,
    FTPAccessor,
    FileAccessor,
    Mount,
]
"""Type alias for static typing the Accessor object returned by createAccessor()"""

SUPPORTED_ACCESSORS = {
    "nfs": NFSAccessor,
    "http": HTTPAccessor,
    "https": HTTPAccessor,
    "ftp": FTPAccessor,
    "file": FileAccessor,
    "dev": DeviceAccessor,
}  # type: dict[str, type[AnyAccessor]]
"""Dict of supported accessors. The key is the URL scheme"""

def createAccessor(baseAddress, *args):
    # type: (str, bool | Tuple[bool, List[str]]) -> Literal[False] | AnyAccessor
    """
    Return instance of the appropriate Accessor subclass based on the baseAddress.

    :param baseAddress (str): The base address for the accessor.
    :param args (tuple): Additional argument(s) to be passed to the accessor constructor
    :returns Accessor (object | Literal[False]): Accessor object or Literal[False]
    :raises AssertionError: If the scheme of the baseAddress is not supported.

    Also raises AssertionError when baseAddress is file:///filename/
    but the final / is omitted. The final terminating / is compulsory.

    For all Accessors, the 1st arg after the address is type bool for ro (readonly flag)
    The DeviceAccessor accepts a 3rd argument: a List[] of filesystem names

    Examples:
        accessor = createAccessor("http://example.com", True)
        accessor = createAccessor("dev://example.com", True, ['iso9660', 'ext3'])
        if not accessor:
            fatal()
        else:
            accessor.read()
    """
    url_parts = urllib.parse.urlsplit(baseAddress, allow_fragments=False)

    assert url_parts.scheme in SUPPORTED_ACCESSORS
    return SUPPORTED_ACCESSORS[url_parts.scheme](baseAddress, *args)
