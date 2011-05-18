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

import md5
import os.path
import xml.dom.minidom

import xcp.version as version
import xcp.xmlunwrap as xmlunwrap

class NoRepository(Exception):
    pass

class RepoFormatError(Exception):
    pass

class Repository(object):
    REPOSITORY_FILENAME = "XS-REPOSITORY"
    PKGDATA_FILENAME = "XS-PACKAGES"
    REPOLIST_FILENAME = "XS-REPOSITORY-LIST"

    XS_MAIN_IDENT = "xs:main"

    OPER_MAP = {'eq': ' = ', 'ne': ' != ', 'lt': ' < ', 'gt': ' > ', 'le': ' <= ', 'ge': ' >= '}

    def __init__(self, access, base):
        (
            self.accessor,
            self.base
        ) = (access, base)
        self._md5 = md5.new()
        self.requires = []

        access.start()

        try:
            repofile = access.openAddress(os.path.join(base, self.REPOSITORY_FILENAME))
        except Exception, e:
            access.finish()
            raise NoRepository, e
        self._parse_repofile(repofile)
        repofile.close()

        access.finish()

    def __repr__(self):
        return "<Repository '%s', version '%s'>" % (self.identifier, self.product_version)

    def _parse_repofile(self, repofile):
        """ Parse repository data -- get repository identifier and name. """
        
        repofile_contents = repofile.read()
        repofile.close()

        # update md5sum for repo
        self._md5.update(repofile_contents)

        # build xml doc object
        try:
            xmldoc = xml.dom.minidom.parseString(repofile_contents)
        except:
            raise RepoFormatError, "%s not in XML" % self.REPOSITORY_FILENAME

        try:
            repo_node = xmlunwrap.getElementsByTagName(xmldoc, ['repository'], mandatory = True)
            desc_node = xmlunwrap.getElementsByTagName(xmldoc, ['description'], mandatory = True)
            originator = xmlunwrap.getStrAttribute(repo_node[0], ['originator'], mandatory = True)
            name = xmlunwrap.getStrAttribute(repo_node[0], ['name'], mandatory = True)
            product = xmlunwrap.getStrAttribute(repo_node[0], ['product'], mandatory = True)
            version_s = xmlunwrap.getStrAttribute(repo_node[0], ['version'], mandatory = True)
            build = xmlunwrap.getStrAttribute(repo_node[0], ['build'], None)
            description = xmlunwrap.getText(desc_node[0])

            for req_node in xmlunwrap.getElementsByTagName(xmldoc, ['requires']):
                req = {}
                for attr in ['originator', 'name', 'test', 'version', 'build']:
                    req[attr] = xmlunwrap.getStrAttribute(req_node, [attr])
                if req['build'] == '':
                    del req['build']
                assert req['test'] in self.OPER_MAP
                self.requires.append(req)
        except:
            raise RepoFormatError, "%s format error" % self.REPOSITORY_FILENAME

        self.identifier = "%s:%s" % (originator, name)
        self.name = description
        self.product_brand = product
        ver_str = version_s
        if build:
            ver_str += '-'+build
        self.product_version = version.Version.from_string(ver_str)

    @classmethod
    def isRepo(cls, access, base):
        """ Return whether there is a repository at base address
        'base' accessible using accessor."""
        return False not in map(lambda x: access.access(os.path.join(base, x)),
                                [cls.REPOSITORY_FILENAME, cls.PKGDATA_FILENAME])

    @classmethod
    def findRepositories(cls, access):
        # Check known locations:
        repo_dirs = ['', 'packages', 'packages.main', 'packages.linux',
                        'packages.site']
        repos = []

        access.start()
        # extend if repo list is present
        try:
            extra = access.openAddress(cls.REPOLIST_FILENAME)
            if extra:
                repo_dirs.extend(map(lambda x: x.strip(), extra))
                extra.close()
        except Exception:
            pass
            
        for repo_dir in repo_dirs:
            if cls.isRepo(access, repo_dir):
                repos.append(cls(access, repo_dir))
        access.finish()

        return repos
