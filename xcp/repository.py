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

from hashlib import md5
import os.path
import xml.dom.minidom
import ConfigParser

import six

import xcp.version as version
import xcp.xmlunwrap as xmlunwrap

class Package(object):          # pylint: disable=too-few-public-methods
    pass

class BzippedPackage(Package):
    def __init__(self, repository, label, size, md5sum, optional, fname, root):
        (
            self.repository,
            self.label,
            self.size,
            self.md5sum,
            self.optional,
            self.filename,
            self.destination
        ) = (repository, label, size, md5sum, optional is True, fname, root)

    def __repr__(self):
        return "<BzippedPackage '%s'>" % self.label

class RPMPackage(Package):
    def __init__(self, repository, label, size, md5sum, optional, fname, options):
        (
            self.repository,
            self.label,
            self.size,
            self.md5sum,
            self.optional,
            self.filename,
            self.options
        ) = (repository, label, size, md5sum, optional is True, fname, options)

    def __repr__(self):
        return "<RPMPackage '%s'>" % self.label

class DriverRPMPackage(RPMPackage):
    def __init__(self, repository, label, size, md5sum, fname, kernel, options):
        (
            self.repository,
            self.label,
            self.size,
            self.md5sum,
            self.filename,
            self.kernel,
            self.options
        ) = (repository, label, size, md5sum, fname, kernel, options)

    def __repr__(self):
        return "<DriverRPMPackage '%s', kernel '%s'>" % (self.label, self.kernel)

class DriverPackage(Package):
    def __init__(self, repository, label, size, md5sum, fname, root):
        (
            self.repository,
            self.label,
            self.size,
            self.md5sum,
            self.filename,
            self.destination
        ) = (repository, label, size, md5sum, fname, root)

    def __repr__(self):
        return "<DriverPackage '%s'>" % self.label

class FirmwarePackage(Package):
    def __init__(self, repository, label, size, md5sum, fname):
        (
            self.repository,
            self.label,
            self.size,
            self.md5sum,
            self.filename
        ) = (repository, label, size, md5sum, fname)

    def __repr__(self):
        return "<FirmwarePackage '%s'>" % self.label

class NoRepository(Exception):
    pass

class RepoFormatError(Exception):
    pass

class BaseRepository(object):
    """ Represents a repository containing packages and associated meta data. """
    def __init__(self, access, base = ""):
        self.access = access
        self.base = base

    @classmethod
    def findRepositories(cls, access):
        repos = YumRepository.findRepositories(access)
        try:
            repos += Repository.findRepositories(access)
        except RepoFormatError:
            pass
        return repos

    @classmethod
    def getRepoVer(cls, access):
        access.start()
        is_yum = YumRepository.isRepo(access, "")
        access.finish()
        
        if is_yum:
            return YumRepository.getRepoVer(access)
        return Repository.getRepoVer(access)

    @classmethod
    def getProductVersion(cls, access):
        access.start()
        is_yum = YumRepository.isRepo(access, "")
        access.finish()

        if is_yum:
            return YumRepository.getProductVersion(access)
        return None

class YumRepository(BaseRepository):
    """ Represents a Yum repository containing packages and associated meta data. """
    REPOMD_FILENAME = "repodata/repomd.xml"
    TREEINFO_FILENAME = ".treeinfo"

    @classmethod
    def findRepositories(cls, access):
        access.start()
        is_repo = cls.isRepo(access, "")
        access.finish()
        if not is_repo:
            return []
        return [ YumRepository(access, "") ]

    def __init__(self, access, base = ""):
        BaseRepository.__init__(self, access, base)

    @classmethod
    def isRepo(cls, access, base):
        """ Return whether there is a repository at base address
        'base' accessible using accessor."""
        return False not in (access.access(os.path.join(base, x))
                             for x in [cls.TREEINFO_FILENAME, cls.REPOMD_FILENAME])

    @classmethod
    def _getVersion(cls, access, category):
        category_map = {'platform': 'platform_version', 'branding': 'product_version'}

        access.start()
        try:
            treeinfofp = access.openAddress(cls.TREEINFO_FILENAME)
            treeinfo = ConfigParser.SafeConfigParser()
            treeinfo.readfp(treeinfofp)
            treeinfofp.close()
            if treeinfo.has_section('system-v1'):
                ver_str = treeinfo.get('system-v1', category_map[category])
            else:
                ver_str = treeinfo.get(category, 'version')
            repo_ver = version.Version.from_string(ver_str)

        except Exception as e:
            six.raise_from(RepoFormatError("Failed to open %s: %s" %
                                           (cls.TREEINFO_FILENAME, str(e))), e)
        access.finish()
        return repo_ver

    @classmethod
    def getRepoVer(cls, access):
        """Returns the platform version of the repository."""

        return cls._getVersion(access, 'platform')

    @classmethod
    def getProductVersion(cls, access):
        """Returns the product version of the repository."""

        return cls._getVersion(access, 'branding')

class Repository(BaseRepository):
    """ Represents a XenSource repository containing packages and associated
    meta data. """
    REPOSITORY_FILENAME = "XS-REPOSITORY"
    PKGDATA_FILENAME = "XS-PACKAGES"
    REPOLIST_FILENAME = "XS-REPOSITORY-LIST"

    XCP_MAIN_IDENT = "xcp:main"
    XS_MAIN_IDENT = "xs:main"

    OPER_MAP = {'eq': ' = ', 'ne': ' != ', 'lt': ' < ', 'gt': ' > ', 'le': ' <= ', 'ge': ' >= '}

    @classmethod
    def findRepositories(cls, access):
        # Check known locations:
        package_list = ['', 'packages', 'packages.main', 'packages.linux',
                        'packages.site']
        repos = []

        access.start()
        try:
            extra = access.openAddress(cls.REPOLIST_FILENAME)
            if extra:
                for line in extra:
                    package_list.append(line.strip())
                extra.close()
        except Exception as e:
            six.raise_from(RepoFormatError("Failed to open %s: %s" %
                                           (cls.REPOLIST_FILENAME, str(e))), e)

        for loc in package_list:
            if cls.isRepo(access, loc):
                repos.append(Repository(access, loc))
        access.finish()
        return repos

    def __init__(self, access, base, is_group = False):
        BaseRepository.__init__(self, access, base)
        self.is_group = is_group
        self._md5 = md5()
        self.requires = []
        self.packages = []

        access.start()

        try:
            repofile = access.openAddress(os.path.join(base, self.REPOSITORY_FILENAME))
        except Exception as e:
            access.finish()
            six.raise_from(NoRepository(), e)
        self._parse_repofile(repofile)
        repofile.close()

        try:
            pkgfile = access.openAddress(os.path.join(base, self.PKGDATA_FILENAME))
        except Exception as e:
            access.finish()
            six.raise_from(NoRepository(), e)
        self._parse_packages(pkgfile)
        pkgfile.close()

        access.finish()

    def __repr__(self):
        return "<Repository '%s', version '%s'>" % (self.identifier, self.product_version)

    def __str__(self):
        out = "Repository '%s', version '%s'" % (self.identifier, self.product_version)
        if len(self.requires) > 0:
            out += ", Requires: %s" % str(self.requires)
        if len(self.packages) > 0:
            out += ", Packages: %s" % str(self.packages)
        return out

    def _parse_repofile(self, repofile):
        """ Parse repository data -- get repository identifier and name. """

        repofile_contents = repofile.read()
        repofile.close()

        # update md5sum for repo
        self._md5.update(repofile_contents)

        # build xml doc object
        try:
            xmldoc = xml.dom.minidom.parseString(repofile_contents)
        except Exception as e:
            six.raise_from(RepoFormatError("%s not in XML" % self.REPOSITORY_FILENAME), e)

        try:
            repo_node = xmlunwrap.getElementsByTagName(xmldoc, ['repository'], mandatory = True)

            attrs = ('originator', 'name', 'product', 'version', 'build')
            optional_attrs = ('build')

            for attr in attrs:
                self.__dict__[attr] = xmlunwrap.getStrAttribute(repo_node[0], [attr], default = None,
                                                                mandatory = (attr not in optional_attrs))

            desc_node = xmlunwrap.getElementsByTagName(xmldoc, ['description'], mandatory = True)
            self.description = xmlunwrap.getText(desc_node[0])

            for req_node in xmlunwrap.getElementsByTagName(xmldoc, ['requires']):
                req = {}
                for attr in ['originator', 'name', 'test', 'version', 'build']:
                    req[attr] = xmlunwrap.getStrAttribute(req_node, [attr])
                if req['build'] == '':
                    del req['build']
                assert req['test'] in self.OPER_MAP
                self.requires.append(req)
        except Exception as e:
            six.raise_from(RepoFormatError("%s format error" % self.REPOSITORY_FILENAME), e)

        self.identifier = "%s:%s" % (self.originator, self.name)
        ver_str = self.version
        if self.build:
            ver_str += '-'+self.build
        self.product_version = version.Version.from_string(ver_str)

    def _parse_packages(self, pkgfile):
        pkgfile_contents = pkgfile.read()
        pkgfile.close()

        # update md5sum for repo
        self._md5.update(pkgfile_contents)

        # build xml doc object
        try:
            xmldoc = xml.dom.minidom.parseString(pkgfile_contents)
        except Exception as e:
            six.raise_from(RepoFormatError("%s not in XML" % self.PKGDATA_FILENAME), e)

        for pkg_node in xmlunwrap.getElementsByTagName(xmldoc, ['package']):
            pkg = self._create_package(pkg_node)
            self.packages.append(pkg)

    constructor_map = {
        'tbz2': [ BzippedPackage, ( 'label', 'size', 'md5', 'optional', 'fname', 'root' ) ],
        'rpm': [ RPMPackage, ( 'label', 'size', 'md5', 'optional', 'fname', 'options' ) ],
        'driver-rpm': [ DriverRPMPackage, ( 'label', 'size', 'md5', 'fname', 'kernel', 'options' ) ],
        # obsolete
        'driver': [ DriverPackage, ( 'label', 'size', 'md5', 'fname', 'root' ) ],
        'firmware': [ FirmwarePackage, ('label', 'size', 'md5', 'fname') ]
        }

    optional_attrs = ['optional', 'options']

    def _create_package(self, node):
        args = [ self ]
        ptype = xmlunwrap.getStrAttribute(node, ['type'], mandatory = True)
        for attr in self.constructor_map[ptype][1]:
            if attr == 'fname':
                args.append(xmlunwrap.getText(node))
            else:
                args.append(xmlunwrap.getStrAttribute(node, [attr], mandatory = attr not in self.optional_attrs))
        return self.constructor_map[ptype][0](*args)

    @classmethod
    def isRepo(cls, access, base):
        """ Return whether there is a repository at base address
        'base' accessible using accessor."""
        return False not in (access.access(os.path.join(base, x))
                             for x in [cls.REPOSITORY_FILENAME, cls.PKGDATA_FILENAME])

    @classmethod
    def getRepoVer(cls, access):
        repo_ver = None

        try:
            repos = cls.findRepositories(access)
            for r in repos:
                if r.identifier == cls.XCP_MAIN_IDENT:
                    repo_ver = r.product_version
                    break
        except:
            pass

        return repo_ver
