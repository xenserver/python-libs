# pylint: disable=reimported,no-name-in-module,unused-import,function-redefined.redefined-builtin
from _pytest.python_api import raises
from _typeshed import Incomplete as fixture
from _typeshed import Incomplete as mark

def skip(msg: str = "", *, allow_module_level: bool = False): ...

__all__ = ["mark", "fixture", "skip", "raises"]
