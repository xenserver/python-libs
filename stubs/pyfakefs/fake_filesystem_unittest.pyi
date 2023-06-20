from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Union

from _typeshed import Incomplete  # pylint: disable=import-error

Patcher = Incomplete
PatchMode = Incomplete

def patchfs(
    _func: Optional[Incomplete] = ...,
    *,
    additional_skip_names: Optional[List[Union[str, ModuleType]]] = ...,
    modules_to_reload: Optional[List[ModuleType]] = ...,
    modules_to_patch: Optional[Dict[str, ModuleType]] = ...,
    allow_root_user: bool = ...,
    use_known_patches: bool = ...,
    patch_open_code: PatchMode = ...,
    patch_default_args: bool = ...,
    use_cache: bool = ...,
) -> Callable[[Any], Any]: ...
