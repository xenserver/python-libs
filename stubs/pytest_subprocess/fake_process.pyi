from .process_recorder import ProcessRecorder as ProcessRecorder
from .types import COMMAND as COMMAND, OPTIONAL_TEXT_OR_ITERABLE as OPTIONAL_TEXT_OR_ITERABLE
from .utils import Any as Any, Command as Command, Program as Program
from _typeshed import Incomplete
from typing import Any as AnyType, Callable, ClassVar, Dict, List, Optional, Type

class FakeProcess:
    any: ClassVar[Type[Any]]
    program: ClassVar[Type[Program]]
    definitions: Incomplete
    calls: Incomplete
    exceptions: Incomplete
    def __init__(self) -> None: ...
    def register(
        self,
        command: COMMAND,
        stdout: OPTIONAL_TEXT_OR_ITERABLE = ...,
        stderr: OPTIONAL_TEXT_OR_ITERABLE = ...,
        returncode: int = ...,
        wait: Optional[float] = ...,
        # callback: Optional[Callable] = ...,
        callback_kwargs: Optional[Dict[str, AnyType]] = ...,
        # signal_callback: Optional[Callable] = ...,
        occurrences: int = ...,
        # stdin_callable: Optional[Callable] = ...,
    ) -> ProcessRecorder: ...
    register_subprocess = register
    def pass_command(self, command: COMMAND, occurrences: int = ...) -> None: ...
    def __enter__(self) -> "FakeProcess": ...
    def __exit__(self, *args: List[Any], **kwargs: Dict[str, Any]) -> None: ...
    def allow_unregistered(self, allow: bool) -> None: ...
    def call_count(self, command: COMMAND) -> int: ...
    def keep_last_process(self, keep: bool) -> None: ...
    @classmethod
    def context(cls) -> "FakeProcess": ...
