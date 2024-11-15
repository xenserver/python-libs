# Python3 Unicode migration in the XCP package

## Problem

Python3.6 on XS8 does not have an all-encompassing default UTF-8 mode for I/O.

Newer Python versions have a UTF-8 mode that they even enable by default.
Python3.6 only enabled UTF-8 for I/O when a UTF-8 locale is used.
See below for more background info on the UTF-8 mode.

For situations where UTF-8 enabled, we have to specify UTF-8 explicitly.

Such situation happens when LANG or LC_* variables are not set for UTF-8.
XAPI plugins like auto-cert-kit are in this situation.

Example:
For reading UTF-8 files like the `pciids` file, add `encoding="utf-8"`.
This applies especially to `open()` and `Popen()` when files my contain UTF-8.

This also applies when en/decoding to/form `urllib` which uses bytes.
`urllib` has to use bytes as HTTP data can of course also be binary, e.g. compressed.

## Migrating `subprocess.Popen()`

With Python3, the `stdin`, `stdout` and `stderr` pipes for `Popen()` default to `bytes`(binary mode). Binary mode is much safer because it foregoes the encode/decode.

The for working with strings, existing users need to either enable text mode (when safe, it will attempt to decode and encode!) or be able to use bytes instead.

For cases where the data is guaranteed to be pure ASCII, such as when resting the `proc.stdout` of `lspci -nm`, it is sufficient to use:

```py
open(["lspci, "-nm"], stdout=subprocess.PIPE, universal_newlines=True)
```

This is possible because `universal_newlines=True` is accepted by Python2 and Python3.
On Python3, it also enables text mode for `subprocess.PIPE` streams (newline conversion
not needed, but text mode is needed)

## Migrating `builtins.open()`

On Python3, `builtins.open()` can be used in a number of modes:

- Binary mode (when `"b"` is in `mode`): `read()` and `write()` use `bytes`.
- Text mode (Python3 default up to Python 3.6), when UTF-8 character encoding is not set by the locale
- UTF-8 mode (default since Python 3.7): <https://peps.python.org/pep-0540/>

When no Unicode locale in force, like in XAPI plugins, Python3 will be in text mode or UTF-8 (since Python 3.7, but existing XS is on 3.6):

- By default, `read()` on files `open()`ed without selecting binary mode attempts
  to decode the data into the Python3 Unicode string type.
  This fails for binary data.
  Any `ord() >= 128`, when no UTF-8 locale is active With Python 3.6, triggers `UnicodeDecodeError`.

- Thus, all `open()` calls which might open binary files have to be converted to binary
  or UTF-8 mode unless the caller is sure he is opening an ASCII file.
  But even then, enabling an error handler to handle decoding errors is recommended:

  ```py
  open(filename, errors="replace")
  ```

  But neither `errors=` nor `encoding=` is accepted by Python2, so a wrapper is likely best.

### Binary mode

When decoding bytes to strings is not needed, binary mode can be great because it side-steps string codecs. But, string operations involving string Literals have to be changed to bytes.

However, when strings need to returned from the library, something like `bytes.decode(errors="ignore")` to get strings is needed.

### UTF-8 mode

Most if the time, the `UTF-8` codec should be used since even simple text files which are even documented to contain only ASCII characters like `"/usr/share/hwdata/pci.ids"` in fact __do__ contain UTF-8 characters.

Some files or some output data from commands even contains legacy `ISO-8859-1` chars, and even the `UTF-8` codec would raise `UnicodeDecodeError` for these.
When this is known to be the case, `encoding="iso-8859-1` could be tried (not tested yet).

### Problems

With the locale set to C (XAPI plugins have that), Python's default mode changes
between 3.6 and 3.7:

```py
for i in 3.{6,7,10,11};do echo -n "3.$i: ";
   LC_ALL=C python3.$i -c 'import locale,sys;print(locale.getpreferredencoding())';done
3.6: ANSI_X3.4-1968
3.7: UTF-8
3.10: UTF-8
3.11: utf-8
```

This has the effect that in Python 3.6, the default codec for XAPI plugins is `ascii`:

```py
for i in 2.7 3.{6,7};do echo "$i:";
  LC_ALL=C python$i -c 'open("/usr/share/hwdata/pci.ids").read()';done
2.7:
3.6:
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/usr/lib64/python3.6/encodings/ascii.py", line 26, in decode
    return codecs.ascii_decode(input, self.errors)[0]
UnicodeDecodeError: 'ascii' codec can't decode byte 0xc2 in position 97850: ordinal not in range(128)
3.7:
```

This error means that the `'ascii' codec` cannot handle input ord() >= 128, and as some Video cards use `²` to reference their power, the `ascii` codec chokes on them.

It means `xcp.pci.PCIIds()` cannot use `open("/usr/share/hwdata/pci.ids").read()`.

While Python 3.7 and newer use UTF-8 mode by default, it does not set up an error handler for `UnicodeDecodeError`.

As it happens, some older tools output ISO-8859-1 characters hard-coded and these aren't valid UTF-8 sequences, and even newer Python versions need error handlers to not fail:

```py
echo -e "\0262"  # ISO-8859-1 for: "²"
python3 -c 'open(".text").read()'
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "<frozen codecs>", line 322, in decode
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb2 in position 0: invalid start byte
```

```py
pylint -d all -e unspecified-encoding --msg-template="{path} line {line} in {obj}()" xcp/ tests/
************* Module xcp.accessor
xcp/accessor.py line 165 in MountingAccessor.writeFile()
xcp/accessor.py line 240 in FileAccessor.writeFile()
************* Module xcp.bootloader
xcp/bootloader.py line 111 in Bootloader.readExtLinux()
xcp/bootloader.py line 219 in Bootloader.readGrub()
xcp/bootloader.py line 335 in Bootloader.readGrub2()
xcp/bootloader.py line 465 in Bootloader.writeExtLinux()
xcp/bootloader.py line 507 in Bootloader.writeGrub()
xcp/bootloader.py line 541 in Bootloader.writeGrub2()
************* Module xcp.cmd
xcp/cmd.py line 67 in OutputCache.fileContents()
************* Module xcp.dom0
xcp/dom0.py line 85 in default_memory()
************* Module xcp.environ
xcp/environ.py line 48 in readInventory()
************* Module xcp.logger
xcp/logger.py line 51 in openLog()
************* Module xcp.net.ifrename.dynamic
xcp/net/ifrename/dynamic.py line 95 in DynamicRules.load_and_parse()
xcp/net/ifrename/dynamic.py line 292 in DynamicRules.save()
************* Module xcp.net.ifrename.static
xcp/net/ifrename/static.py line 118 in StaticRules.load_and_parse()
xcp/net/ifrename/static.py line 330 in StaticRules.save()
************* Module tests.test_biosdevname
tests/test_biosdevname.py line 30 in TestDeviceNames.test()
tests/test_biosdevname.py line 32 in TestDeviceNames.test()
************* Module tests.test_bootloader
tests/test_bootloader.py line 32 in TestLinuxBootloader.setUp()
tests/test_bootloader.py line 34 in TestLinuxBootloader.setUp()
tests/test_bootloader.py line 36 in TestLinuxBootloader.setUp()
tests/test_bootloader.py line 38 in TestLinuxBootloader.setUp()
************* Module tests.test_pci
tests/test_pci.py line 96 in TestPCIIds.test_videoclass_by_mock_calls()
tests/test_pci.py line 110 in TestPCIIds.mock_lspci_using_open_testfile()
```

Of course, `xcp/net/ifrename` won't be affected, but it would be good to fix the
warning for them as well in an intelligent way. See the proposal for that below.

There are a couple of possibilities and Python because 2.7 does not support the
arguments we need to pass to ensure that all users of open() will work, we need
to make passing the arguments conditional on Python >= 3.

1. Overriding `open()`.
   While technically working, it would affect the entire interpreter:

    ```py
    if sys.version_info >= (3, 0):
        original_open = __builtins__["open"]
            def utf8_open(*args, **kwargs):
                if "b" not in (args[1] \
                  if len(args) >= 2 else kwargs.get("mode", "")):
                    kwargs.setdefault("encoding", "UTF-8")
                    kwargs.setdefault("errors", "replace")
                return original_open(*args, **kwargs)
            __builtins__["open"] = utf8_open
    ```

2. This is sufficient but is not very nice:

    ```py
    # xcp/utf8mode.py
    if sys.version_info >= (3, 0):
        open_utf8args = {"encoding": "utf-8", "errors": "replace"}
    else:
        open_utf8args = {}
    # xcp/{cmd,pci,environ?,logger?}.py tests/test_{pci,biosdevname?,...?}.py
    + from .utf8mode import open_utf8args
    ...
    - open(filename)
    + open(filename, **open_utf8args)
    ```

   But, `pylint` will still warn about these lines, so I propose:

3. Instead, use a wrapper function, which will also silence the `pylint` warnings at the locations which have been changed to use it:

    ```py
    # xcp/utf8mode.py
    if sys.version_info >= (3, 0):
        def utf8open(*args, **kwargs):
            if len(args) > 1 and "b" in args[1]:
                return open(*args, **kwargs)
            return open(*args, encoding="utf-8", errors="replace", **kwargs)
    else:
        utf8open = open
    # xcp/{cmd,pci,environ?,logger?}.py tests/test_{pci,biosdevname?,...?}.py
    + from .utf8mode import utf8open
    ...
    - open(filename)
    + utf8open(filename)
    ```

Using the 3rd option, the `pylint` warnings for the changed locations
`unspecified-encoding` and `consider-using-with` don't appear without
explicitly disabling them.

PS: Since utf8open() still returns a context-manager, `with open(...) as f:`
would still work.
