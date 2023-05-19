"""Helper module for setting up binary or UTF-8 I/O for Popen and open in Python 3.6 and newer"""
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

def open_defaults_for_utf8_text(args, kwargs):
    """Setup keyword arguments for UTF-8 text mode with codec error handler to replace chars"""
    other_kwargs = kwargs.copy()
    mode = other_kwargs.pop("mode", "")
    if args:
        mode = args[0]
    if not mode or not isinstance(mode, str):
        raise ValueError("The mode argument is required! r for text, rb for binary")
    if sys.version_info >= (3, 0) and "b" not in mode:
        kwargs.setdefault("encoding", "utf-8")
        kwargs.setdefault("errors", "replace")
    return mode, other_kwargs
