import logging
from ._compat import unicode as unicode  # type: ignore
from _typeshed import Incomplete

logger: Incomplete
LEVEL: Incomplete
PREFIX: str
PREFIX_MPROC: str
COLOURED: Incomplete
TIME_FORMAT: str

class LogFormatter(logging.Formatter):
    PREFIX = PREFIX
    def __init__(self, *args, **kwargs) -> None: ...
    def format(self, record): ...

def debug(s, inst: Incomplete | None = ...) -> None: ...
def is_logging_configured(): ...
def config_logging(level=..., prefix=..., other_loggers: Incomplete | None = ...) -> None: ...
