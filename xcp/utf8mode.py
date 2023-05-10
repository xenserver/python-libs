# See README-Unicode.md for Details
import sys

if sys.version_info >= (3, 0):
    open_textmode = {"encoding": "utf-8", "errors": "replace"}  # pragma: no cover
    popen_textmode = open_textmode  # pragma: no cover

    def utf8open(*args, **kwargs):
        """Helper for open() which adds encoding="utf-8", errors="replace" for Py3"""
        if len(args) > 1 and "b" in args[1]:  # pragma: no cover
            # pylint: disable-next=unspecified-encoding
            return open(*args, **kwargs)
        return open(*args, encoding="utf-8", errors="replace", **kwargs)

else:  # pragma: no cover
    open_textmode = {}  # pragma: no cover
    popen_textmode = {}  # pragma: no cover
    utf8open = open
