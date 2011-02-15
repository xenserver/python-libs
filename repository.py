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

import os.path

import xcl.accessor as accessor

class Repository:
    REPOSITORY_FILENAME = "XS-REPOSITORY"
    PKGDATA_FILENAME = "XS-PACKAGES"
    REPOLIST_FILENAME = "XS-REPOSITORY-LIST"

    def __init__(self, accessor, base):
        (
            self.accessor,
            self.base
        ) = (accessor, base)

    @classmethod
    def isRepo(cls, accessor, base):
        """ Return whether there is a repository at base address 'base' accessible
        using accessor."""
        return False not in map(lambda x: accessor.access(os.path.join(base, x)), [cls.REPOSITORY_FILENAME, cls.PKGDATA_FILENAME])

    @classmethod
    def findRepositories(cls, accessor):
        # Check known locations:
        repo_dirs = ['', 'packages', 'packages.main', 'packages.linux',
                        'packages.site']
        repos = []

        accessor.start()
        # extend if repo list is present
        try:
            extra = accessor.openAddress(cls.REPOLIST_FILENAME)
            if extra:
                repo_dirs.extend(map(lambda x: x.strip(), extra))
                extra.close()
        except:
            pass
            
        for repo_dir in repo_dirs:
            if cls.isRepo(accessor, repo_dir):
                repos.append(cls(accessor, repo_dir))
        accessor.finish()

        return repos
