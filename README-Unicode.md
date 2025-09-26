# Unicode migration

## Problem

Python3.6 on XS8 does not have an all-encompassing default UTF-8 mode for I/O.

Newer Python versions have a UTF-8 mode that they even enable by default.
Python3.6 only enabled UTF-8 for I/O when a UTF-8 locale is used.
See below for more background info on the UTF-8 mode.

For situations where UTF-8 enabled, we have to specify UTF-8 explicitly.

This happens when LANG or LC_* variables are not set for UTF-8.
XAPI plugins like auto-cert-kit find themselves in this situation.

Example:
For reading UTF-8 files like the `pciids` file, add `encoding="utf-8"`.
This applies especially to `open()` and `Popen()` when files may contain UTF-8.

This also applies when en/decoding to/from `urllib` which uses bytes.
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

```sh
for i in 3.{6,7,10,11};do echo -n "3.$i: ";
   LC_ALL=C python3.$i -c 'import locale,sys;print(locale.getpreferredencoding())';done
3.6: ANSI_X3.4-1968
3.7: UTF-8
3.10: UTF-8
3.11: utf-8
```

This has the effect that in Python 3.6, the default codec for XAPI plugins is `ascii`:

```sh
for i in 2.7 3.{6,7};do echo "$i:";
  LC_ALL=C python$i -c 'open("/usr/share/hwdata/pci.ids").read()';done
```

```text
2.7:
3.6:
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/usr/lib64/python3.6/encodings/ascii.py", line 26, in decode
    return codecs.ascii_decode(input, self.errors)[0]
UnicodeDecodeError: 'ascii' codec can't decode byte 0xc2 in position 97850: ordinal not in range(128)
3.7:
```

The `'ascii'` codec fails on all bytes >128.
For example, it cannot decode the bytes representing `²` (UTF-8: power of two) in the PCI IDs database.
To read `/usr/share/hwdata/pci.ids`, we must use `encoding="utf-8"`.

While Python 3.7 and newer use UTF-8 mode by default, it does not set up an error handler for `UnicodeDecodeError`.

Also, some older tools output ISO-8859-1 characters
These aren't valid UTF-8 sequences.
For all Python versions, we need to use error handlers to handle them:

```sh
echo -e "\0262"  # ISO-8859-1 for: "²"
python3 -c 'open(".text").read()'
```

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "<frozen codecs>", line 322, in decode
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb2 in position 0: invalid start byte
```

To fix these issues, `xcp.compat`, provides a wrapper for `open()`.
It adds `encoding="utf-8", errors="replace"`
to enable UTF-8 conversion and handle encoding errors:

```py
    def utf8open(*args, **kwargs):
        if len(args) > 1 and "b" in args[1]:
            return open(*args, **kwargs)
        return open(*args, encoding="utf-8", errors="replace", **kwargs)
```
