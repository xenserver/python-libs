[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![](https://img.shields.io/badge/python-2.7_%7C_3.6_%7C_3.7_%7C_3.8_%7C_3.9_%7C_3.10_%7C_3.11+-blue.svg)](https://www.python.org/downloads/)
[![codecov](https://codecov.io/gh/xenserver/python-libs/branch/master/graph/badge.svg?token=6WKVLDXJFN)](https://codecov.io/gh/xenserver/python-libs)
[![](https://img.shields.io/badge/License-BSD--2--Cause%20%26%20MIT-brightgreen)](https://github.com/xenserver/python-libs/blob/master/LICENSE)

# Common XenServer/XCP-ng Python classes

The `xcp` directory contains the Common XenServer and XCP-ng Python packages.
They are intented for use in XenServer and XCP-ng Dom0 only and deal with logging,
Hardware/PCI, networking, and other Dom0 tasks.

The package name is `python-libs` which is also the `rpm` package name in XenServer.
XCP-ng packages it as [xcp-python-libs](https://github.com/xcp-ng-rpms/xcp-python-libs)
([koji](https://koji.xcp-ng.org/packageinfo?packageID=400)).

It supports Python 2.7 and is currently in progress to get further fixes for >= 3.6.
It depends on `six`, and on Python 2.7, also `configparser` and `pyliblzma`.

## Test-driven Development (TDD) Model

This package has CI which can be run locally but is also run in GitHub CI to ensure
Test-driven development.

The Continuous Integration Tests feature:

- Combined coverage testing of Python 2.7 and Python 3.8 code branches
- Automatic Upload of the combined coverage to CodeCov (from the GitHub Workflow)
- Checking of the combined coverage against the diff to master: Fails if changes are not covered!
- Pylint report in the GitHub Action Summary page, with Warning and Error annotatios, even in the code review.
- Check that changes don't generate pylint warnings (if warning classes which are enabled in pylintrc)
- Static analysis using `mypy`, `pyre` and `pytype`

This enforces that any change (besides whitespace):

- has code coverage and
- does not introduce a `pylint` warning which is not disabled in `pylintrc`
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
- `pylintrc`: Configuration file of `Pylint`

## Testing locally and in GitHub CI using `tox`

`pytest` runs tests, checks by `pylint` and `mypy`. With `tox`, developers can
run the full test suite for Python 2.7 and 3.x. Unit tests are passing, but there are
many Python3 issues which it does not uncover yet.

> _"Intro: Managing a Project's Virtualenvs with tox -
> A comprehensive beginner's introduction to tox":_
> https://www.seanh.cc/2018/09/01/tox-tutorial/

To run the tests for all supported and installed python versions, run:

```yaml
pip3 install --user --upgrade 'py>=1.11.0' 'virtualenv<20.22' 'tox>=4.5.1'; hash -r; tox
```

- `tox>=4` is needed in order to fix reading the python2.7 deps from `pyproject.toml`
- The latest versions of `tox` need `'py>=1.11.0'`. Ensure that it is at least 1.11.
- `virtualenv-20.22` breaks using python2.7 for the `py27` virtualenv with tox,
  therefore it has to be downgraded thus `'virtualenv<20.22'`.

Using pip-tools, you can also extract the requirements and extras from `pyptoject.toml`:

```bash
PYTHON=python3.10
$PYTHON -m pip install pip-tools
$PYTHON -m piptools compile --extra=.,test,mypy,pyre,pytype,tox -o - pyproject.toml |
    $PYTHON -m pip install -r /dev/stdin --no-warn-conflicts
```

With this, you can run most of the CI tests run by `tox` and GitHub CI also from the shell.

You can run `tox` with just the Python versions you have using `tox -e py27-test -e py3.11-mypy`.
The syntax is `-e py<pvthon-version>-<factor1>[-factor2]` The currently supported factors
are:

- `test`: runs `pytest`
- `cov`: runs `pytest --cov` and generates `XML` and `HTML` reports in `.tox/py<ver>-cov/logs/`
- `mypy`: runs `mypy`
- `fox`: runs like `cov` but then opens the `HTML` reports in Firefox!

## Recommended `pytest` plugins for development

When changing existing tests or developing new code with new test coverage, we might want to
ignore all other tests. This can be achieved with an exciting plugin called `pytest-picked`:
`pytest --picked` will collect all test modules that were newly created or changed but not
yet committed in a Git repository and run only them.

`pytest-sugar` is a plugin that, once installed, automatically changes the format of the
`pytest` standard output to include a graphical %-progress bar when running the test suite.

For nicer diffs of dictionaries, arrays and the like, use `pytest-clarity` or `pytest-icdiff`.
For more information to debug pytest test suites see: https://stribny.name/blog/pytest/

```py
pip install "pytest<7" pytest-picked pytest-sugar pytest-clarity
```

## Example development workflow

- `pip install pytest-watch` - `ptw` watches changed files and runs pytest after changes are saved.
  - Then run `ptw` on the code/tests you work on, e.g.: `ptw tests/test_pci_*` and edit the files.
- Run the tests for at also with `LC_ALL=C python3.6 -m pytest` to check for any `ascii` codec
  issues by Python3.6
- Test with `python2.7 -m pytest`
- Run `mypy` (without any arguments - The configuration is in `pyproject.toml`)
- Run `./run-pytype.py`
- Run `./run-pyre.py`
- Run `tox -e py36-lint` and fix any `Pylint` warnings
- Run `tox -e py38-covcombine` and fix any missing diff-coverage.
- Run `tox` for the full CI test suite
- Run `act` for the full CI test suite in local containers (similar to GitHub action containers)
- Commit with `--signoff` on a new branch and push it and check the triggered GitHub Action run succeeds.
- Open a new PR

The list of `virtualenvs` configured in tox can be shown using this command: `tox -av`

```yaml
$ tox -av
default environments:
py311-pyre      -> Run in a py311 virtualenv: Run pyre for static analyis, only passes using: tox -e py311-pyre
py310-pytype    -> Run in a py310 virtualenv: Run pytype for static analyis, intro: https://youtu.be/abvW0mOrDiY
py39-check      -> Run in a py39 virtualenv: Run mypy for static analyis
py38-covcombine -> Run in a py38 virtualenv: Generate combined coverage reports with py27-test coverage merged
py37-mdreport   -> Run in a py37 virtualenv: Make a test report (which is shown in the GitHub Actions Summary Page)
py36-lint       -> Run in a py36 virtualenv: Run pylint and fail on warnings remaining on lines in the diff to master

additional environments:
cov             -> Run in a /usr/bin/python3 virtualenv: Generate coverage html reports (incl. diff-cover) for this environment
covcp           -> Run in a /usr/bin/python3 virtualenv: Copy the generated .converage and coverage.xml to the UPLOAD_DIR dir
fox             -> Run in a /usr/bin/python3 virtualenv: Generate combined coverage html reports and open them in firefox
test            -> Run in a /usr/bin/python3 virtualenv: Run pytest in this environment with --cov for use in other stages
```

If you have only one version of Python3, that works too. Use: `tox -e py<ver>-test`

Installation of additional python versions for testing different versions:

- Fedora 37: `sudo dnf install tox` installs all Python versions, even 3.12a7.
- On Ubuntu, the deadsnakes/ppa is broken(except for 3.12), so conda or pyenv has to be used.
  For full instructions, see https://realpython.com/intro-to-pyenv/, E.g install on Ubuntu:
  ```yaml
  sudo apt-get install -y build-essential libssl-dev zlib1g-dev libbz2-dev
                          libreadline-dev libsqlite3-dev xz-utils libffi-dev liblzma-dev
  curl https://pyenv.run | bash # and add the displayed commands to .bashrc
  pyenv install 3.{6,7,8,9} && pyenv local 3.{6,7,8,9} # builds and adds them
  ```
- For testing on newer Ubuntu hosts which have `python2-dev`, but not `pip2`, install `pip2` this way:
  ```yml
  curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py;sudo python2 get-pip.py
  ```

## Static analysis using mypy, pyre, pyright and pytype

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

## Type annotations: Use Type comments for now!

Python2.7 can't support the type annotation syntax, but until all users are migrated,
annotations in comments (type comments) can be used. They are supported by
tools like `mypy` and `pyright` (VS Code):

Quoting from https://stackoverflow.com/questions/53306458/python-3-type-hints-in-python-2:

> Function annotations were introduced in [PEP 3107](https://www.python.org/dev/peps/pep-3107/) for Python 3.0. The usage of annotations as type hints was formalized in in [PEP 484](https://www.python.org/dev/peps/pep-0484/) for Python 3.5+.
>
> Any version before 3.0 then will not support the syntax you are using for type hints at all. However, PEP 484 [offers a workaround](https://www.python.org/dev/peps/pep-0484/#suggested-syntax-for-python-2-7-and-straddling-code), which some editors may choose to honor. In your case, the hints would look like this:

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

See https://github.com/xenserver/python-libs/pull/23 for the context of this example.

## Special open TODOs:

Charset encoding/string handling:
See [README-Unicode.md](README-Unicode.md) for details:

- What's more: When code is called from a xapi plugin (such as ACK), when such code
  attempts to read text files like the `pciids` file, and there is a Unicode char
  it int, and the locale is not set up to be UTF-8 (because xapi plugins are started
  from xapi), the UTF-8 decoder has to be explicitly enabled for these files,
  bese by adding `encoding="utf-8"` to the arguments of these specific `open()` calls,
  to have valid Unicode text strings, e.g. `xcp.pci`, for regular text processing.
- TODO: More to be opened for all remaining `open()` and `Popen()` users,
  as well as ensuring that users of `urllib` are able to work with they bytes
  it returns (there is no option to use text mode, data may be gzip-encoded!)

## Users

- https://github.com/xenserver/host-installer
  - /opt/xensource/installer/ (has copies of `cpiofile.py`, `repository.py` (with `accessor.py`)
- https://github.com/xcp-ng-rpms/host-upgrade-plugin ([koji](https://koji.xcp-ng.org/packageinfo?packageID=104)):
  - /etc/xapi.d/plugins/prepare_host_upgrade.py
- https://github.com/xapi-project/xen-api (`xapi-core.rpm` and `xenopsd.rpm`)
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
- https://github.com/xcp-ng-rpms/interface-rename:
  - /etc/sysconfig/network-scripts/interface-rename.py
  - /opt/xensource/bin/interface-rename
- pvsproxy (Proprietary)
  - /usr/libexec/xapi-storage-script/volume/org.xen.xapi.storage.tmpfs/memoryhelper.py
- https://github.com/xenserver/linux-guest-loader (not installed by default anymore)
  - /opt/xensource/libexec/eliloader.py
- https://github.com/xcp-ng-rpms/vcputune
  - /opt/xensource/bin/host-cpu-tune
- The ACK xenapi plugin see: https://github.com/xenserver/python-libs/pull/21

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
