Common XenServer/XCP-ng Python classes
======================================

The `xcp` directory contains the Common XenServer and XCP-ng Python packages.
They are intented for use in XenServer and XCP-ng Dom0 only and deal with logging,
Hardware/PCI, networking, and other Dom0 tasks.

The pip package name is `python-libs` which is also the rpm package name in XenServer.
XCP-ng packages it as [xcp-python-libs](https://github.com/xcp-ng-rpms/xcp-python-libs)
([koji](https://koji.xcp-ng.org/packageinfo?packageID=400)).

It supports Python 2.7 and is currently in progress to get further fixes for >= 3.6.
It depends on `six`, and on Python 2.7, also `configparser` and `pyliblzma`.

Pylint results from GitHub CI in GitHub Actions page
----------------------------------------------------
A step of the GitHub workflow produces a browser-friendly `pylint` report:
From the [Actions tab](https://github.com/xenserver/python-libs/actions),
open a recent workflow run the latest and scroll down until you see the tables!

Testing locally and in GitHub CI using tox
------------------------------------------

`pytest` runs tests. Checks by `pylint` and `mypy`. With `tox`, developers can
run the full test suite for Python 2.7 and 3.x. Unit tests are passing but there are
 many Python3 issues which it does not uncover yet.

> Intro: Managing a Project's Virtualenvs with tox -
> A comprehensive beginner's introduction to tox.
> https://www.seanh.cc/2018/09/01/tox-tutorial/

To run the tests for all supported and installed python versions, run:
```yaml
# The latest versions of tox need 1.11.0, so sensure that you have the latest py-1.11:
pip3 install 'py>=1.11.0' tox; tox
```
You can run tox with just the python versions you have using `tox -e py27-test -e py3.11-mypy`.
The syntax is `-e py<pvthon-version>-<factor1>[-factor2]` The currently supported factors
are:
- `test`: runs pytest
- `cov`: runs pytest --cov and generate XML and HTML reports in `.tox/py<ver>-cov/logs/`
- `mypy`: runs mypy
- `fox`: runs like `cov` but then opens the HTML reports in Firefox!

The list of `virtualenvs` can be shown using this command: `tox -av -e py312-fox`
```yaml
using tox-3.28.0 from /usr/lib/python3.11/site-packages/tox/__init__.py (pid 157772)
default environments:
py27-test  -> Run in a python2.7 virtualenv: pytest
py36-test  -> Run in a python3.6 virtualenv: pytest
py37-test  -> Run in a python3.7 virtualenv: pytest
py38-test  -> Run in a python3.8 virtualenv: pytest
py39-test  -> Run in a python3.9 virtualenv: pytest
py310-test -> Run in a python3.10 virtualenv: pytest
py311-mypy -> Run in a python3.11 virtualenv: mypy static analyis
py311-cov  -> Run in a python3.11 virtualenv: generate coverage html reports
py312-test -> Run in a python3.12 virtualenv: pytest

additional environments:
py312-fox  -> Run in a python3.12 virtualenv: generate coverage html reports and open them in firefox
```
If you have just one version of Python3, that will be enough, just use `tox -e py<ver>-test`.

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
- Note: `virtualenv-20.22` broke creating the `py27` venv with tox, at least in some setups.
  As a workaround, downgrade it to 20.21 if that happens: `pip3 install -U 'virtualenv<20.22'`
- For testing on newer Ubuntu hosts which have `python2-dev`, but not `pip2`, install `pip2` this way:
  ```json
  curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py;sudo python2 get-pip.py
  ```

Static analysis using mypy and pyright
--------------------------------------
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

Type annotations: Use Type comments for now!
--------------------------------------------
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
> or more verbosely,
```py
def get_default_device(use_gpu=True  # type: bool
                      ):
    # type: (...) -> cl.Device
    ...
```
> The PEP explicitly states that this form of type hinting should work for any version of Python.

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

Special open TODOs:
-------------------

Charset encoding/string handling:
* With Python3, `read()` on files `open()`ed without specifying binary mode will attempt
  to decode the data into the Python3 Unicode string type, which will fail for all
  binary data. Thus all `open()` calls which might open binary files have to be converted
  to binary mode by default unless the caller is sure he is opening an ASCII file,
  even then, enabling an error handle to handle decoding errors is recommended.
* With Python3, the `stdin`, `stdout` and `stderr` pipes for `Popen()` default to
  `bytes`(binary mode.) Binary mode is much safer because it foregoes the encode/decode. The existing users need to be able to enable text mode (when safe, it will attempt
  to decode and encode!) or preferably be able to use bytes (which is the type behind Python2 strings too) instead. See these PRs for details:
  * https://github.com/xenserver/python-libs/pull/22
  * https://github.com/xenserver/python-libs/pull/23
  * https://github.com/xenserver/python-libs/pull/24
  * What's more: When code is called from a xapi plugin (such as ACK), when such code
    attempts to read text files like the `pciids` file, and there is a Unicode char
    it int, and the locale is not set up to be UTF-8 (because xapi plugins are started
    from xapi), the UTF-8 decoder has to be explicitly enabled for these files,
    bese by adding `encoding="utf-8"` to the arguments of these specific `open()` calls,
    to have valid Unicode text strings, e.g. `xcp.pci`, for regular text processing.
  * TODO: More to be opened for all remaining `open()` and `Popen()` users,
    as well as ensuring that users of `urllib` are able to work with they bytes
    it returns (there is no option to use text mode, data may be gzip-encoded!)

Users
-----

* https://github.com/xenserver/host-installer
    * /opt/xensource/installer/ (has copies of `cpiofile.py`, `repository.py` (with `accessor.py`)
* https://github.com/xcp-ng-rpms/host-upgrade-plugin ([koji](https://koji.xcp-ng.org/packageinfo?packageID=104)):
    * /etc/xapi.d/plugins/prepare_host_upgrade.py
* https://github.com/xapi-project/xen-api (`xapi-core.rpm` and `xenopsd.rpm`)
    * /etc/xapi.d/extensions/pool_update.apply
    * /etc/xapi.d/extensions/pool_update.precheck
    * /etc/xapi.d/plugins/disk-space
    * /etc/xapi.d/plugins/install-supp-pack
    * /opt/xensource/libexec/host-display
    * /opt/xensource/libexec/mail-alarm
    * /opt/xensource/libexec/usb_reset.py
    * /opt/xensource/libexec/usb_scan.py
    * /usr/libexec/xenopsd/igmp_query_injector.py
* xenserver-release-config/[xcp-ng-release-config](https://koji.xcp-ng.org/rpminfo?rpmID=10250)
    * /opt/xensource/libexec/fcoe_driver
    * /opt/xensource/libexec/xen-cmdline
* https://github.com/xcp-ng-rpms/interface-rename:
    * /etc/sysconfig/network-scripts/interface-rename.py
    * /opt/xensource/bin/interface-rename
* pvsproxy (Proprietary)
    * /usr/libexec/xapi-storage-script/volume/org.xen.xapi.storage.tmpfs/memoryhelper.py
* https://github.com/xenserver/linux-guest-loader (not installed by default anymore)
    * /opt/xensource/libexec/eliloader.py
* https://github.com/xcp-ng-rpms/vcputune
    * /opt/xensource/bin/host-cpu-tune
* The ACK xenapi plugin see: https://github.com/xenserver/python-libs/pull/21

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

