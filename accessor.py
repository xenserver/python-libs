#!/usr/bin/env python
# Copyright (c) 2011 Citrix Systems, Inc. All use and distribution of this
# copyrighted material is governed by and subject to terms and conditions
# as licensed by Citrix Systems, Inc. All other rights reserved.
# Xen, XenSource and XenEnterprise are either registered trademarks or
# trademarks of Citrix Systems, Inc. in the United States and/or other 
# countries.

import ftplib
import os
import tempfile
import urllib
import urllib2
import urlparse

import mount

class SplitResult:
    def __init__(self, args):
        (
            self.scheme,
            self.netloc,
            self.path,
            _,
            __
        ) = args

    @property
    def username(self):
        netloc = self.netloc
        if "@" in netloc:
            userinfo = netloc.rsplit("@", 1)[0]
            if ":" in userinfo:
                userinfo = userinfo.split(":", 1)[0]
            return userinfo
        return None

    @property
    def password(self):
        netloc = self.netloc
        if "@" in netloc:
            userinfo = netloc.rsplit("@", 1)[0]
            if ":" in userinfo:
                return userinfo.split(":", 1)[1]
        return None

    @property
    def hostname(self):
        netloc = self.netloc
        if "@" in netloc:
            netloc = netloc.rsplit("@", 1)[1]
        if ":" in netloc:
            netloc = netloc.split(":", 1)[0]
        return netloc.lower() or None

def compat_urlsplit(url, allow_fragments = True):
    ret = urlparse.urlsplit(url, allow_fragments)
    if 'SplitResult' in dir(urlparse):
        return ret
    return SplitResult(ret)

class Accessor:
    def access(self, name):
        """ Return boolean determining where 'name' is an accessible object
        in the target. """
        try:
            f = self.openAddress(name)
            f.close()
        except:
            return False

        return True

    def canEject(self):
        return False

    def start(self):
        pass

    def finish(self):
        pass
    
class FilesystemAccessor(Accessor):
    def __init__(self, location):
        self.location = location

    def openAddress(self, addr):
        return open(os.path.join(self.location, addr), 'r')

class MountingAccessor(FilesystemAccessor):
    def __init__(self, mount_types, mount_source, mount_options = ['ro']):
        (
            self.mount_types,
            self.mount_source,
            self.mount_options
        ) = (mount_types, mount_source, mount_options)
        self.start_count = 0
        self.location = None

    def start(self):
        if self.start_count == 0:
            self.location = tempfile.mkdtemp(prefix="media-", dir="/tmp")
            # try each filesystem in turn:
            success = False
            for fs in self.mount_types:
                try:
                    mount.mount(self.mount_source, self.location,
                                options = self.mount_options,
                                fstype = fs)
                except mount.MountException, e:
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

    def __del__(self):
        while self.start_count > 0:
            self.finish()

class DeviceAccessor(MountingAccessor):
    def __init__(self, device, fs = ['iso9660', 'vfat', 'ext3']):
        """ Return a MountingAccessor for a device 'device', which should
        be a fully qualified path to a device node. """
        MountingAccessor.__init__(self, fs, device)
        self.device = device

    def __repr__(self):
        return "<DeviceAccessor: %s>" % self.device

#    def canEject(self):
#        if diskutil.removable(self.device):
#            return True

#    def eject(self):
#        assert self.canEject()
#        self.finish()
#        util.runCmd2(['/usr/bin/eject', self.device])

class NFSAccessor(MountingAccessor):
    def __init__(self, nfspath):
        if nfspath.startswith('nfs://'):
            nfspath = nfspath[:6]
        MountingAccessor.__init__(self, ['nfs'], nfspath, ['ro', 'tcp'])

    def __repr__(self):
        return "<NFSAccessor: %s>" % self.nfspath

class URLAccessor(Accessor):
    url_prefixes = ['http', 'https', 'ftp', 'file']

    def __init__(self, baseAddress):
        assert baseAddress.endswith('/')
        self.url_parts = compat_urlsplit(baseAddress, allow_fragments = False)
        assert self.url_parts.scheme in self.url_prefixes

        if self.url_parts.scheme.startswith('http') and self.url_parts.username:
            self.passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
            print self.url_parts.hostname, self.url_parts.username, self.url_parts.password
            self.passman.add_password(None, self.url_parts.hostname,
                                      self.url_parts.username, self.url_parts.password)
            self.authhandler = urllib2.HTTPBasicAuthHandler(self.passman)
            self.opener = urllib2.build_opener(self.authhandler)
            urllib2.install_opener(self.opener)
        # rebuild URL without auth components & escape special chars in path
        self.baseAddress = urlparse.urlunsplit((self.url_parts.scheme,
                                                self.url_parts.hostname,
                                                urllib.quote(self.url_parts.path), '', ''))

    def access(self, path):
        if self.url_parts.scheme != 'ftp':
            return Accessor.access(self, path)

        url = os.path.join(self.url_parts.path, path)[1:]

        # if FTP, override by actually checking the file exists because urllib2 seems
        # to be not so good at this.
        try:
            directory, fname = os.path.split(url)

            # now open a connection to the server and verify that fname is in 
            ftp = ftplib.FTP(self.url_parts.hostname)
            ftp.login(self.url_parts.username, self.url_parts.password)
            if directory != '':
                ftp.cwd(directory)
            lst = ftp.nlst()
            return fname in lst
        except:
            return False

    def openAddress(self, address):
        return urllib2.urlopen(os.path.join(self.baseAddress, address))

    def __repr__(self):
        return "<URLAccessor: %s>" % self.baseAddress

supported_accessors = {'nfs': NFSAccessor,
                       'http': URLAccessor,
                       'https': URLAccessor,
                       'ftp': URLAccessor,
                       'file': URLAccessor}

def createAccessor(baseAddress):
    url_parts = compat_urlsplit(baseAddress, allow_fragments = False)

    assert url_parts.scheme in supported_accessors.keys()
    return supported_accessors[url_parts.scheme](baseAddress)
