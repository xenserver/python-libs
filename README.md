# Common XenServer/XCP-ng Python classes

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![](https://img.shields.io/badge/python-2.7_%7C_3.6_%7C_3.7_%7C_3.8_%7C_3.9_%7C_3.10_%7C_3.11+-blue.svg)](https://www.python.org/downloads/)
[![codecov](https://codecov.io/gh/xenserver/python-libs/branch/master/graph/badge.svg?token=6WKVLDXJFN)](https://codecov.io/gh/xenserver/python-libs)
[![](https://img.shields.io/badge/License-BSD--2--Cause%20%26%20MIT-brightgreen)](https://github.com/xenserver/python-libs/blob/master/LICENSE)

The `xcp` directory contains the Common XenServer and XCP-ng Python packages.
They are intented for use in XenServer and XCP-ng Dom0 only and deal with logging,
Hardware/PCI, networking, and other Dom0 tasks.

The package name is `python-libs` which is also the `rpm` package name in XenServer.
XCP-ng packages it as [xcp-python-libs](https://github.com/xcp-ng-rpms/xcp-python-libs)
([koji](https://koji.xcp-ng.org/packageinfo?packageID=400)).

It supports Python 2.7 and is currently in progress to get further fixes for >= 3.6.
It depends on `six`, and on Python 2.7, also `configparser` and `pyliblzma`.

## Test-driven Development (TDD) Model

Please see [CONTRIBUTING.md] for installing a local development environment.

This package has CI which can be run locally but is also run in GitHub CI to ensure
Test-driven development.

The Continuous Integration Tests feature:

- Combined coverage testing of Python 2.7 and Python 3.8 code branches
- Automatic Upload of the combined coverage to CodeCov (from the GitHub Workflow)
- Checking of the combined coverage against the diff to master: Fails if changes are not covered!
- Pylint report in the GitHub Action Summary page, with Warning and Error annotatios, even in the code review.
- Check that changes don't generate pylint warnings (if warning classes which are enabled in .pylintrc)
- Static analysis using `mypy`, `pylint`, `pyright` and `pytype`

This enforces that any change (besides whitespace):

- has code coverage and
- does not introduce a `pylint` warning which is not disabled in `.pylintrc`
- does not introduce a type of static analysis warning which is currently suppressed.

## Status Summary

- The warnings shown on the GitHub Actions Summary Page indicate the remaining
  work for full Pyhon3 support (excluding missing tests).

## `Pylint` results from GitHub CI in GitHub Actions page

A step of the GitHub workflow produces a browser-friendly `pylint` report:
From the [Actions tab](https://github.com/xenserver/python-libs/actions),
open a recent workflow run the latest and scroll down until you see the tables!

## Configuration files

- `pyproject.toml`: Top-level configuration of the package metadata and dependencies
- `tox.ini`: Secondary level configuration, defines of the CI executed by `tox`
- `pytest.ini`: The defaults used by `pytest` unless overruled by command line options
- `.github/workflows/main.yml`: Configuration of the GitHub CI matrix jobs and coverage upload
- `.github/act-serial.yaml`: Configuration for the jobs run by the local GitHub actions runner `act`
- `.pylintrc`: Configuration file of `Pylint`

## Installation and setup of the development environment

For the installation of the general development dependencies, visit [CONTRIBUTING.md](CONTRIBUTING.md)

## Static analysis using mypy, pylint, pyright and pytype

The preconditions for using static analysis with `mypy` (which passes now but has
only a few type comments) and `pyright` are present now and `mypy` is enabled in `tox`
which runs the tests in GitHub CI as well. But of course, because they code is largely
still not yet typed, no strict checks can be enabled so far. However, every checker
which is possible now, is enabled.

Checking the contents of untyped functions is enabled for all but four modules which
would need more work. Look for `check_untyped_defs = false` in `pytproject.toml`.

The goal or final benefit would be to have it to ensure internal type correctness
and code quality but also to use static analysis to check the interoperability with
the calling code.

## Type annotations: Use Type comments for now

Python2.7 can't support the type annotation syntax, but until all users are migrated,
annotations in comments (type comments) can be used. They are supported by
tools like `mypy` and `pyright` (VS Code):

Quoting from <https://stackoverflow.com/questions/53306458/python-3-type-hints-in-python-2>:

> Function annotations were introduced in [PEP 3107](https://www.python.org/dev/peps/pep-3107/) for Python 3.0. The usage of annotations as type hints was formalized in in [PEP 484](https://www.python.org/dev/peps/pep-0484/) for Python 3.5+.
>
> Python < 3.0 does support the type hints syntax, but
> [PEP 484](https://www.python.org/dev/peps/pep-0484/#suggested-syntax-for-python-2-7-and-straddling-code)
> introduces type comments that are equally supported and are otherwise ignored.
  These type comments look like this:

```py
def get_default_device(use_gpu=True):
    # type: (bool) -> cl.Device
    ...
```

Many type checkers support this syntax: mypy, pyright/pylance, pytype

As proof, these examples show how the comment below triggers the checks:

```diff
--- a/xcp/xmlunwrap.py
+++ b/xcp/xmlunwrap.py
@@ -29,1 +29,2 @@ class XmlUnwrapError(Exception):
 def getText(nodelist):
+    # type:(Element) -> str
```

mypy:

```py
$ mypy xcp/xmlunwrap.py
xcp/xmlunwrap.py:31: error: Name "Element" is not defined
xcp/xmlunwrap.py:38: error: Incompatible return value type (got "bytes", expected "str")
```

pyright (used by VS Code by default):

```py
$ pyright xcp/xmlunwrap.py|sed "s|$PWD/||"
...
pyright 1.1.295
xcp/xmlunwrap.py
  xcp/xmlunwrap.py:32:13 - error: "Element" is not defined (reportUndefinedVariable)
  xcp/xmlunwrap.py:38:12 - error: Expression of type "Unknown | bytes" cannot be assigned to return type "str"
    Type "Unknown | bytes" cannot be assigned to type "str"
      "bytes" is incompatible with "str" (reportGeneralTypeIssues)
  xcp/xmlunwrap.py:81:38 - error: Argument of type "Unknown | None" cannot be assigned to parameter "default" of type "str" in function "getStrAttribute"
    Type "Unknown | None" cannot be assigned to type "str"
      Type "None" cannot be assigned to type "str" (reportGeneralTypeIssues)
3 errors, 0 warnings, 0 informations
Completed in 0.604sec
```

See <https://github.com/xenserver/python-libs/pull/23> for the context of this example.

## Guidelines

Charset encoding/string handling:
See [README-Unicode.md](README-Unicode.md) for details on Unicode support.

## Users

- [host-installer](https://github.com/xenserver/host-installer)
- [host-upgrade-plugin](https://github.com/xcp-ng-rpms/host-upgrade-plugin) ([koji](https://koji.xcp-ng.org/packageinfo?packageID=104)):
  - /etc/xapi.d/plugins/prepare_host_upgrade.py
- [xapi](https://github.com/xapi-project/xen-api) (`xapi-core.rpm` and `xenopsd.rpm`)
  - /etc/xapi.d/extensions/pool_update.apply
  - /etc/xapi.d/extensions/pool_update.precheck
  - /etc/xapi.d/plugins/disk-space
  - /etc/xapi.d/plugins/install-supp-pack
  - /opt/xensource/libexec/host-display
  - /opt/xensource/libexec/mail-alarm
  - /opt/xensource/libexec/usb_reset.py
  - /opt/xensource/libexec/usb_scan.py
  - /usr/libexec/xenopsd/igmp_query_injector.py
- xenserver-release-config/[xcp-ng-release-config](https://koji.xcp-ng.org/rpminfo?rpmID=10250)
  - /opt/xensource/libexec/fcoe_driver
  - /opt/xensource/libexec/xen-cmdline
- <https://github.com/xcp-ng-rpms/interface-rename>
  - /etc/sysconfig/network-scripts/interface-rename.py
  - /opt/xensource/bin/interface-rename
- pvsproxy (Proprietary)
  - /usr/libexec/xapi-storage-script/volume/org.xen.xapi.storage.tmpfs/memoryhelper.py
- <https://github.com/xenserver/linux-guest-loader> (not installed by default anymore)
  - /opt/xensource/libexec/eliloader.py
- <https://github.com/xcp-ng-rpms/vcputune>
  - /opt/xensource/bin/host-cpu-tune
- The ACK xapi plugin. See: <https://github.com/xenserver/python-libs/pull/21>

Verification:

```ps
# rpm -qf $(grep -r import /usr/libexec/ /usr/bin /etc/xapi.d/ /opt/xensource/|grep xcp|cut -d: -f1|grep -v Binary) --qf '%{name}\n'|sort -u|tee xcp-python-libs-importers.txt
host-upgrade-plugin
interface-rename
pvsproxy
vcputune
xapi-core
xenopsd
xenserver-release-config
# grep -s import $(rpm -ql xapi-core)|grep xcp|cut -d: -f1
/etc/xapi.d/extensions/pool_update.apply
/etc/xapi.d/extensions/pool_update.precheck
/etc/xapi.d/plugins/disk-space
/etc/xapi.d/plugins/disk-space
/etc/xapi.d/plugins/install-supp-pack
/opt/xensource/libexec/host-display
/opt/xensource/libexec/mail-alarm
/opt/xensource/libexec/usb_reset.py
/opt/xensource/libexec/usb_scan.py
```
