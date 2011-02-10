#!/usr/bin/env python
# Copyright (c) 2011 Citrix Systems, Inc. All use and distribution of this
# copyrighted material is governed by and subject to terms and conditions
# as licensed by Citrix Systems, Inc. All other rights reserved.
# Xen, XenSource and XenEnterprise are either registered trademarks or
# trademarks of Citrix Systems, Inc. in the United States and/or other 
# countries.

import os.path

import accessor

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
