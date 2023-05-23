"""Helper module for providing common defaults on how to enable UTF-8 I/O in Py3.6 and newer"""
# See README-Unicode.md for Details
import sys

if sys.version_info >= (3, 0):  # pragma: no cover
    open_utf8 = {"encoding": "utf-8", "errors": "replace"}

    def utf8open(filename, *args, **kwargs):
        """Helper for open(): Handle UTF-8: Default to encoding="utf-8", errors="replace" for Py3"""
        if "b" in (args[0] if args else kwargs.get("mode", "")):
            # Binary mode: just call open() unmodified:
            return open(filename, *args, **kwargs)  # pylint: disable=unspecified-encoding
        # Text mode: default to UTF-8 with error handling to replace malformed UTF-8 sequences
        kwargs.setdefault("encoding", "utf-8")  # Needed for Python 3.6 when no UTF-8 locale is set
        kwargs.setdefault("errors", "replace")  # Simple codec error handler: Replace malformed char
        # pylint: disable-next=unspecified-encoding
        return open(filename, *args, **kwargs)  # type: ignore[call-overload]
else:
    # Python2.7: None of the above is either supported or relevant (strings are bytes):
    open_utf8 = {}
    utf8open = open
