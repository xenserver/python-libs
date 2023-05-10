Unicode Handling in the XCP package
===================================

For open(), Python 3.7 and newer use UTF-8 mode by default, not even those newer
versions set up an error handler for `UnicodeDecodeError`, for example, try.
Some older tools may output latin1/ISO-8859-1 characters, Python fails to decode these:
```ada
iconv -tlatin1 /usr/share/hwdata/pci.ids >latin1.txt
python3 -c 'open("latin1.txt").read()'
```
Python 3.6 even needs the encoding parameter if called with `LANG=C` (`XAPI` plugins):
```ada
LC_ALL=C python3.6 -c 'open("/usr/share/hwdata/pci.ids").read()'
```
Of course, Python 2.7 encoding/decoding to Unicode strings in open() and therefore,
it does not even accept the encoding and errors parameters.

To handle this in xcp and the test suite, there are two possibilities:
- Override `open()`:
  ```py
  if sys.version_info >= (3, 0):
      original_open = __builtins__["open"]
          def uopen(*args, **kwargs):
              if "b" not in (args[1] \
                if len(args) >= 2 else kwargs.get("mode", "")):
                  kwargs.setdefault("encoding", "UTF-8")
              return original_open(*args, **kwargs)
          __builtins__["open"] = uopen
  ```
But this would affect not only the `xcp` package but also it's users directly.
Hence, it is likely that we cannot consider this possibility.

The other two are to wrap our open() calls specifically and call the wrapped function,
or to pass the additional arguments by using keyword arguments (`kwargs`) dict.

Action:
- To guarantee text mode with UTF-8 support, pass encoding="utf-8"
- But not on Python2, which does not support the encoding parameter.
- If we don't set an error handler like "replace", we'd get encoding errors if the
  stdout or stderr unexpectedly contains malformed UTF-8 sequences (e.g.binary data)
```
if sys.version_info >= (3, 0):
    open_utf8 = {"encoding": "utf-8", "errors": "replace"}  # pragma: no cover
else:
    open_utf8 = {}  # pragma: no cover
```
Similar for `Popen` (see below), but `Popen` has a "text mode", which can to be
enabled in different ways using various keyword arguments. Use a dedicated
variable for `Popen` to configure the text mode:
```
if sys.version_info >= (3, 0):
    popen_utf8 = {"encoding": "utf-8", "errors": "replace"}  # pragma: no cover
else:
    popen_utf8 = {}  # pragma: no cover
```

## Discussion on Popen() in Python 2.7 and Python 3.x:

- in Python2, `Popen` returns Python2 strings (like bytes, we just read/write any data)

- in Python3, `Popen` defaults to returning bytes, not `str`.
  (In Python3: `str` is Unicode)

  `Popen` can be switched into text mode to do `.decode()` and `.encode()`
  like `open(file, "b")` can be used to open a file into binary mode.

  - `subprocess.Popen()` internally encodes and decodes when text mode is enabled,
    but by default, `suprocess.Popen()` defaults in "binary mode" (no codec).

  - The problem is which codec it uses. UTF-8 has taken over as the standard
    encoding, so we should specify it for de- and encoding non-ASCII characters.

  - Like with open() enabling an error handler for handling Unicode encoding
    and decoding errors in `Popen` itself is highly recommended using errors="replace"

  - The locale-dependent switch is a problem because we suddenly we
    get bytes instead of strings on stdout and stderr.
